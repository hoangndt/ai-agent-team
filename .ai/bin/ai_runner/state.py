"""File I/O, status.json and project_config.json loading, and stage transitions."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .constants import (
    AGENTS, ARCH_INIT_TICKET, ARCH_REFRESH_TICKET, BASE, ENGINE_REGISTRY, RUNS,
)
from .paths import (
    adr_distill_dir, architect_dir, dev_dir, distill_dir, epic_analysis_dir,
    epic_breakdown_dir, epic_design_dir, epic_fix_dir, epic_input_dir, epic_path,
    epic_review_dir, epic_status_file, epic_tickets_dir, fix_dir, input_dir, input_file,
    now, project_config_path, qa_dir, review_dir, run_path, status_file,
)


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
        distill_dir(ticket),
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
        adr_distill_dir(epic),
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


def resolve_engine(engine_flag: Optional[str]) -> str:
    name = engine_flag or load_project_config().get("engine", {}).get("default", "claude")
    if name not in ENGINE_REGISTRY:
        print(
            f"[ERROR] Unknown engine: {name!r}. Known engines: {list(ENGINE_REGISTRY)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return name


def get_base_branch() -> str:
    cfg = load_project_config()
    return cfg.get("git", {}).get("base_branch", "main")


def init_status(ticket: str, domain: str, domains: Optional[List[str]] = None) -> Dict:
    ts = now()
    status: Dict = {
        "ticket": ticket,
        "domain": domain,
        "current_stage": "init",
        "state": "ready",
        "updated_at": ts,
        "artifacts": {},
        "history": [{"stage": "init", "status": "done", "time": ts}],
        "runner": {"mode": "file_referenced_prompts", "last_command": None},
    }
    if domains and len(domains) > 1:
        status["domains"] = list(domains)
    return status


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


def init_ticket(
    ticket: str, requirement: str, domain: str = "", domains: Optional[List[str]] = None
) -> None:
    ensure_base_dirs()
    config = load_project_config()
    resolved_domain = domain or config.get("default_domain", "backend")

    ensure_ticket_dirs(ticket)

    write(input_file(ticket), requirement.strip() + "\n")
    save_status(ticket, init_status(ticket, resolved_domain, domains))
    set_artifact(ticket, "input", input_file(ticket))
    label = f"domain={resolved_domain}"
    if domains and len(domains) > 1:
        label = f"domains={','.join(domains)}"
    print(f"[OK] Initialized {ticket} at {run_path(ticket)} ({label})")


def ensure_arch_init_status() -> None:
    """Create the sentinel run's status.json on first use; no-op on re-run.

    arch-init has no CLI ticket id, but every reused status/prompt helper
    (update_stage, complete_stage, fail_stage, ensure_non_empty_files,
    build_project_context, get_effective_role_skills) requires one. Reusing
    ARCH_INIT_TICKET here makes run_path/status_file resolve to an ordinary
    per-ticket run directory, so none of those helpers need ticket-less variants.
    """
    if status_file(ARCH_INIT_TICKET).exists():
        return
    ensure_base_dirs()
    run_path(ARCH_INIT_TICKET).mkdir(parents=True, exist_ok=True)
    default_domain = load_project_config().get("default_domain", "backend")
    save_status(ARCH_INIT_TICKET, init_status(ARCH_INIT_TICKET, default_domain))


def ensure_arch_refresh_status() -> None:
    """Create the sentinel run's status.json on first use; no-op on re-run.

    Mirrors ensure_arch_init_status() with a distinct sentinel id so the two
    ticket-less operator commands don't share/clobber the same status.json.
    """
    if status_file(ARCH_REFRESH_TICKET).exists():
        return
    ensure_base_dirs()
    run_path(ARCH_REFRESH_TICKET).mkdir(parents=True, exist_ok=True)
    default_domain = load_project_config().get("default_domain", "backend")
    save_status(ARCH_REFRESH_TICKET, init_status(ARCH_REFRESH_TICKET, default_domain))
