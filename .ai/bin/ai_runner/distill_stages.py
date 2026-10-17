"""Ticket-level distill prepare/complete handlers and vault cap retry state."""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from .paths import (
    design_note_path, distill_prompt_path, implementation_report_path, now,
    vault_cap_exceeded_path,
)
from .state import (
    complete_stage, fail_stage, load_project_config, load_status, read, save_status,
    set_artifact, set_runner, update_stage, write,
)
from .context import (
    ensure_non_empty_files, file_ref_list, get_ticket_domain, next_adr_id, vault_root,
)
from .prompts import build_role_prompt


# ── DISTILL WORKFLOW (write path) ───────────────────────────────────────────────
# Ticket-land vault refresh, auto-triggered by qa_complete on QA pass. Mirrors the
# prepare/complete shape of every other stage. distill_complete enforces a single
# shared retry round when vault line caps are exceeded.

def _extract_architecture_impact(ticket: str) -> str:
    """Slice the '## Architecture Impact' section out of implementation_report.md.

    Falls back to embedding the whole report (with a note) if the heading is
    absent — e.g. an older ticket that predates US-004.
    """
    report = read(implementation_report_path(ticket))
    lines = report.splitlines()
    heading_re = re.compile(r"^## Architecture Impact\s*$")
    next_heading_re = re.compile(r"^#{1,2}\s")

    start = None
    for i, line in enumerate(lines):
        if heading_re.match(line):
            start = i + 1
            break

    if start is None:
        return (
            "(No '## Architecture Impact' heading found in implementation_report.md; "
            "falling back to the full report below.)\n\n" + report.strip()
        )

    end = len(lines)
    for j in range(start, len(lines)):
        if next_heading_re.match(lines[j]):
            end = j
            break

    body = "\n".join(lines[start:end]).strip()
    return body if body else "(Architecture Impact section present but empty.)"


def _distill_retry_state(ticket: str) -> Tuple[int, List[str]]:
    s = load_status(ticket)
    return s.get("distill_retry", 0), list(s.get("distill_overcap_files", []))


def _set_distill_retry_state(ticket: str, retry: int, overcap_files: List[str]) -> None:
    s = load_status(ticket)
    s["distill_retry"] = retry
    if overcap_files:
        s["distill_overcap_files"] = overcap_files
    else:
        s.pop("distill_overcap_files", None)
    s["updated_at"] = now()
    save_status(ticket, s)


def _stage_completed_in_history(ticket: str, stage: str) -> bool:
    history = load_status(ticket).get("history", [])
    return any(h.get("stage") == stage and h.get("status") == "done" for h in history)


def _largest_sections(text: str, top_n: int = 3) -> List[Tuple[str, int]]:
    """Top-N sections by line span between consecutive ##/### headings."""
    lines = text.splitlines()
    heading_re = re.compile(r"^(#{2,3})\s+(.*)$")
    sections: List[Tuple[str, int]] = []
    current_title: Optional[str] = None
    current_start = 0
    for i, line in enumerate(lines):
        if heading_re.match(line):
            if current_title is not None:
                sections.append((current_title, i - current_start))
            current_title = heading_re.match(line).group(2).strip()
            current_start = i
    if current_title is not None:
        sections.append((current_title, len(lines) - current_start))
    sections.sort(key=lambda item: item[1], reverse=True)
    return sections[:top_n]


def _write_vault_cap_exceeded(
    ticket: str, overview_path: Path, overview_lines: int, overview_cap: int
) -> None:
    overage = overview_lines - overview_cap
    sections = _largest_sections(read(overview_path))
    lines = [
        "# Vault Cap Exceeded",
        "",
        f"File: {overview_path.as_posix()}",
        f"Cap: {overview_cap} lines",
        f"Actual: {overview_lines} lines",
        f"Overage: {overage} lines",
        "",
        "## Largest Sections",
    ]
    if sections:
        for title, span in sections:
            lines.append(f"- {title} ({span} lines)")
    else:
        lines.append("- (no ##/### sections found)")
    lines.extend(
        [
            "",
            "## Next Steps",
            "Trim system-overview.md under the cap (or raise `overview_cap_lines` in "
            "project_config.json, an explicit opt-in), then re-run `distill-complete`.",
        ]
    )
    path = vault_cap_exceeded_path(ticket)
    write(path, "\n".join(lines) + "\n")
    set_artifact(ticket, "vault_cap_exceeded", path)


def distill_prepare(ticket: str) -> None:
    root = vault_root()
    if root is None:
        # Vault-disabled contract: no-op without mutating current_stage or
        # artifacts, so next_action's rule 0 is the only thing that resolves this
        # ticket to "done" — never an incidental fallback through rules 1-4.
        print(f"[SKIP] Vault disabled; distill_prepare no-op for {ticket}")
        return

    update_stage(ticket, "distill_prepare")
    set_runner(ticket, "distill-prepare")

    domain = get_ticket_domain(ticket)
    adr_id = f"ADR-{next_adr_id()}"
    impact_block = _extract_architecture_impact(ticket)

    retry, overcap_files = _distill_retry_state(ticket)
    cfg = load_project_config().get("vault", {})
    overview_cap = cfg.get("overview_cap_lines", 200)
    module_cap = cfg.get("module_cap_lines", 400)

    compress_block = ""
    if retry >= 1 and overcap_files:
        named = []
        if "overview" in overcap_files:
            named.append(f"`system-overview.md` (cap {overview_cap} lines)")
        if "module" in overcap_files:
            named.append(f"`modules/{domain}.md` (cap {module_cap} lines)")
        compress_block = f"""

## Compress Instruction (retry round)

{" and ".join(named)} exceeded its line cap on the previous distill pass. Compress it:
write a map, not an encyclopedia — drop prose, merge redundant rows, prune stale
`planned` entries, tighten wording. Do not drop required headings or structure.
"""

    overview_target = root / "architecture" / "system-overview.md"
    module_target = root / "architecture" / "modules" / f"{domain}.md"

    epic_prefix_match = re.match(r"^(EPIC-\d+)-", ticket)
    epic_prefix = epic_prefix_match.group(1).lower() if epic_prefix_match else None
    epic_scope_note = (
        f"This ticket's epic prefix is `{epic_prefix}` (epic dir/ADR `epic:` values are "
        f"lowercase full slugs starting with this prefix, e.g. `{epic_prefix}-mvp`)."
        if epic_prefix
        else "This ticket has no `EPIC-NNN-` prefix — it implements no epic-level ADR."
    )

    task_instruction = f"""Work inside the current repository.

Refresh the architecture vault to reflect this ticket's changes. The current
(capped) system-overview.md and modules/{domain}.md are injected above under
"Architecture (Vault)".

Read these files:
{file_ref_list([design_note_path(ticket), implementation_report_path(ticket)])}

Developer-reported Architecture Impact (from implementation_report.md):

{impact_block}

Next free ADR id for this ticket: {adr_id}
{compress_block}
Rewrite these files directly:
- {overview_target.as_posix()}
- {module_target.as_posix()}

Rules:
- Keep system-overview.md's fixed headings and order exactly: `## Components`,
  `## Data Flows`, `## Invariants / Constraints`, `## ADR Index`.
- Only update what this ticket's Architecture Impact actually changed — this is a
  map, not an encyclopedia. Prune stale `planned` entries this ticket superseded.
- ADR handling — two modes. {epic_scope_note}
  - **Flip an existing epic-approved decision:** if this ticket has an epic
    prefix, look at every `proposed`/`accepted` ADR under
    `.ai/vault/architecture/decisions/` whose `epic:` value starts with (or
    equals) that prefix — e.g. prefix `epic-001` matches an ADR with
    `epic: epic-001-living-architecture-doc`. If exactly one plausibly matches
    the decision this ticket implements, append
    this ticket's id to that ADR's `tickets:` list, flip its `status` from
    `proposed` to `accepted` if this is the first implementing ticket (leave
    `accepted` as-is on later tickets), and flip the matching module-doc entry
    from `planned` to `current`.
  - **Ambiguous match:** if zero or more than one epic-scoped ADR plausibly
    matches, do NOT flip any ADR or module entry — print a `[FLAG]` line naming
    this ticket's id, its epic prefix, and (if multiple) the candidate ADR ids,
    for manual resolution.
  - **New, ticket-only decision:** if the Architecture Impact warrants
    recording a decision not already tracked by an epic ADR, use {adr_id} for
    its id and write a new `proposed` ADR file under
    `.ai/vault/architecture/decisions/`. Do not invent a different id.
- Prune signal: if you notice any `proposed` ADR (in or outside this ticket's
  epic scope) with an empty `tickets:` list, print a `[PRUNE]` line naming that
  ADR id and its associated `planned` module entry.
- If the Architecture Impact has no delta for a dimension, leave it unchanged.
- Do not run git add/commit/push — leave all edits as working-tree changes.

Important:
- Write the updated files directly. Do not reply in chat with the final content.
"""
    prompt = build_role_prompt(ticket, "distiller", task_instruction)
    write(distill_prompt_path(ticket), prompt)
    set_artifact(ticket, "distill_prompt", distill_prompt_path(ticket))
    complete_stage(ticket, "distill_prepare", "Generated distill prompt.")
    print(f"[OK] Wrote {distill_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it rewrite the vault files, then run next --run."
    )


def distill_complete(ticket: str) -> None:
    update_stage(ticket, "distill_complete")
    set_runner(ticket, "distill-complete")

    root = vault_root()
    if root is None:
        # Defensive only — next_action's rule 0 keeps a vault-disabled ticket from
        # ever reaching this step, but a manual CLI invocation shouldn't crash.
        complete_stage(ticket, "distill_complete", "Vault disabled; nothing to verify.")
        print(f"[OK] Vault disabled; distill_complete no-op for {ticket}")
        return

    cfg = load_project_config().get("vault", {})
    overview_cap = cfg.get("overview_cap_lines", 200)
    module_cap = cfg.get("module_cap_lines", 400)

    domain = get_ticket_domain(ticket)
    overview_path = root / "architecture" / "system-overview.md"
    module_path = root / "architecture" / "modules" / f"{domain}.md"

    ensure_non_empty_files([overview_path, module_path], "distill_complete", ticket)

    overview_lines = len(read(overview_path).splitlines())
    module_lines = len(read(module_path).splitlines())
    overview_over = overview_lines > overview_cap
    module_over = module_lines > module_cap

    retry, _ = _distill_retry_state(ticket)

    if retry == 0 and (overview_over or module_over):
        overcap_files = []
        if overview_over:
            overcap_files.append("overview")
        if module_over:
            overcap_files.append("module")
        _set_distill_retry_state(ticket, 1, overcap_files)
        distill_prepare(ticket)
        print(
            f"[RETRY] Vault cap exceeded ({', '.join(overcap_files)}); re-ran "
            f"distill-prepare with a compress instruction for {ticket}. Paste the new "
            "prompt, then run distill-complete again."
        )
        return

    if module_over:
        print(
            f"[WARN] modules/{domain}.md is {module_lines} lines (cap {module_cap}); "
            "proceeding anyway after one retry round."
        )

    if overview_over:
        _write_vault_cap_exceeded(ticket, overview_path, overview_lines, overview_cap)
        fail_stage(
            ticket,
            "distill_complete",
            f"system-overview.md exceeds overview_cap_lines after retry "
            f"({overview_lines} > {overview_cap} lines)",
        )
        print(
            f"[BLOCK] system-overview.md still exceeds cap after retry; see "
            f"{vault_cap_exceeded_path(ticket)}. Trim it (or raise overview_cap_lines) "
            "and re-run distill-complete."
        )
        return

    vault_cap_exceeded_path(ticket).unlink(missing_ok=True)
    _set_distill_retry_state(ticket, 0, [])
    complete_stage(ticket, "distill_complete", "Vault caps verified.")
    print(f"[OK] Distill verified for {ticket}")
