#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(".ai")
RUNS = BASE / "runs"
AGENTS = BASE / "agents"
FIGMA_URL_RE = re.compile(
    r"https?://(?:www\.)?figma\.com/(?:file|design|proto)/[^\s)>\\\]]+",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_path(ticket: str) -> Path:
    return RUNS / ticket


def status_file(ticket: str) -> Path:
    return run_path(ticket) / "status.json"


def project_config_path() -> Path:
    return BASE / "project_config.json"


def input_dir(ticket: str) -> Path:
    return run_path(ticket) / "input"


def architect_dir(ticket: str) -> Path:
    return run_path(ticket) / "architect"


def dev_dir(ticket: str) -> Path:
    return run_path(ticket) / "dev"


def fix_dir(ticket: str) -> Path:
    return run_path(ticket) / "fix"


def review_dir(ticket: str) -> Path:
    return run_path(ticket) / "review"


def qa_dir(ticket: str) -> Path:
    return run_path(ticket) / "qa"


def input_file(ticket: str) -> Path:
    return input_dir(ticket) / "input.md"


def architect_prompt_path(ticket: str) -> Path:
    return architect_dir(ticket) / "architect_prompt.md"


def task_spec_path(ticket: str) -> Path:
    return architect_dir(ticket) / "task_spec.md"


def design_note_path(ticket: str) -> Path:
    return architect_dir(ticket) / "design_note.md"


def acceptance_criteria_path(ticket: str) -> Path:
    return architect_dir(ticket) / "acceptance_criteria.md"


def assumptions_path(ticket: str) -> Path:
    return architect_dir(ticket) / "assumptions.md"


def dev_prompt_path(ticket: str) -> Path:
    return dev_dir(ticket) / "dev_prompt.md"


def implementation_report_path(ticket: str) -> Path:
    return dev_dir(ticket) / "implementation_report.md"


def dev_fix_prompt_path(ticket: str) -> Path:
    return fix_dir(ticket) / "dev_fix_prompt.md"


def review_fix_context_path(ticket: str) -> Path:
    return fix_dir(ticket) / "review_fix_context.md"


def qa_fix_context_path(ticket: str) -> Path:
    return fix_dir(ticket) / "qa_fix_context.md"


def previous_review_report_path(ticket: str) -> Path:
    return fix_dir(ticket) / "previous_review_report.json"


def previous_qa_report_path(ticket: str) -> Path:
    return fix_dir(ticket) / "previous_qa_report.json"


def architect_review_prompt_path(ticket: str) -> Path:
    return architect_dir(ticket) / "architect_review_prompt.md"


def architect_review_report_path(ticket: str) -> Path:
    return architect_dir(ticket) / "architect_review.json"


def architect_fix_prompt_path(ticket: str) -> Path:
    return fix_dir(ticket) / "architect_fix_prompt.md"


def architect_fix_context_path(ticket: str) -> Path:
    return fix_dir(ticket) / "architect_fix_context.md"


def previous_architect_review_path(ticket: str) -> Path:
    return fix_dir(ticket) / "previous_architect_review.json"


def review_prompt_path(ticket: str) -> Path:
    return review_dir(ticket) / "review_prompt.md"


def review_report_path(ticket: str) -> Path:
    return review_dir(ticket) / "review_report.json"


def qa_prompt_path(ticket: str) -> Path:
    return qa_dir(ticket) / "qa_prompt.md"


def qa_report_path(ticket: str) -> Path:
    return qa_dir(ticket) / "qa_report.json"


# ── EPIC PATH HELPERS ──────────────────────────────────────────────────────────

EPICS = BASE / "epics"


def epic_path(epic: str) -> Path:
    return EPICS / epic


def epic_status_file(epic: str) -> Path:
    return epic_path(epic) / "status.json"


def epic_input_dir(epic: str) -> Path:
    return epic_path(epic) / "input"


def epic_input_file(epic: str) -> Path:
    return epic_input_dir(epic) / "epic_input.md"


def epic_analysis_dir(epic: str) -> Path:
    return epic_path(epic) / "analysis"


def epic_analysis_prompt_path(epic: str) -> Path:
    return epic_analysis_dir(epic) / "epic_analysis_prompt.md"


def epic_analysis_path(epic: str) -> Path:
    return epic_analysis_dir(epic) / "epic_analysis.md"


def epic_design_dir(epic: str) -> Path:
    return epic_path(epic) / "design"


def epic_design_prompt_path(epic: str) -> Path:
    return epic_design_dir(epic) / "epic_design_prompt.md"


def epic_design_path(epic: str) -> Path:
    return epic_design_dir(epic) / "epic_design.md"


def epic_review_dir(epic: str) -> Path:
    return epic_path(epic) / "review"


def epic_review_prompt_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_review_prompt.md"


def epic_review_report_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_review.json"


def epic_fix_dir(epic: str) -> Path:
    return epic_path(epic) / "fix"


def epic_design_fix_prompt_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_design_fix_prompt.md"


def epic_review_fix_context_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_review_fix_context.md"


def previous_epic_review_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "previous_epic_review.json"


def epic_breakdown_dir(epic: str) -> Path:
    return epic_path(epic) / "breakdown"


def epic_breakdown_prompt_path(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "epic_breakdown_prompt.md"


def epic_story_map_path(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "epic_story_map.md"


def epic_tickets_dir(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "tickets"


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_base_dirs() -> None:
    for path in [BASE, RUNS, AGENTS, BASE / "templates", BASE / "bin"]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_ticket_dirs(ticket: str) -> None:
    for path in [
        run_path(ticket),
        input_dir(ticket),
        architect_dir(ticket),
        dev_dir(ticket),
        fix_dir(ticket),
        review_dir(ticket),
        qa_dir(ticket),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_epic_dirs(epic: str) -> None:
    for path in [
        epic_path(epic),
        epic_input_dir(epic),
        epic_analysis_dir(epic),
        epic_design_dir(epic),
        epic_review_dir(epic),
        epic_fix_dir(epic),
        epic_breakdown_dir(epic),
        epic_tickets_dir(epic),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_status(ticket: str) -> Dict:
    sf = status_file(ticket)
    if not sf.exists():
        raise FileNotFoundError(
            f"Status file not found for ticket '{ticket}'. Run init first."
        )
    return json.loads(sf.read_text(encoding="utf-8"))


def save_status(ticket: str, data: Dict) -> None:
    write(status_file(ticket), json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_project_config() -> Dict:
    path = project_config_path()
    if not path.exists():
        raise FileNotFoundError("Missing .ai/project_config.json")
    return json.loads(path.read_text(encoding="utf-8"))


def get_base_branch() -> str:
    cfg = load_project_config()
    return cfg.get("git", {}).get("base_branch", "main")


def init_status(ticket: str, domain: str) -> Dict:
    ts = now()
    return {
        "ticket": ticket,
        "domain": domain,
        "current_stage": "init",
        "state": "ready",
        "updated_at": ts,
        "artifacts": {},
        "history": [{"stage": "init", "status": "done", "time": ts}],
        "runner": {"mode": "file_referenced_prompts", "last_command": None},
    }


def init_epic_status(epic: str, domains: List[str]) -> Dict:
    ts = now()
    return {
        "epic": epic,
        "domains": domains,
        "current_stage": "init",
        "state": "ready",
        "updated_at": ts,
        "artifacts": {},
        "history": [{"stage": "init", "status": "done", "time": ts}],
        "runner": {"mode": "file_referenced_prompts", "last_command": None},
    }


def add_history(ticket: str, stage: str, status: str, note: str = "") -> None:
    s = load_status(ticket)
    s.setdefault("history", []).append(
        {"stage": stage, "status": status, "time": now(), "note": note}
    )
    s["updated_at"] = now()
    save_status(ticket, s)


def update_stage(ticket: str, stage: str, state: str = "running") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = state
    s["updated_at"] = now()
    save_status(ticket, s)


def complete_stage(ticket: str, stage: str, note: str = "") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = "ready"
    s["updated_at"] = now()
    save_status(ticket, s)
    add_history(ticket, stage, "done", note)


def fail_stage(ticket: str, stage: str, note: str = "") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = "failed"
    s["updated_at"] = now()
    save_status(ticket, s)
    add_history(ticket, stage, "failed", note)


def set_artifact(ticket: str, key: str, path: Path) -> None:
    s = load_status(ticket)
    s.setdefault("artifacts", {})[key] = str(path)
    s["updated_at"] = now()
    save_status(ticket, s)


def set_runner(ticket: str, detail: str) -> None:
    s = load_status(ticket)
    s.setdefault("runner", {})["last_command"] = detail
    s["updated_at"] = now()
    save_status(ticket, s)


# ── EPIC STATUS HELPERS ────────────────────────────────────────────────────────

def load_epic_status(epic: str) -> Dict:
    sf = epic_status_file(epic)
    if not sf.exists():
        raise FileNotFoundError(
            f"Status file not found for epic '{epic}'. Run epic-init first."
        )
    return json.loads(sf.read_text(encoding="utf-8"))


def save_epic_status(epic: str, data: Dict) -> None:
    write(epic_status_file(epic), json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def update_epic_stage(epic: str, stage: str, state: str = "running") -> None:
    s = load_epic_status(epic)
    s["current_stage"] = stage
    s["state"] = state
    s["updated_at"] = now()
    save_epic_status(epic, s)


def complete_epic_stage(epic: str, stage: str, note: str = "") -> None:
    s = load_epic_status(epic)
    s["current_stage"] = stage
    s["state"] = "ready"
    s["updated_at"] = now()
    s.setdefault("history", []).append(
        {"stage": stage, "status": "done", "time": now(), "note": note}
    )
    save_epic_status(epic, s)


def fail_epic_stage(epic: str, stage: str, note: str = "") -> None:
    s = load_epic_status(epic)
    s["current_stage"] = stage
    s["state"] = "failed"
    s["updated_at"] = now()
    s.setdefault("history", []).append(
        {"stage": stage, "status": "failed", "time": now(), "note": note}
    )
    save_epic_status(epic, s)


def set_epic_artifact(epic: str, key: str, path: Path) -> None:
    s = load_epic_status(epic)
    s.setdefault("artifacts", {})[key] = str(path)
    s["updated_at"] = now()
    save_epic_status(epic, s)


def set_epic_runner(epic: str, detail: str) -> None:
    s = load_epic_status(epic)
    s.setdefault("runner", {})["last_command"] = detail
    s["updated_at"] = now()
    save_epic_status(epic, s)


def ensure_non_empty_epic_files(paths: List[Path], stage: str, epic: str) -> None:
    missing = [p.as_posix() for p in paths if not p.exists() or not read(p).strip()]
    if missing:
        fail_epic_stage(epic, stage, f"Missing files: {', '.join(missing)}")
        raise FileNotFoundError(f"Missing or empty files: {', '.join(missing)}")


def init_ticket(ticket: str, requirement: str, domain: str = "") -> None:
    ensure_base_dirs()
    config = load_project_config()
    resolved_domain = domain or config.get("default_domain", "backend")

    ensure_ticket_dirs(ticket)

    write(input_file(ticket), requirement.strip() + "\n")
    save_status(ticket, init_status(ticket, resolved_domain))
    set_artifact(ticket, "input", input_file(ticket))
    print(f"[OK] Initialized {ticket} at {run_path(ticket)} (domain={resolved_domain})")


def require_agent_file(name: str) -> str:
    content = read(AGENTS / name)
    if not content.strip():
        raise FileNotFoundError(f"Missing .ai/agents/{name}")
    return content.strip()


def file_ref_list(paths: List[Path], require_exists: bool = True) -> str:
    lines = []
    for path in paths:
        if require_exists and not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
        lines.append(f"- {path.as_posix()}")
    return "\n".join(lines)


def ensure_non_empty_files(paths: List[Path], stage: str, ticket: str) -> None:
    missing = [p.as_posix() for p in paths if not p.exists() or not read(p).strip()]
    if missing:
        fail_stage(ticket, stage, f"Missing files: {', '.join(missing)}")
        raise FileNotFoundError(f"Missing or empty files: {', '.join(missing)}")


def get_ticket_domain(ticket: str) -> str:
    s = load_status(ticket)
    if s.get("domain"):
        return s["domain"]
    return load_project_config().get("default_domain", "backend")


def get_domain_config(ticket: str) -> Dict:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    return config.get("domains", {}).get(domain, {})


def get_role_skills(ticket: str, role: str) -> List[Path]:
    domain_cfg = get_domain_config(ticket)
    skill_paths = domain_cfg.get("skills", {}).get(role, [])
    return [Path(p) for p in skill_paths]


def load_skill_contents(paths: List[Path]) -> str:
    chunks = []
    for path in paths:
        content = read(path).strip()
        if not content:
            continue
        chunks.append(f"## Skill: {path.parent.name}\n\n{content}")
    return "\n\n".join(chunks)

def extract_figma_urls(text: str) -> List[str]:
    if not text:
        return []
    urls = FIGMA_URL_RE.findall(text)
    seen = set()
    result: List[str] = []
    for url in urls:
        normalized = url.strip().rstrip(".,;")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def get_ticket_figma_urls(ticket: str) -> List[str]:
    return extract_figma_urls(read(input_file(ticket)))


def get_figma_skill_paths(role: str) -> List[Path]:
    base = BASE / "skills" / "common" / "figma"

    role_map = {
        "architect": base / "architect" / "SKILL.md",
        "developer": base / "developer" / "SKILL.md",
        "reviewer": base / "reviewer" / "SKILL.md",
        "qa": base / "qa" / "SKILL.md",
    }

    paths = [base / "base" / "SKILL.md"]
    role_path = role_map.get(role)
    if role_path:
        paths.append(role_path)

    return paths


def dedupe_paths(paths: List[Path]) -> List[Path]:
    seen = set()
    result: List[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def get_effective_role_skills(ticket: str, role: str) -> List[Path]:
    paths = list(get_role_skills(ticket, role))

    figma_urls = get_ticket_figma_urls(ticket)
    if figma_urls:
        paths.extend(get_figma_skill_paths(role))

    return dedupe_paths(paths)


def build_figma_context(ticket: str) -> str:
    figma_urls = get_ticket_figma_urls(ticket)
    if not figma_urls:
        return ""

    lines = [
        "# Figma Context",
        "This ticket includes Figma design references.",
        "Use the configured Figma MCP to inspect the linked design before producing your output.",
        "Treat Figma as an important source of truth for visible UI structure when available.",
        "",
        "Figma URLs:",
    ]

    for url in figma_urls:
        lines.append(f"- {url}")

    lines.extend(
        [
            "",
            "Important:",
            "- Inspect Figma before writing the main output.",
            "- If Figma inspection is partial or fails, state that explicitly and continue with best-effort assumptions.",
            "- Summarize relevant findings instead of dumping raw Figma output.",
        ]
    )

    return "\n".join(lines)


def build_project_context(ticket: str) -> str:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    domain_cfg = config.get("domains", {}).get(domain, {})
    lines = [
        f"Project: {config.get('project_name', 'Unknown')}",
        f"Domain: {domain}",
        f"Base branch: {get_base_branch()}",
    ]
    paths = domain_cfg.get("paths", [])
    if paths:
        lines.append("Relevant paths:")
        for p in paths:
            lines.append(f"- {p}")
    return "\n".join(lines)


def build_role_prompt(ticket: str, role: str, task_instruction: str) -> str:
    role_file_map = {
        "architect": "architect.md",
        "architect_reviewer": "architect_reviewer.md",
        "developer": "developer.md",
        "reviewer": "reviewer.md",
        "qa": "qa.md",
    }
    # architect_reviewer uses the same domain skills as architect (per A-7)
    skills_role = "architect" if role == "architect_reviewer" else role
    role_prompt = require_agent_file(role_file_map[role])
    project_context = build_project_context(ticket)
    skill_content = load_skill_contents(get_effective_role_skills(ticket, skills_role))
    figma_context = build_figma_context(ticket)

    parts = [
        "# Role Instruction",
        role_prompt,
        "",
        "# Project Context",
        project_context,
    ]

    if skill_content:
        parts.extend(["", "# Domain Skills", skill_content])

    if figma_context:
        parts.extend(["", figma_context])

    parts.extend(["", "# Task Instruction", task_instruction.strip()])
    return "\n".join(parts) + "\n"


def build_fix_context(ticket: str) -> Optional[Path]:
    path = review_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return None

    buckets = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Review Fix Context",
        "",
        "Use this file to fix review findings without re-implementing the whole feature.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            lines.append(f"{idx}. File: {issue.get('file', 'unknown')}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    path = review_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "review_fix_context", path)
    return path


def build_qa_fix_context(ticket: str) -> Optional[Path]:
    path = qa_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        qa = json.loads(read(path))
    except Exception:
        return None

    missing_tests = qa.get("missing_tests", [])
    risks = qa.get("risks", [])
    summary = str(qa.get("summary", "")).strip()

    if not missing_tests and not risks and not summary:
        return None

    lines = [
        "# QA Fix Context",
        "",
        "Use this file to address QA failures, missing tests, real defects, and delivery gaps.",
        "",
        f"QA decision: {qa.get('decision', 'unknown')}",
        "",
    ]

    if missing_tests:
        lines.append("## Missing Tests")
        for idx, item in enumerate(missing_tests, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if risks:
        lines.append("## Risks Requiring Attention")
        for idx, item in enumerate(risks, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if summary:
        lines.extend(["## QA Summary", summary, ""])

    path = qa_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "qa_fix_context", path)
    return path


def build_architect_fix_context(ticket: str) -> Optional[Path]:
    path = architect_review_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    buckets: Dict[str, list] = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Architect Review Fix Context",
        "",
        "Use this file to fix architect review findings and update the design artifacts.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            area = issue.get("area", issue.get("file", "unknown"))
            lines.append(f"{idx}. Area: {area}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    ctx_path = architect_fix_context_path(ticket)
    write(ctx_path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "architect_fix_context", ctx_path)
    return ctx_path


def get_epic_domains(epic: str) -> List[str]:
    s = load_epic_status(epic)
    if "domains" in s:
        return s["domains"]
    if "domain" in s:
        return [s["domain"]]
    return list(load_project_config().get("domains", {}).keys())


def get_epic_domain(epic: str) -> str:
    """Backward-compat shim — returns the first domain from get_epic_domains.

    Raises ValueError if no domains are available (empty config and no status entry).
    Callers that do config.get('domains', {}).get(domain, {}) would silently receive
    an empty dict if this returned ""; raising here makes the failure explicit.
    """
    domains = get_epic_domains(epic)
    if not domains:
        raise ValueError(
            f"No domains found for epic '{epic}'. "
            "Check status.json and project_config.json to ensure at least one domain is defined."
        )
    return domains[0]


def build_epic_project_context(epic: str) -> str:
    config = load_project_config()
    domains = get_epic_domains(epic)
    lines = [
        f"Project: {config.get('project_name', 'Unknown')}",
        f"Domains: {', '.join(domains)}",
        f"Base branch: {get_base_branch()}",
    ]
    seen_paths: List[str] = []
    for domain in domains:
        domain_cfg = config.get("domains", {}).get(domain, {})
        for p in domain_cfg.get("paths", []):
            if p not in seen_paths:
                seen_paths.append(p)
    if seen_paths:
        lines.append("Relevant paths:")
        for p in seen_paths:
            lines.append(f"- {p}")
    return "\n".join(lines)


def get_epic_role_skills(epic: str, role: str) -> List[Path]:
    config = load_project_config()
    domains = get_epic_domains(epic)
    seen: List[str] = []
    for domain in domains:
        domain_cfg = config.get("domains", {}).get(domain, {})
        for p in domain_cfg.get("skills", {}).get(role, []):
            if p not in seen:
                seen.append(p)
    return [Path(p) for p in seen]


def build_epic_role_prompt(epic: str, role: str, task_instruction: str) -> str:
    role_file_map = {
        "epic_analyst": "epic_analyst.md",
        "epic_designer": "epic_designer.md",
        "epic_reviewer": "epic_reviewer.md",
        "epic_planner": "epic_planner.md",
    }
    role_prompt = require_agent_file(role_file_map[role])
    project_context = build_epic_project_context(epic)
    skill_content = load_skill_contents(get_epic_role_skills(epic, role))
    parts = [
        "# Role Instruction",
        role_prompt,
        "",
        "# Project Context",
        project_context,
    ]
    if skill_content:
        parts.extend(["", "# Domain Skills", skill_content])
    parts.extend(["", "# Task Instruction", task_instruction.strip()])
    return "\n".join(parts) + "\n"


def build_epic_review_fix_context(epic: str) -> Optional[Path]:
    path = epic_review_report_path(epic)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return None

    buckets: Dict[str, list] = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Epic Review Fix Context",
        "",
        "Use this file to fix epic design review findings.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            area = issue.get("area", issue.get("file", "unknown"))
            lines.append(f"{idx}. Area: {area}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    ctx_path = epic_review_fix_context_path(epic)
    write(ctx_path, "\n".join(lines).strip() + "\n")
    set_epic_artifact(epic, "epic_review_fix_context", ctx_path)
    return ctx_path


def architect_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_prepare")
    set_runner(ticket, "architect-prepare")

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list([input_file(ticket)])}

You may inspect other relevant repository files if needed.

Do NOT reply in chat with the actual result.
Write the outputs directly to these files:

- {task_spec_path(ticket).as_posix()}
- {design_note_path(ticket).as_posix()}
- {acceptance_criteria_path(ticket).as_posix()}
- {assumptions_path(ticket).as_posix()}

File requirements:
- task_spec.md: Restate the task in technical terms, define scope and out-of-scope, and list impacted modules/files if known
- design_note.md: Proposed implementation approach, main flow, data/API considerations, risks and trade-offs
- acceptance_criteria.md: Clear, testable acceptance criteria including success cases, validation cases, and failure cases
- assumptions.md: Explicit assumptions, unknowns, and ambiguities that could affect implementation

Important:
- Write each file directly.
- Do not create extra output files unless necessary.
- Keep content concise but precise.
"""
    prompt = build_role_prompt(ticket, "architect", task_instruction)
    write(architect_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_prompt", architect_prompt_path(ticket))
    complete_stage(ticket, "architect_prepare", "Generated architect prompt.")
    print(f"[OK] Wrote {architect_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write the 4 files directly, then run next --run."
    )


def architect_complete(ticket: str) -> None:
    update_stage(ticket, "architect_complete")
    set_runner(ticket, "architect-complete")

    required = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required, "architect_complete", ticket)

    set_artifact(ticket, "task_spec", task_spec_path(ticket))
    set_artifact(ticket, "design_note", design_note_path(ticket))
    set_artifact(ticket, "acceptance_criteria", acceptance_criteria_path(ticket))
    set_artifact(ticket, "assumptions", assumptions_path(ticket))

    complete_stage(ticket, "architect_complete", "Architect files verified.")
    print(f"[OK] Architect files verified for {ticket}")


def architect_review_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_review_prepare")
    set_runner(ticket, "architect-review-prepare")

    required_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "architect_review_prepare", ticket)

    followup_mode = (
        previous_architect_review_path(ticket).exists()
        and read(previous_architect_review_path(ticket)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_architect_review_path(ticket)]
        if (
            architect_fix_context_path(ticket).exists()
            and read(architect_fix_context_path(ticket)).strip()
        ):
            extra_files.append(architect_fix_context_path(ticket))

        followup_block = f"""

This is a follow-up review after an architect fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were addressed in the updated design artifacts
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the revisions
- In the summary, explicitly state whether previous high-severity issues were resolved
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Review the architect design artifacts for correctness, completeness, and alignment with the requirement.

Write valid JSON only directly to:
- {architect_review_report_path(ticket).as_posix()}

Required JSON format:
{{
  "decision": "approve|request_changes|block",
  "issues": [
    {{
      "severity": "high|medium|low",
      "area": "...",
      "message": "..."
    }}
  ],
  "summary": "..."
}}

Review focus areas:
- Design correctness: Is the proposed approach sound and implementable?
- Scope completeness: Does the task_spec cover everything needed? Are out-of-scope items clear?
- Acceptance criteria quality: Are criteria testable and unambiguous? Are failure cases covered?
- Assumption validity: Are assumptions reasonable? Are unknowns clearly called out?
- Missing edge cases: Are there scenarios the design doesn't address?
- Over/under-specification: Is the design too vague or too prescriptive?

Decision guidance:
- approve: Design is solid, criteria are testable, assumptions are reasonable, no important gaps
- request_changes: There are meaningful gaps but they are fixable within the current approach
- block: The design has severe flaws, dangerous assumptions, or is fundamentally misaligned with the requirement

Rules:
- List high severity issues first
- Tie findings to correctness, completeness, or feasibility
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "architect_reviewer", task_instruction)
    write(architect_review_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_review_prompt", architect_review_prompt_path(ticket))
    complete_stage(ticket, "architect_review_prepare", "Generated architect review prompt.")
    print(f"[OK] Wrote {architect_review_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write architect_review.json directly, then run next --run."
    )


def architect_review_complete(ticket: str) -> None:
    update_stage(ticket, "architect_review_complete")
    set_runner(ticket, "architect-review-complete")

    ensure_non_empty_files(
        [architect_review_report_path(ticket)], "architect_review_complete", ticket
    )

    try:
        parsed = json.loads(read(architect_review_report_path(ticket)))
    except json.JSONDecodeError as exc:
        fail_stage(ticket, "architect_review_complete", f"Invalid JSON in architect_review.json: {exc}")
        raise

    write(
        architect_review_report_path(ticket),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_artifact(ticket, "architect_review_report", architect_review_report_path(ticket))

    decision = parsed.get("decision", "unknown")

    if decision not in {"approve", "request_changes", "block"}:
        print(
            f"[WARN] Unexpected architect review decision: '{decision}'. "
            "Treating as request_changes (safe default). Fix the JSON if this is wrong.",
            file=sys.stderr,
        )

    if decision in {"request_changes", "block"}:
        # Archive review and build fix context
        fix_dir(ticket).mkdir(parents=True, exist_ok=True)
        archived = previous_architect_review_path(ticket)
        write(archived, read(architect_review_report_path(ticket)))
        set_artifact(ticket, "previous_architect_review", archived)
        build_architect_fix_context(ticket)
        complete_stage(
            ticket, "architect_review_complete", f"Architect reviewer decision: {decision} — fix loop required"
        )
        print(f"[OK] Architect review verified for {ticket} ({decision})")
        print("[FIX] Decision requires changes. Run next --run to start architect fix loop.")
    else:
        complete_stage(ticket, "architect_review_complete", f"Architect reviewer decision: {decision}")
        print(f"[OK] Architect review verified for {ticket} ({decision})")


def architect_fix_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_fix_prepare")
    set_runner(ticket, "architect-fix-prepare")

    required_inputs = [
        input_file(ticket),
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "architect_fix_prepare", ticket)

    fix_ctx = architect_fix_context_path(ticket)
    extra_paths: List[Path] = []
    if fix_ctx.exists() and read(fix_ctx).strip():
        extra_paths.append(fix_ctx)

    prev_review = previous_architect_review_path(ticket)
    if prev_review.exists() and read(prev_review).strip():
        extra_paths.append(prev_review)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs + extra_paths)}

Your task is to revise the architect design artifacts to address all review findings.

Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Do NOT redesign from scratch — revise the existing design artifacts
- Preserve sections that were not flagged as problematic
- Be explicit in the artifacts about how each major issue was addressed
- Do NOT write production code in this step

Overwrite the design artifacts with the corrected versions:
- {task_spec_path(ticket).as_posix()}
- {design_note_path(ticket).as_posix()}
- {acceptance_criteria_path(ticket).as_posix()}
- {assumptions_path(ticket).as_posix()}

Important:
- Write the updated artifacts directly to the files above.
- Do not reply in chat with the final content.
- Only modify files needed to address the review findings.
"""
    prompt = build_role_prompt(ticket, "architect", task_instruction)
    write(architect_fix_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_fix_prompt", architect_fix_prompt_path(ticket))
    complete_stage(ticket, "architect_fix_prepare", "Generated architect fix prompt.")
    print(f"[OK] Wrote {architect_fix_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it update the design artifacts, then run next --run."
    )


def architect_fix_complete(ticket: str) -> None:
    update_stage(ticket, "architect_fix_complete")
    set_runner(ticket, "architect-fix-complete")

    required = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required, "architect_fix_complete", ticket)

    # Clear previous architect review so next_action routes to architect-review-prepare
    architect_review_report_path(ticket).unlink(missing_ok=True)

    complete_stage(ticket, "architect_fix_complete", "Architect fix artifacts verified.")
    print(f"[OK] Architect fix verified for {ticket}")


def dev_prepare(ticket: str) -> None:
    update_stage(ticket, "dev_prepare")
    set_runner(ticket, "dev-prepare")

    required_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "dev_prepare", ticket)

    base_branch = get_base_branch()

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Implement the required code changes in the repository.

Git context:
- The current working branch contains the ticket changes
- If useful, compare the current branch against {base_branch} to understand the full ticket delta

Then write your implementation report directly to:
- {implementation_report_path(ticket).as_posix()}

The report must include:
1. Summary of changes
2. Files modified
3. Key decisions
4. Assumptions followed
5. Commands/tests you ran

Important:
- Make the code changes directly in the repo.
- Write the report directly to the file above.
- Keep the report concise and factual.
"""
    prompt = build_role_prompt(ticket, "developer", task_instruction)
    write(dev_prompt_path(ticket), prompt)
    set_artifact(ticket, "dev_prompt", dev_prompt_path(ticket))
    complete_stage(ticket, "dev_prepare", "Generated dev prompt.")
    print(f"[OK] Wrote {dev_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it change code and write implementation_report.md, then run next --run."
    )


def archive_file(ticket: str, source: Path, archive_name: str) -> Optional[Path]:
    if not source.exists() or not read(source).strip():
        return None

    archived = fix_dir(ticket) / archive_name
    write(archived, read(source))
    source.unlink(missing_ok=True)
    return archived


def archive_quality_reports_for_fix(ticket: str) -> Dict[str, Optional[Path]]:
    review_archived = archive_file(
        ticket,
        review_report_path(ticket),
        "previous_review_report.json",
    )
    qa_archived = archive_file(
        ticket,
        qa_report_path(ticket),
        "previous_qa_report.json",
    )

    result = {
        "review": review_archived,
        "qa": qa_archived,
    }

    if review_archived:
        set_artifact(ticket, "previous_review_report", review_archived)
    if qa_archived:
        set_artifact(ticket, "previous_qa_report", qa_archived)

    return result


def dev_fix_prepare(ticket: str) -> None:
    update_stage(ticket, "dev_fix_prepare")
    set_runner(ticket, "dev-fix-prepare")

    core_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(core_inputs, "dev_fix_prepare", ticket)

    review_exists = (
        review_report_path(ticket).exists() and read(review_report_path(ticket)).strip()
    )
    qa_exists = qa_report_path(ticket).exists() and read(qa_report_path(ticket)).strip()

    if not review_exists and not qa_exists:
        fail_stage(
            ticket,
            "dev_fix_prepare",
            "No review_report.json or qa_report.json found for fix mode",
        )
        raise FileNotFoundError(
            "No review_report.json or qa_report.json found for dev fix mode"
        )

    extra_paths: List[Path] = []
    issue_sources: List[str] = []

    if review_exists:
        fix_ctx = build_fix_context(ticket)
        if fix_ctx:
            extra_paths.append(fix_ctx)
        issue_sources.append("Review")

    if qa_exists:
        qa_fix_ctx = build_qa_fix_context(ticket)
        if qa_fix_ctx:
            extra_paths.append(qa_fix_ctx)
        issue_sources.append("QA")

    archived = archive_quality_reports_for_fix(ticket)

    archived_paths: List[Path] = []
    if archived.get("review"):
        archived_paths.append(archived["review"])
    if archived.get("qa"):
        archived_paths.append(archived["qa"])

    base_branch = get_base_branch()
    source_label = (
        " and/or ".join(issue_sources) if issue_sources else "Review and/or QA"
    )

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(core_inputs + archived_paths + extra_paths)}

Your task is to fix all unresolved quality findings reported by: {source_label}.

Fixing rules:
- Resolve all high severity review issues
- Resolve QA failures that indicate real code defects
- Add automated tests for missing scenarios identified by QA where appropriate
- Address delivery gaps required by acceptance criteria when feasible
- Do NOT re-implement the feature from scratch
- Do NOT introduce unrelated changes
- Prefer the minimal correct fix for each issue
- Preserve existing behavior unless it is explicitly identified as wrong

Git context:
- The current working branch contains the ticket changes
- If useful, compare the current branch against {base_branch}
- Focus on fixing the effective branch delta, not only uncommitted changes

Apply code changes directly in the repository.

Then update the implementation report by **appending** a new fix-round section to the existing file (do NOT overwrite or erase previous rounds):
- {implementation_report_path(ticket).as_posix()}

Steps:
1. Read the current content of implementation_report.md to determine how many fix rounds exist already.
2. Append a new section at the bottom using this heading (increment the round number accordingly):
   `## Fix Round N — <short description>`
3. The new section must include:
   - Summary of changes made in this round
   - Files modified
   - Key decisions
   - Commands/tests you ran
   - Review Issues Addressed (reference each issue explicitly)
   - QA Issues Addressed (reference each issue explicitly)

Important:
- Preserve all existing content in implementation_report.md — only append.
- Make the code changes directly in the repo.
- Be explicit about how each critical issue was fixed.
- If QA identified missing tests, add them when feasible and report them clearly.
"""
    prompt = build_role_prompt(ticket, "developer", task_instruction)
    write(dev_fix_prompt_path(ticket), prompt)
    set_artifact(ticket, "dev_fix_prompt", dev_fix_prompt_path(ticket))
    complete_stage(ticket, "dev_fix_prepare", "Generated dev-fix prompt.")
    print(f"[OK] Wrote {dev_fix_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it fix the issues and append a new fix-round section to implementation_report.md, then run next --run."
    )


def dev_complete(ticket: str) -> None:
    update_stage(ticket, "dev_complete")
    set_runner(ticket, "dev-complete")

    ensure_non_empty_files([implementation_report_path(ticket)], "dev_complete", ticket)
    set_artifact(ticket, "implementation_report", implementation_report_path(ticket))

    complete_stage(ticket, "dev_complete", "Implementation report verified.")
    print(f"[OK] Dev files verified for {ticket}")


def dev_fix_complete(ticket: str) -> None:
    update_stage(ticket, "dev_fix_complete")
    set_runner(ticket, "dev-fix-complete")

    ensure_non_empty_files(
        [implementation_report_path(ticket)], "dev_fix_complete", ticket
    )
    set_artifact(ticket, "implementation_report", implementation_report_path(ticket))

    complete_stage(ticket, "dev_fix_complete", "Fix implementation verified.")
    print(f"[OK] Dev fix verified for {ticket}")


def review_prepare(ticket: str) -> None:
    update_stage(ticket, "review_prepare")
    set_runner(ticket, "review-prepare")

    required_inputs = [
        task_spec_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
        implementation_report_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "review_prepare", ticket)

    base_branch = get_base_branch()
    followup_mode = (
        previous_review_report_path(ticket).exists()
        and read(previous_review_report_path(ticket)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_review_report_path(ticket)]
        if (
            review_fix_context_path(ticket).exists()
            and read(review_fix_context_path(ticket)).strip()
        ):
            extra_files.append(review_fix_context_path(ticket))

        followup_block = f"""

This is a follow-up review after a developer fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were fixed
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the fixes
- In the summary, explicitly state whether previous high-severity issues were resolved
- Treat this as a verification pass, not a blind fresh review
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Git review context:
- Compare the current branch against {base_branch}
- Review the effective ticket delta, including committed changes
- Use git diff, git log, and changed files as needed
- Do not limit review to uncommitted changes

Write valid JSON only directly to:
- {review_report_path(ticket).as_posix()}

Required JSON format:
{{
  "decision": "approve|request_changes|block",
  "issues": [
    {{
      "severity": "high|medium|low",
      "file": "...",
      "message": "..."
    }}
  ],
  "summary": "..."
}}

Review rules:
- List high severity issues first
- Tie findings to correctness, acceptance criteria, maintainability, or production risk
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "reviewer", task_instruction)
    write(review_prompt_path(ticket), prompt)
    set_artifact(ticket, "review_prompt", review_prompt_path(ticket))
    complete_stage(ticket, "review_prepare", "Generated review prompt.")
    print(f"[OK] Wrote {review_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write review_report.json directly, then run next --run."
    )


def review_complete(ticket: str) -> None:
    update_stage(ticket, "review_complete")
    set_runner(ticket, "review-complete")

    ensure_non_empty_files([review_report_path(ticket)], "review_complete", ticket)

    parsed = json.loads(read(review_report_path(ticket)))
    write(
        review_report_path(ticket),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_artifact(ticket, "review_report", review_report_path(ticket))

    build_fix_context(ticket)

    decision = parsed.get("decision", "unknown")
    complete_stage(ticket, "review_complete", f"Reviewer decision: {decision}")
    print(f"[OK] Review file verified for {ticket} ({decision})")


def qa_prepare(ticket: str) -> None:
    update_stage(ticket, "qa_prepare")
    set_runner(ticket, "qa-prepare")

    required_inputs = [
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
        implementation_report_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "qa_prepare", ticket)

    base_branch = get_base_branch()

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Git QA context:
- Compare the current branch against {base_branch}
- Evaluate the effective ticket delta, including committed changes
- Use git diff, git log, and changed files as needed
- Check likely regression areas impacted by this branch

Write valid JSON only directly to:
- {qa_report_path(ticket).as_posix()}

Required JSON format:
{{
  "decision": "pass|fail",
  "missing_tests": [],
  "risks": [],
  "summary": "..."
}}

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "qa", task_instruction)
    write(qa_prompt_path(ticket), prompt)
    set_artifact(ticket, "qa_prompt", qa_prompt_path(ticket))
    complete_stage(ticket, "qa_prepare", "Generated QA prompt.")
    print(f"[OK] Wrote {qa_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write qa_report.json directly, then run next --run."
    )


def qa_complete(ticket: str) -> None:
    update_stage(ticket, "qa_complete")
    set_runner(ticket, "qa-complete")

    ensure_non_empty_files([qa_report_path(ticket)], "qa_complete", ticket)

    parsed = json.loads(read(qa_report_path(ticket)))
    write(
        qa_report_path(ticket), json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    )
    set_artifact(ticket, "qa_report", qa_report_path(ticket))

    build_qa_fix_context(ticket)

    decision = parsed.get("decision", "unknown")
    complete_stage(ticket, "qa_complete", f"QA decision: {decision}")
    print(f"[OK] QA file verified for {ticket} ({decision})")


# ── EPIC WORKFLOW ──────────────────────────────────────────────────────────────

def epic_init(epic: str, requirement: str, domains: str = "") -> None:
    ensure_base_dirs()
    config = load_project_config()

    resolved_domains = [d.strip() for d in domains.split(",") if d.strip()]
    if not resolved_domains:
        resolved_domains = list(config.get("domains", {}).keys())

    valid_domains = set(config.get("domains", {}).keys())
    if resolved_domains:
        # Validate regardless of whether any valid domains exist in the config.
        # An empty config means there are no valid domains, so any explicit request
        # for a specific domain must be rejected with a clear error.
        unknown = [d for d in resolved_domains if d not in valid_domains]
        if unknown:
            valid_label = ", ".join(sorted(valid_domains)) if valid_domains else "(none defined in project_config.json)"
            print(
                f"[ERROR] Unknown domain(s): {', '.join(unknown)}. "
                f"Valid domains: {valid_label}"
            )
            sys.exit(1)

    ensure_epic_dirs(epic)

    write(epic_input_file(epic), requirement.strip() + "\n")
    save_epic_status(epic, init_epic_status(epic, resolved_domains))
    set_epic_artifact(epic, "epic_input", epic_input_file(epic))
    print(f"[OK] Initialized epic {epic} at {epic_path(epic)} (domains={resolved_domains})")


def epic_analysis_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_analysis_prepare")
    set_epic_runner(epic, "epic-analysis-prepare")

    ensure_non_empty_epic_files([epic_input_file(epic)], "epic_analysis_prepare", epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list([epic_input_file(epic)])}

Analyze the epic requirement and write a comprehensive analysis directly to:
- {epic_analysis_path(epic).as_posix()}

The analysis must include:
1. Problem statement — restate the epic in your own words
2. Goals — primary objectives and success metrics
3. Scope — what is in and out of scope
4. Key stakeholders or user personas affected
5. High-level solution areas — major functional areas to address
6. Open questions — unknowns that must be resolved before design

Important:
- Write the analysis directly to the file above.
- Do not reply in chat with the final content.
- Keep the analysis concise but thorough.
"""
    prompt = build_epic_role_prompt(epic, "epic_analyst", task_instruction)
    write(epic_analysis_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_analysis_prompt", epic_analysis_prompt_path(epic))
    complete_epic_stage(epic, "epic_analysis_prepare", "Generated epic analysis prompt.")
    print(f"[OK] Wrote {epic_analysis_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_analysis.md, then run epic-next --run."
    )


def epic_analysis_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_analysis_complete")
    set_epic_runner(epic, "epic-analysis-complete")

    ensure_non_empty_epic_files([epic_analysis_path(epic)], "epic_analysis_complete", epic)
    set_epic_artifact(epic, "epic_analysis", epic_analysis_path(epic))

    complete_epic_stage(epic, "epic_analysis_complete", "Epic analysis verified.")
    print(f"[OK] Epic analysis verified for {epic}")


def epic_design_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_design_prepare")
    set_epic_runner(epic, "epic-design-prepare")

    required_inputs = [epic_input_file(epic), epic_analysis_path(epic)]
    ensure_non_empty_epic_files(required_inputs, "epic_design_prepare", epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Produce a detailed epic design document and write it directly to:
- {epic_design_path(epic).as_posix()}

The design must include:
1. Solution overview — high-level approach and architecture
2. Key design decisions — rationale for major choices
3. Component breakdown — major components or services involved
4. Data flow — how information moves through the system
5. Integration points — external systems or APIs affected
6. Risks and trade-offs — known risks and mitigation strategies
7. Out of scope — explicit exclusions from this epic

Important:
- Write the design directly to the file above.
- Do not reply in chat with the final content.
"""
    prompt = build_epic_role_prompt(epic, "epic_designer", task_instruction)
    write(epic_design_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_design_prompt", epic_design_prompt_path(epic))
    complete_epic_stage(epic, "epic_design_prepare", "Generated epic design prompt.")
    print(f"[OK] Wrote {epic_design_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_design.md, then run epic-next --run."
    )


def epic_design_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_design_complete")
    set_epic_runner(epic, "epic-design-complete")

    ensure_non_empty_epic_files([epic_design_path(epic)], "epic_design_complete", epic)
    set_epic_artifact(epic, "epic_design", epic_design_path(epic))

    complete_epic_stage(epic, "epic_design_complete", "Epic design verified.")
    print(f"[OK] Epic design verified for {epic}")


def epic_review_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_review_prepare")
    set_epic_runner(epic, "epic-review-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_review_prepare", epic)

    followup_mode = (
        previous_epic_review_path(epic).exists()
        and read(previous_epic_review_path(epic)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_epic_review_path(epic)]
        if (
            epic_review_fix_context_path(epic).exists()
            and read(epic_review_fix_context_path(epic)).strip()
        ):
            extra_files.append(epic_review_fix_context_path(epic))

        followup_block = f"""

This is a follow-up review after a designer fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were addressed in the updated design
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the revisions
- In the summary, explicitly state whether previous high-severity issues were resolved
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Review the epic design for completeness, feasibility, and alignment with the stated requirements.

Write valid JSON only directly to:
- {epic_review_report_path(epic).as_posix()}

Required JSON format:
{{
  "decision": "approve|request_changes|block",
  "issues": [
    {{
      "severity": "high|medium|low",
      "area": "...",
      "message": "..."
    }}
  ],
  "summary": "..."
}}

Review rules:
- List high severity issues first
- Tie findings to feasibility, completeness, or alignment with requirements
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_epic_role_prompt(epic, "epic_reviewer", task_instruction)
    write(epic_review_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_review_prompt", epic_review_prompt_path(epic))
    complete_epic_stage(epic, "epic_review_prepare", "Generated epic review prompt.")
    print(f"[OK] Wrote {epic_review_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_review.json, then run epic-next --run."
    )


def epic_review_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_review_complete")
    set_epic_runner(epic, "epic-review-complete")

    ensure_non_empty_epic_files([epic_review_report_path(epic)], "epic_review_complete", epic)

    parsed = json.loads(read(epic_review_report_path(epic)))
    write(
        epic_review_report_path(epic),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_epic_artifact(epic, "epic_review_report", epic_review_report_path(epic))

    build_epic_review_fix_context(epic)

    decision = parsed.get("decision", "unknown")
    complete_epic_stage(epic, "epic_review_complete", f"Epic reviewer decision: {decision}")
    print(f"[OK] Epic review verified for {epic} ({decision})")


def epic_design_fix_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_design_fix_prepare")
    set_epic_runner(epic, "epic-design-fix-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_design_fix_prepare", epic)

    if not epic_review_report_path(epic).exists() or not read(epic_review_report_path(epic)).strip():
        fail_epic_stage(epic, "epic_design_fix_prepare", "No epic_review.json found")
        raise FileNotFoundError("No epic_review.json found for epic design fix mode")

    # Archive the review report (fix context was already written by epic_review_complete)
    archived_review = previous_epic_review_path(epic)
    write(archived_review, read(epic_review_report_path(epic)))
    epic_review_report_path(epic).unlink(missing_ok=True)
    set_epic_artifact(epic, "previous_epic_review", archived_review)

    fix_ctx = epic_review_fix_context_path(epic)
    extra_paths: List[Path] = [archived_review]
    if fix_ctx.exists():
        extra_paths.append(fix_ctx)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs + extra_paths)}

Your task is to revise the epic design to address all review findings.

Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Do NOT redesign from scratch — revise the existing design document
- Preserve sections that were not flagged as problematic
- Be explicit in the design about how each major issue was addressed

Overwrite the epic design file with the corrected version:
- {epic_design_path(epic).as_posix()}

Important:
- Write the updated design directly to the file above.
- Do not reply in chat with the final content.
"""
    prompt = build_epic_role_prompt(epic, "epic_designer", task_instruction)
    write(epic_design_fix_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_design_fix_prompt", epic_design_fix_prompt_path(epic))
    complete_epic_stage(epic, "epic_design_fix_prepare", "Generated epic design fix prompt.")
    print(f"[OK] Wrote {epic_design_fix_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it update epic_design.md, then run epic-next --run."
    )


def epic_design_fix_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_design_fix_complete")
    set_epic_runner(epic, "epic-design-fix-complete")

    ensure_non_empty_epic_files([epic_design_path(epic)], "epic_design_fix_complete", epic)
    set_epic_artifact(epic, "epic_design", epic_design_path(epic))

    complete_epic_stage(epic, "epic_design_fix_complete", "Epic design fix verified.")
    print(f"[OK] Epic design fix verified for {epic}")


def epic_breakdown_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_breakdown_prepare")
    set_epic_runner(epic, "epic-breakdown-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_breakdown_prepare", epic)

    if not epic_review_report_path(epic).exists() or not read(epic_review_report_path(epic)).strip():
        fail_epic_stage(epic, "epic_breakdown_prepare", "No approved epic_review.json found")
        raise FileNotFoundError(
            "No epic_review.json found. Run epic-review-complete first."
        )

    try:
        review = json.loads(read(epic_review_report_path(epic)))
    except Exception:
        fail_epic_stage(epic, "epic_breakdown_prepare", "epic_review.json is not valid JSON")
        raise

    if review.get("decision") != "approve":
        fail_epic_stage(
            epic,
            "epic_breakdown_prepare",
            f"Review decision is '{review.get('decision')}', not 'approve'",
        )
        raise ValueError(
            f"Cannot run breakdown: review decision is '{review.get('decision')}'. Must be 'approve'."
        )

    tickets_dir = epic_tickets_dir(epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Break the epic down into a structured set of user stories and tickets.

Write the story map directly to:
- {epic_story_map_path(epic).as_posix()}

Write individual ticket files directly to:
- {tickets_dir.as_posix()}/<US-NNN-short-slug>.md

## Story Map Requirements

1. List all user stories in priority order
2. Group stories by theme or functional area
3. Note dependencies between stories
4. If any quality concerns are detected (overlap, oversize, vague AC), add a `## Quality Notes` section listing each issue with: ticket ID, concern type, and severity (high/medium/low)

## Ticket File Requirements

- Filename format: US-NNN-<slug>.md (e.g. US-001-add-cli-commands.md)
- Each ticket file MUST contain all of the following sections using exact `##` level headers:

  ```
  ## Summary
  ## Goal
  ## Scope
  ## Out of Scope
  ## Acceptance Criteria
  ## Dependencies
  ## Suggested Order
  ## Domain
  ## Notes
  ```

- `## Goal` — must be non-empty; state what this ticket achieves
- `## Scope` — must be non-empty; list exactly what is included
- `## Acceptance Criteria` — must contain at least two concrete, testable criteria (not placeholders like "works correctly")
- `## Domain` — must be set to one of the configured project domains

## Quality Requirements

Before writing output, apply the self-review checklist:
- Every ticket is estimable within 1–3 days
- No two tickets share overlapping scope (same files, same API endpoints, same data model fields)
- Every ticket has at least two concrete, testable Acceptance Criteria
- `## Goal` and `## Scope` are distinct and non-empty in every ticket
- No ticket title is a vague action phrase (e.g. "Improve X", "Refactor Y")
- Do NOT produce god tickets (covering multiple features) or layer-split tickets without independent user value

## Important

- Write the story map and all ticket files directly.
- Do not reply in chat with the final content.
- Create at least one ticket file in {tickets_dir.as_posix()}.
"""
    prompt = build_epic_role_prompt(epic, "epic_planner", task_instruction)
    write(epic_breakdown_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_breakdown_prompt", epic_breakdown_prompt_path(epic))
    complete_epic_stage(epic, "epic_breakdown_prepare", "Generated epic breakdown prompt.")
    print(f"[OK] Wrote {epic_breakdown_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_story_map.md and ticket files, then run epic-next --run."
    )


def epic_breakdown_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_breakdown_complete")
    set_epic_runner(epic, "epic-breakdown-complete")

    ensure_non_empty_epic_files([epic_story_map_path(epic)], "epic_breakdown_complete", epic)

    ticket_files = list(epic_tickets_dir(epic).glob("*.md"))
    if not ticket_files:
        fail_epic_stage(
            epic,
            "epic_breakdown_complete",
            "No ticket files found in breakdown/tickets/",
        )
        raise FileNotFoundError(
            f"No ticket files found in {epic_tickets_dir(epic).as_posix()}. "
            "The epic_planner must write at least one *.md file there."
        )

    # AC-7: verify each ticket file has a non-empty ## Domain section
    initialized_domains = set(get_epic_domains(epic))
    domain_errors = []
    for tf in ticket_files:
        content = tf.read_text(encoding="utf-8")
        # Find ## Domain header and extract the value on the next non-blank line
        domain_value = ""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("## domain"):
                # collect lines after the header until the next ## heading or EOF
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped.startswith("#"):
                        break
                    if stripped:
                        domain_value = stripped
                        break
                break
        if not domain_value:
            domain_errors.append(f"  {tf.name}: missing or empty '## Domain' section")
        elif initialized_domains and domain_value not in initialized_domains:
            domain_errors.append(
                f"  {tf.name}: '## Domain' value '{domain_value}' is not one of the "
                f"initialized domains ({', '.join(sorted(initialized_domains))})"
            )

    if domain_errors:
        msg = "Ticket file(s) failed ## Domain validation:\n" + "\n".join(domain_errors)
        fail_epic_stage(epic, "epic_breakdown_complete", msg)
        raise ValueError(msg)

    # Validate ## Goal, ## Scope, ## Acceptance Criteria are non-empty in each ticket
    def _section_is_non_empty(lines: list, header: str) -> bool:
        """Return True if the named ## section exists and has at least one non-blank line."""
        header_lower = header.lower()
        in_section = False
        for line in lines:
            if line.strip().lower() == header_lower:
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    return False  # reached next section without content
                if line.strip():
                    return True  # found non-blank content
        return False

    section_errors = []
    required_sections = ["## Goal", "## Scope", "## Acceptance Criteria"]
    for tf in ticket_files:
        lines = tf.read_text(encoding="utf-8").splitlines()
        for section in required_sections:
            if not _section_is_non_empty(lines, section):
                section_errors.append(f"  {tf.name}: missing or empty '{section}' section")

    if section_errors:
        msg = "Ticket file(s) failed section validation:\n" + "\n".join(section_errors)
        fail_epic_stage(epic, "epic_breakdown_complete", msg)
        raise ValueError(msg)

    set_epic_artifact(epic, "epic_story_map", epic_story_map_path(epic))
    set_epic_artifact(epic, "epic_tickets_dir", epic_tickets_dir(epic))

    complete_epic_stage(
        epic,
        "epic_breakdown_complete",
        f"Epic breakdown verified. {len(ticket_files)} ticket(s) found.",
    )
    print(f"[OK] Epic breakdown verified for {epic} ({len(ticket_files)} ticket(s))")


def epic_current_review_decision(epic: str) -> Optional[str]:
    try:
        if epic_review_report_path(epic).exists():
            return json.loads(read(epic_review_report_path(epic))).get("decision")
    except Exception:
        pass
    return None


def epic_next_action(epic: str) -> str:
    current_stage = load_epic_status(epic).get("current_stage", "")
    review_decision = epic_current_review_decision(epic)

    # Analysis
    if not epic_analysis_path(epic).exists() or not read(epic_analysis_path(epic)).strip():
        if epic_analysis_prompt_path(epic).exists():
            return "epic-analysis-complete"
        return "epic-analysis-prepare"

    if current_stage == "epic_analysis_prepare":
        return "epic-analysis-complete"

    # Design
    if not epic_design_path(epic).exists() or not read(epic_design_path(epic)).strip():
        if epic_design_prompt_path(epic).exists():
            return "epic-design-complete"
        return "epic-design-prepare"

    if current_stage == "epic_design_prepare":
        return "epic-design-complete"

    # Fix loop — check current_stage first, before reading review_decision,
    # because epic_design_fix_prepare deletes epic_review.json which makes
    # review_decision None, causing the review_decision guard to miss this branch.
    if current_stage == "epic_design_fix_prepare":
        return "epic-design-fix-complete"

    if current_stage == "epic_design_fix_complete":
        return "epic-review-prepare"

    if review_decision in {"request_changes", "block"}:
        return "epic-design-fix-prepare"

    # Review
    if not epic_review_report_path(epic).exists() or not read(epic_review_report_path(epic)).strip():
        return "epic-review-prepare"

    if current_stage == "epic_review_prepare":
        return "epic-review-complete"

    # Breakdown after approved review
    if review_decision == "approve":
        if not epic_story_map_path(epic).exists() or not read(epic_story_map_path(epic)).strip():
            if current_stage == "epic_breakdown_prepare":
                return "epic-breakdown-complete"
            return "epic-breakdown-prepare"

        if list(epic_tickets_dir(epic).glob("*.md")):
            return "done"

    return "done"


def run_named_epic_step(epic: str, step: str) -> None:
    mapping = {
        "epic-analysis-prepare": epic_analysis_prepare,
        "epic-analysis-complete": epic_analysis_complete,
        "epic-design-prepare": epic_design_prepare,
        "epic-design-complete": epic_design_complete,
        "epic-review-prepare": epic_review_prepare,
        "epic-review-complete": epic_review_complete,
        "epic-design-fix-prepare": epic_design_fix_prepare,
        "epic-design-fix-complete": epic_design_fix_complete,
        "epic-breakdown-prepare": epic_breakdown_prepare,
        "epic-breakdown-complete": epic_breakdown_complete,
    }
    if step == "done":
        print("Epic looks complete. Review the story map and ticket files.")
        return
    if step not in mapping:
        raise ValueError(f"Unknown epic step: {step}")
    mapping[step](epic)


_EPIC_PREPARE_STEP_PROMPT: Dict[str, object] = {
    "epic-analysis-prepare": epic_analysis_prompt_path,
    "epic-design-prepare": epic_design_prompt_path,
    "epic-design-fix-prepare": epic_design_fix_prompt_path,
    "epic-review-prepare": epic_review_prompt_path,
    "epic-breakdown-prepare": epic_breakdown_prompt_path,
}


def epic_next_step(epic: str, execute: bool = False, run_auto: bool = False) -> None:
    step = epic_next_action(epic)
    if run_auto or execute:
        run_named_epic_step(epic, step)
        if run_auto and step in _EPIC_PREPARE_STEP_PROMPT:
            prompt_path = _EPIC_PREPARE_STEP_PROMPT[step](epic)  # type: ignore[operator]
            spawn_claude_wezterm(prompt_path, str(Path.cwd()))
    else:
        print(step)


def show_epic_status(epic: str) -> None:
    print(json.dumps(load_epic_status(epic), indent=2, ensure_ascii=False))


# ── TICKET WORKFLOW ROUTING ────────────────────────────────────────────────────

def current_outcome(ticket: str) -> Dict[str, Optional[str]]:
    review_decision = None
    qa_decision = None

    try:
        if review_report_path(ticket).exists():
            review_decision = json.loads(read(review_report_path(ticket))).get(
                "decision"
            )
    except Exception:
        pass

    try:
        if qa_report_path(ticket).exists():
            qa_decision = json.loads(read(qa_report_path(ticket))).get("decision")
    except Exception:
        pass

    return {"review": review_decision, "qa": qa_decision}


def next_action(ticket: str) -> str:
    outcome = current_outcome(ticket)
    current_stage = load_status(ticket).get("current_stage", "")

    # Architect
    if not task_spec_path(ticket).exists() or not read(task_spec_path(ticket)).strip():
        return "architect-prepare"

    if (
        not design_note_path(ticket).exists()
        or not read(design_note_path(ticket)).strip()
    ):
        return "architect-complete"

    if current_stage == "architect_prepare":
        return "architect-complete"

    # Architect review gate
    # Check fix stages first (architect_review.json may still hold an old decision)
    if current_stage == "architect_fix_prepare":
        return "architect-fix-complete"

    if current_stage == "architect_fix_complete":
        return "architect-review-prepare"

    arch_review = architect_review_report_path(ticket)
    arch_review_exists = arch_review.exists() and read(arch_review).strip()

    if not arch_review_exists:
        if current_stage == "architect_review_prepare":
            return "architect-review-complete"
        return "architect-review-prepare"

    if current_stage == "architect_review_prepare":
        return "architect-review-complete"

    arch_review_decision = None
    try:
        arch_review_decision = json.loads(read(arch_review)).get("decision")
    except Exception:
        return "architect-review-prepare"

    if arch_review_decision in {"request_changes", "block"}:
        return "architect-fix-prepare"

    if arch_review_decision != "approve":
        # Unknown decision — safe default: treat as fix needed
        return "architect-fix-prepare"

    # arch_review_decision == "approve" → proceed to dev workflow

    # Review fail -> fix loop
    if outcome["review"] in {"request_changes", "block"}:
        if current_stage == "dev_fix_prepare":
            return "dev-fix-complete"
        return "dev-fix-prepare"

    # QA fail -> fix loop
    if current_stage == "dev_fix_complete":
        return "review-prepare"
    if outcome["qa"] == "fail":
        if current_stage == "dev_fix_prepare":
            return "dev-fix-complete"
        return "dev-fix-prepare"

    # After fix complete, always go back to review
    if current_stage == "dev_fix_complete":
        return "review-prepare"

    # Initial dev
    if (
        not implementation_report_path(ticket).exists()
        or not read(implementation_report_path(ticket)).strip()
    ):
        return "dev-prepare"

    if current_stage == "dev_prepare":
        return "dev-complete"

    # Review
    if (
        not review_report_path(ticket).exists()
        or not read(review_report_path(ticket)).strip()
    ):
        return "review-prepare"

    if current_stage == "review_prepare":
        return "review-complete"

    # QA after approved review
    if outcome["review"] == "approve":
        if (
            not qa_report_path(ticket).exists()
            or not read(qa_report_path(ticket)).strip()
        ):
            return "qa-prepare"

        if current_stage == "qa_prepare":
            return "qa-complete"

        if outcome["qa"] == "pass":
            return "done"

        if outcome["qa"] is None:
            return "qa-complete"

    return "done"


def run_named_step(ticket: str, step: str) -> None:
    mapping = {
        "architect-prepare": architect_prepare,
        "architect-complete": architect_complete,
        "architect-review-prepare": architect_review_prepare,
        "architect-review-complete": architect_review_complete,
        "architect-fix-prepare": architect_fix_prepare,
        "architect-fix-complete": architect_fix_complete,
        "dev-prepare": dev_prepare,
        "dev-fix-prepare": dev_fix_prepare,
        "dev-fix-complete": dev_fix_complete,
        "dev-complete": dev_complete,
        "review-prepare": review_prepare,
        "review-complete": review_complete,
        "qa-prepare": qa_prepare,
        "qa-complete": qa_complete,
    }
    if step == "done":
        print("Ticket looks ready. Review and merge manually.")
        return
    if step not in mapping:
        raise ValueError(f"Unknown step: {step}")
    mapping[step](ticket)


_PREPARE_STEP_PROMPT: Dict[str, object] = {
    "architect-prepare": architect_prompt_path,
    "architect-review-prepare": architect_review_prompt_path,
    "architect-fix-prepare": architect_fix_prompt_path,
    "dev-prepare": dev_prompt_path,
    "dev-fix-prepare": dev_fix_prompt_path,
    "review-prepare": review_prompt_path,
    "qa-prepare": qa_prompt_path,
}


def spawn_claude_wezterm(
    prompt_path: Path, cwd: str, wait_seconds: float = 4.0
) -> None:
    result = subprocess.run(
        [
            "wezterm",
            "cli",
            "spawn",
            "--cwd",
            cwd,
            "--",
            "claude",
            "--dangerously-skip-permissions",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[WARN] wezterm spawn failed: {result.stderr.strip()}", file=sys.stderr)
        return

    pane_id = result.stdout.strip()
    if not pane_id:
        print(
            "[WARN] Could not get WezTerm pane ID, skipping auto-paste.",
            file=sys.stderr,
        )
        return

    print(
        f"[AUTO] Spawned Claude in WezTerm pane {pane_id}. Waiting {wait_seconds}s for it to load..."
    )
    time.sleep(wait_seconds)

    prompt_text = prompt_path.read_text(encoding="utf-8").rstrip("\n")
    subprocess.run(
        ["wezterm", "cli", "send-text", "--pane-id", pane_id, "--no-paste"],
        input=prompt_text,
        text=True,
    )
    print(f"[AUTO] Prompt pasted into pane {pane_id}. Press Enter in Claude to submit.")


def next_step(ticket: str, execute: bool = False, run_auto: bool = False) -> None:
    step = next_action(ticket)
    if run_auto or execute:
        run_named_step(ticket, step)
        if run_auto and step in _PREPARE_STEP_PROMPT:
            prompt_path = _PREPARE_STEP_PROMPT[step](ticket)  # type: ignore[operator]
            spawn_claude_wezterm(prompt_path, str(Path.cwd()))
    else:
        print(step)


def show_status(ticket: str) -> None:
    print(json.dumps(load_status(ticket), indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reusable file-referenced prepare/complete workflow for local AI agent team."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a ticket run.")
    p_init.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_init.add_argument("requirement", help="Initial input text")
    p_init.add_argument(
        "--domain",
        default="",
        help="Optional domain override, e.g. backend or frontend",
    )

    for cmd in [
        "architect-prepare",
        "architect-complete",
        "architect-review-prepare",
        "architect-review-complete",
        "architect-fix-prepare",
        "architect-fix-complete",
        "dev-prepare",
        "dev-fix-prepare",
        "dev-fix-complete",
        "dev-complete",
        "review-prepare",
        "review-complete",
        "qa-prepare",
        "qa-complete",
        "status",
    ]:
        p = sub.add_parser(cmd, help=f"Run {cmd}")
        p.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")

    p_next = sub.add_parser("next", help="Show or run the next step.")
    p_next.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_next.add_argument(
        "--run",
        action="store_true",
        help="Execute the next step instead of only printing it.",
    )
    p_next.add_argument(
        "--run-auto",
        action="store_true",
        help="Execute the next step and automatically open Claude in a new WezTerm tab with the prompt pre-loaded.",
    )

    # ── Epic subcommands ──────────────────────────────────────────────────────
    p_epic_init = sub.add_parser("epic-init", help="Initialize an epic run.")
    p_epic_init.add_argument("epic", help="Epic ID, e.g. EPIC-001")
    p_epic_init.add_argument("requirement", help="Initial epic requirement text")
    p_epic_init.add_argument(
        "--domains",
        default="",
        metavar="DOMAINS",
        help="Comma-separated domains, e.g. backend,frontend. Defaults to all domains in config.",
    )
    p_epic_init.add_argument(
        "--domain",
        default="",
        metavar="DOMAIN",
        help="[DEPRECATED] Use --domains instead. Kept for backward compatibility.",
    )

    for cmd in [
        "epic-analysis-prepare",
        "epic-analysis-complete",
        "epic-design-prepare",
        "epic-design-complete",
        "epic-review-prepare",
        "epic-review-complete",
        "epic-design-fix-prepare",
        "epic-design-fix-complete",
        "epic-breakdown-prepare",
        "epic-breakdown-complete",
        "epic-status",
    ]:
        p = sub.add_parser(cmd, help=f"Run {cmd}")
        p.add_argument("epic", help="Epic ID, e.g. EPIC-001")

    p_epic_next = sub.add_parser("epic-next", help="Show or run the next epic step.")
    p_epic_next.add_argument("epic", help="Epic ID, e.g. EPIC-001")
    p_epic_next.add_argument(
        "--run",
        action="store_true",
        help="Execute the next epic step instead of only printing it.",
    )
    p_epic_next.add_argument(
        "--run-auto",
        action="store_true",
        help="Execute the next epic step and automatically open Claude in a new WezTerm tab.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init":
            init_ticket(args.ticket, args.requirement, domain=args.domain)
        elif args.command == "architect-prepare":
            architect_prepare(args.ticket)
        elif args.command == "architect-complete":
            architect_complete(args.ticket)
        elif args.command == "architect-review-prepare":
            architect_review_prepare(args.ticket)
        elif args.command == "architect-review-complete":
            architect_review_complete(args.ticket)
        elif args.command == "architect-fix-prepare":
            architect_fix_prepare(args.ticket)
        elif args.command == "architect-fix-complete":
            architect_fix_complete(args.ticket)
        elif args.command == "dev-prepare":
            dev_prepare(args.ticket)
        elif args.command == "dev-fix-prepare":
            dev_fix_prepare(args.ticket)
        elif args.command == "dev-fix-complete":
            dev_fix_complete(args.ticket)
        elif args.command == "dev-complete":
            dev_complete(args.ticket)
        elif args.command == "review-prepare":
            review_prepare(args.ticket)
        elif args.command == "review-complete":
            review_complete(args.ticket)
        elif args.command == "qa-prepare":
            qa_prepare(args.ticket)
        elif args.command == "qa-complete":
            qa_complete(args.ticket)
        elif args.command == "status":
            show_status(args.ticket)
        elif args.command == "next":
            next_step(args.ticket, execute=args.run, run_auto=args.run_auto)
        elif args.command == "epic-init":
            domains_arg = args.domains
            if not domains_arg and getattr(args, "domain", ""):
                print(
                    "[DEPRECATED] --domain is deprecated for epic-init; use --domains instead."
                )
                domains_arg = args.domain
            epic_init(args.epic, args.requirement, domains=domains_arg)
        elif args.command == "epic-analysis-prepare":
            epic_analysis_prepare(args.epic)
        elif args.command == "epic-analysis-complete":
            epic_analysis_complete(args.epic)
        elif args.command == "epic-design-prepare":
            epic_design_prepare(args.epic)
        elif args.command == "epic-design-complete":
            epic_design_complete(args.epic)
        elif args.command == "epic-review-prepare":
            epic_review_prepare(args.epic)
        elif args.command == "epic-review-complete":
            epic_review_complete(args.epic)
        elif args.command == "epic-design-fix-prepare":
            epic_design_fix_prepare(args.epic)
        elif args.command == "epic-design-fix-complete":
            epic_design_fix_complete(args.epic)
        elif args.command == "epic-breakdown-prepare":
            epic_breakdown_prepare(args.epic)
        elif args.command == "epic-breakdown-complete":
            epic_breakdown_complete(args.epic)
        elif args.command == "epic-status":
            show_epic_status(args.epic)
        elif args.command == "epic-next":
            epic_next_step(args.epic, execute=args.run, run_auto=args.run_auto)
        else:
            parser.print_help()
            return 2
    except KeyboardInterrupt:
        print("\n[ABORTED]")
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
