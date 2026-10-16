#!/usr/bin/env python3
"""
Read-only sidecar for the Claude slash-command wrapper.

Reuses the runner's own routing (`ai_run.next_action` / `ai_run.epic_next_action`)
and emits machine-readable routing info. It never mutates run state and has no
--run/--run-auto options. Run from the project root, like ai_run.py.

    python .ai/bin/ai_wrap.py next <TICKET> --json
    python .ai/bin/ai_wrap.py epic-next <EPIC> --json
    python .ai/bin/ai_wrap.py validate-id <ID>

`prompt_path` is null when kind=prepare and state=failed; re-query `next --json`
after a successful re-prepare to get the real path.

`missing_outputs` is a file-presence check only. It never predicts whether the
runner's `*-complete` step will pass. These completes also validate content:

    dev-complete, dev-fix-complete            "## Architecture Impact" heading
    architect-review/review/qa/epic-review    strict JSON parse + decision value
    epic-breakdown-complete                   ticket naming + "## Domain" sections
    distill-complete                          vault line caps + retry state
    adr-distill-complete                      ADR frontmatter validity
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ai_run  # noqa: E402

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
DECISION_RE = re.compile(r"decision: (\w+)")

# Complete step -> required output paths (file presence / non-empty only).
_TICKET_OUTPUTS: Dict[str, Callable[[str], List[Path]]] = {
    "architect-complete": lambda t: [
        ai_run.task_spec_path(t),
        ai_run.design_note_path(t),
        ai_run.acceptance_criteria_path(t),
        ai_run.assumptions_path(t),
    ],
    "architect-fix-complete": lambda t: [
        ai_run.task_spec_path(t),
        ai_run.design_note_path(t),
        ai_run.acceptance_criteria_path(t),
        ai_run.assumptions_path(t),
    ],
    "architect-review-complete": lambda t: [ai_run.architect_review_report_path(t)],
    "dev-complete": lambda t: [ai_run.implementation_report_path(t)],
    "dev-fix-complete": lambda t: [ai_run.implementation_report_path(t)],
    "review-complete": lambda t: [ai_run.review_report_path(t)],
    "qa-complete": lambda t: [ai_run.qa_report_path(t)],
}

_EPIC_OUTPUTS: Dict[str, Callable[[str], List[Path]]] = {
    "epic-analysis-complete": lambda e: [ai_run.epic_analysis_path(e)],
    "epic-design-complete": lambda e: [ai_run.epic_design_path(e)],
    "epic-design-fix-complete": lambda e: [ai_run.epic_design_path(e)],
    "epic-review-complete": lambda e: [ai_run.epic_review_report_path(e)],
}


def _empty(path: Path) -> bool:
    return not path.exists() or not ai_run.read(path).strip()


def _distill_paths(ticket: str) -> List[Path]:
    root = ai_run.vault_root()
    if root is None:
        return []
    domain = ai_run.get_ticket_domain(ticket)
    return [
        root / "architecture" / "system-overview.md",
        root / "architecture" / "modules" / f"{domain}.md",
    ]


def _adr_paths(epic: str) -> List[Path]:
    root = ai_run.vault_root()
    start = ai_run.load_epic_status(epic).get("adr_distill_start_id")
    if root is None or not start:
        return []
    decisions = root / "architecture" / "decisions"
    if not decisions.is_dir():
        return []
    out = []
    for p in sorted(decisions.iterdir()):
        m = re.match(r"^ADR-(\d{3})", p.name)
        if p.is_file() and m and int(m.group(1)) >= int(start):
            out.append(p)
    return out


def missing_outputs(step: str, ident: str, epic: bool) -> List[str]:
    """Repo-relative paths of required outputs of a complete step that are absent/empty."""
    missing: List[Path] = []
    if epic and step == "epic-breakdown-complete":
        for p in (ai_run.epic_story_map_path(ident), ai_run.epic_story_status_path(ident)):
            if _empty(p):
                missing.append(p)
        tickets = ai_run.epic_tickets_dir(ident)
        if not (tickets.is_dir() and list(tickets.glob("*.md"))):
            missing.append(tickets / "*.md")
    elif epic and step == "adr-distill-complete":
        missing = [p for p in _adr_paths(ident) if _empty(p)]
    elif not epic and step == "distill-complete":
        missing = [p for p in _distill_paths(ident) if _empty(p)]
    else:
        table = _EPIC_OUTPUTS if epic else _TICKET_OUTPUTS
        resolver = table.get(step)
        if resolver:
            missing = [p for p in resolver(ident) if _empty(p)]
    return [p.as_posix() for p in missing]


def _load_status(ident: str, epic: bool) -> Dict:
    return ai_run.load_epic_status(ident) if epic else ai_run.load_status(ident)


def _tables(epic: bool):
    if epic:
        return ai_run._EPIC_PREPARE_TO_COMPLETE, ai_run._EPIC_PREPARE_STEP_PROMPT
    return ai_run._PREPARE_TO_COMPLETE, ai_run._PREPARE_STEP_PROMPT


def _stage(step: str) -> str:
    return step.replace("-", "_")


def _step(stage: str) -> str:
    return stage.replace("_", "-")


def _decision(entry: Dict) -> Optional[str]:
    m = DECISION_RE.search(entry.get("note", "") or "")
    return m.group(1) if m else None


def fix_round(step: str, history: List[Dict], epic: bool) -> Optional[int]:
    """Fix rounds already completed for the gate this fix step belongs to (0-based)."""
    if not (step.endswith("-fix-prepare") or step.endswith("-fix-complete")):
        return None
    done = [h for h in history if h.get("status") == "done"]

    if epic:
        return _simple_gate(done, "epic_design_fix_complete", "epic_review_complete", "approve")
    if step.startswith("architect-fix"):
        return _simple_gate(done, "architect_fix_complete", "architect_review_complete", "approve")

    # Shared dev_fix_complete marker: attribute each to the most recent preceding
    # non-approve/non-pass gate decision among review_complete / qa_complete.
    counts = {"review": 0, "qa": 0}
    current: Optional[str] = None
    for h in done:
        stage = h.get("stage")
        if stage in ("review_complete", "qa_complete"):
            gate = "review" if stage == "review_complete" else "qa"
            ok = "approve" if gate == "review" else "pass"
            if _decision(h) == ok:
                counts[gate] = 0
            else:
                current = gate
        elif stage == "dev_fix_complete" and current:
            counts[current] += 1
    return counts[current] if current else 0


def _simple_gate(done: List[Dict], marker: str, gate: str, ok: str) -> int:
    count = 0
    for h in done:
        if h.get("stage") == gate and _decision(h) == ok:
            count = 0
        elif h.get("stage") == marker:
            count += 1
    return count


def _last_prepare_done(history: List[Dict], prepare_stage: str) -> bool:
    for h in reversed(history):
        if h.get("stage") == prepare_stage:
            return h.get("status") == "done"
    return False


def route(ident: str, epic: bool) -> Dict:
    status = _load_status(ident, epic)
    history = status.get("history") or []
    state = status.get("state")
    current = status.get("current_stage")
    last = history[-1] if history else None
    prepare_to_complete, prompt_paths = _tables(epic)
    complete_to_prepare = {v: k for k, v in prepare_to_complete.items()}

    # A failed prepare/complete mutates current_stage; next_action would route
    # past it, so report the failed step itself.
    kind = None
    step = None
    if state == "failed" and current:
        cand = _step(current)
        if cand in complete_to_prepare:
            kind, step = "complete", cand
        elif cand in prepare_to_complete:
            kind, step = "prepare", cand
    forced_prepare = kind == "prepare"
    if kind is None:
        step = ai_run.epic_next_action(ident) if epic else ai_run.next_action(ident)
        if step == "done":
            kind = "done"
        elif step in prepare_to_complete:
            kind = "prepare"
        elif step in complete_to_prepare:
            kind = "complete"
        else:
            raise ValueError(f"Unroutable step from runner: {step!r}")

    out: Dict = {
        ("epic" if epic else "ticket"): ident,
        "step": step,
        "kind": kind,
        "prompt_path": None,
        "model": None,
        "effort": None,
        "next_complete": None,
        "fix_round": None,
        "missing_outputs": None,
        "state": state,
        "current_stage": current,
        "last_history": (
            {"stage": last.get("stage"), "status": last.get("status")} if last else None
        ),
    }
    if kind == "done":
        return out

    prepare_step = step if kind == "prepare" else complete_to_prepare[step]
    model, effort = ai_run.STEP_MODEL.get(prepare_step, ai_run._DEFAULT_STEP_MODEL)
    out["model"], out["effort"] = model, effort
    out["fix_round"] = fix_round(step, history, epic)
    prompt = prompt_paths[prepare_step](ident)  # type: ignore[operator]

    if kind == "prepare":
        out["next_complete"] = prepare_to_complete[step]
        out["prompt_path"] = None if forced_prepare else prompt.as_posix()
    else:
        out["missing_outputs"] = missing_outputs(step, ident, epic)
        if prompt.exists() and _last_prepare_done(history, _stage(prepare_step)):
            out["prompt_path"] = prompt.as_posix()
    return out


def validate_id(ident: str) -> bool:
    return bool(ID_RE.match(ident)) and ".." not in ident


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only routing helper for the Claude wrapper.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_ in (("next", "Ticket routing as JSON."), ("epic-next", "Epic routing as JSON.")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("id")
        p.add_argument("--json", action="store_true", help="Emit JSON (always on; accepted for clarity).")
    p = sub.add_parser("validate-id", help="Exit 0 iff the id is a safe ticket/epic id.")
    p.add_argument("id")
    args = parser.parse_args(argv)

    if args.command == "validate-id":
        if validate_id(args.id):
            return 0
        print(
            f"[ERROR] Invalid id {args.id!r}: must match [A-Za-z0-9][A-Za-z0-9._-]{{0,79}} and not contain '..'.",
            file=sys.stderr,
        )
        return 2

    try:
        result = route(args.id, epic=args.command == "epic-next")
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - surface any routing failure on stderr only
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
