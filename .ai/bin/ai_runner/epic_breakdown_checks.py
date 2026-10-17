"""Breakdown ticket parsing/validation and breakdown-review state helpers."""

import re
from pathlib import Path
from typing import Dict, List

from .paths import (
    epic_story_map_path, epic_story_status_path, epic_tickets_dir,
    previous_epic_breakdown_review_path, epic_breakdown_review_report_path, run_path,
)
from .state import ensure_non_empty_epic_files, fail_epic_stage, load_epic_status, read
from .context import get_epic_domains


TICKET_NAME_RE = re.compile(r"^EPIC-\d+-([A-Z]+-\d+)-.+\.md$", re.IGNORECASE)

TRACKER_ROW_RE = re.compile(r"^\|\s*([A-Za-z]+-\d+)\s*\|")

CHECKLIST_ITEM_RE = re.compile(r"^[-*]\s*\[[ xX]\]")

REQUIRED_SECTIONS = [
    "## Goal", "## Scope", "## Acceptance Criteria", "## Verification", "## References",
]


def _section_body(lines: List[str], header: str) -> List[str]:
    """Lines of the exact `##` section, including `###` subsections, up to the next `#`/`##`."""
    header_lower = header.lower()
    body: List[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if not in_section:
            if stripped.lower() == header_lower:
                in_section = True
            continue
        if re.match(r"^#{1,2}\s", stripped):
            break
        body.append(stripped)
    return body


def _section_is_filled(lines: List[str], header: str) -> bool:
    return any(line for line in _section_body(lines, header))


def parse_ticket_domains(text: str) -> List[str]:
    """Ordered, de-duplicated domain values of a ticket's `## Domains` (or legacy `## Domain`)."""
    lines = text.splitlines()
    body: List[str] = []
    for header in ("## domains", "## domain"):
        found = False
        for i, line in enumerate(lines):
            if line.strip().lower() == header:
                found = True
                for follow in lines[i + 1:]:
                    if follow.strip().startswith("#"):
                        break
                    body.append(follow)
                break
        if found:
            break

    domains: List[str] = []
    for line in body:
        item = re.sub(r"^\s*[-*]\s+", "", line.strip())
        for value in item.split(","):
            value = value.strip().strip("`").strip()
            if value and value not in domains:
                domains.append(value)
    return domains


def _checklist_counts(lines: List[str]) -> Dict[str, int]:
    """Checklist item count per `### <domain>` subsection of `## Domain Checklist` (lower-cased)."""
    counts: Dict[str, int] = {}
    current = None
    for line in _section_body(lines, "## Domain Checklist"):
        if line.startswith("###"):
            current = line.lstrip("#").strip().strip("`").strip().lower()
            counts.setdefault(current, 0)
        elif current is not None and CHECKLIST_ITEM_RE.match(line):
            counts[current] += 1
    return counts


def _fail(epic: str, stage: str, msg: str, exc: type = ValueError) -> None:
    fail_epic_stage(epic, stage, msg)
    raise exc(msg)


def validate_breakdown(epic: str, stage: str) -> List[Path]:
    """Validate story map, status tracker and every ticket; return the ticket files."""
    ensure_non_empty_epic_files(
        [epic_story_map_path(epic), epic_story_status_path(epic)], stage, epic
    )

    ticket_files = sorted(epic_tickets_dir(epic).glob("*.md"))
    if not ticket_files:
        msg = f"No ticket files found in {epic_tickets_dir(epic).as_posix()}. " \
              "The epic_planner must write at least one *.md file there."
        fail_epic_stage(epic, stage, "No ticket files found in breakdown/tickets/")
        raise FileNotFoundError(msg)

    bad_names = [tf.name for tf in ticket_files if not TICKET_NAME_RE.match(tf.name)]
    if bad_names:
        _fail(
            epic, stage,
            "Ticket file(s) do not follow the required naming format "
            "`<EPIC-ID>-<STORY-ID>-<slug>.md` (e.g. EPIC-001-US-001-add-schema.md):\n"
            + "\n".join(f"  {n}" for n in bad_names),
        )

    initialized = set(get_epic_domains(epic))
    contents = {tf: tf.read_text(encoding="utf-8") for tf in ticket_files}

    domain_errors: List[str] = []
    ticket_domains: Dict[Path, List[str]] = {}
    for tf, text in contents.items():
        domains = parse_ticket_domains(text)
        ticket_domains[tf] = domains
        if not domains:
            domain_errors.append(f"  {tf.name}: missing or empty '## Domains' section")
            continue
        for value in domains:
            if initialized and value not in initialized:
                domain_errors.append(
                    f"  {tf.name}: '## Domains' value '{value}' is not one of the "
                    f"initialized domains ({', '.join(sorted(initialized))})"
                )
    if domain_errors:
        _fail(epic, stage, "Ticket file(s) failed ## Domains validation:\n" + "\n".join(domain_errors))

    section_errors: List[str] = []
    for tf, text in contents.items():
        lines = text.splitlines()
        for section in REQUIRED_SECTIONS:
            if not _section_is_filled(lines, section):
                section_errors.append(f"  {tf.name}: missing or empty '{section}' section")
    if section_errors:
        _fail(epic, stage, "Ticket file(s) failed section validation:\n" + "\n".join(section_errors))

    checklist_errors: List[str] = []
    for tf, text in contents.items():
        domains = ticket_domains[tf]
        if len(domains) <= 1:
            continue
        lines = text.splitlines()
        if not _section_is_filled(lines, "## Domain Checklist"):
            checklist_errors.append(
                f"  {tf.name}: multi-domain ticket needs a '## Domain Checklist' section"
            )
            continue
        counts = _checklist_counts(lines)
        for value in domains:
            if counts.get(value.lower(), 0) < 1:
                checklist_errors.append(
                    f"  {tf.name}: '## Domain Checklist' needs a '### {value}' subsection "
                    "with at least one '- [ ]' item"
                )
    if checklist_errors:
        _fail(epic, stage, "Ticket file(s) failed Domain Checklist validation:\n" + "\n".join(checklist_errors))

    _check_tracker_consistency(epic, stage, ticket_files)
    return ticket_files


def _check_tracker_consistency(epic: str, stage: str, ticket_files: List[Path]) -> None:
    ticket_ids: Dict[str, List[str]] = {}
    for tf in ticket_files:
        match = TICKET_NAME_RE.match(tf.name)
        if match:
            ticket_ids.setdefault(match.group(1).upper(), []).append(tf.name)

    tracker_ids = set()
    for line in read(epic_story_status_path(epic)).splitlines():
        match = TRACKER_ROW_RE.match(line.strip())
        if match:
            tracker_ids.add(match.group(1).upper())

    errors: List[str] = []
    for story_id in sorted(ticket_ids):
        if story_id not in tracker_ids:
            errors.append(f"  {story_id}: ticket file(s) {', '.join(ticket_ids[story_id])} "
                          "have no row in epic_story_status.md")
        if len(ticket_ids[story_id]) > 1:
            errors.append(f"  {story_id}: shared by multiple ticket files "
                          f"({', '.join(ticket_ids[story_id])})")
    for story_id in sorted(tracker_ids - set(ticket_ids)):
        errors.append(f"  {story_id}: row in epic_story_status.md has no ticket file")
    if errors:
        _fail(epic, stage, "Story status tracker and ticket files disagree:\n" + "\n".join(errors))


def breakdown_review_started(epic: str) -> bool:
    """True once any breakdown review/fix artifact or history entry exists."""
    if epic_breakdown_review_report_path(epic).exists():
        return True
    if previous_epic_breakdown_review_path(epic).exists():
        return True
    history = load_epic_status(epic).get("history", [])
    return any(
        str(h.get("stage", "")).startswith(("epic_breakdown_review_", "epic_breakdown_fix_"))
        for h in history
    )


def seeded_ticket_runs(epic: str) -> List[str]:
    """Run ids (`<EPIC>-<ticket stem>`) of tickets already seeded into the ticket workflow."""
    tickets_dir = epic_tickets_dir(epic)
    if not tickets_dir.exists():
        return []
    return [
        f"{epic}-{tf.stem}"
        for tf in sorted(tickets_dir.glob("*.md"))
        if run_path(f"{epic}-{tf.stem}").is_dir()
    ]
