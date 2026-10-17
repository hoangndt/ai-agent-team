"""Next-step routing for tickets and epics and named step dispatch."""

import json
from pathlib import Path
from typing import Dict, Optional

from .paths import (
    adr_distill_prompt_path, architect_fix_prompt_path, architect_prompt_path,
    architect_review_prompt_path, architect_review_report_path, design_note_path,
    dev_fix_prompt_path, dev_prompt_path, distill_prompt_path, epic_analysis_path,
    epic_analysis_prompt_path, epic_breakdown_prompt_path, epic_design_fix_prompt_path,
    epic_design_path, epic_design_prompt_path, epic_review_prompt_path,
    epic_review_report_path, epic_story_map_path, epic_tickets_dir,
    implementation_report_path, qa_prompt_path, qa_report_path, review_prompt_path,
    review_report_path, task_spec_path, vault_cap_exceeded_path,
)
from .state import load_epic_status, load_status, read
from .context import vault_root
from .architect_stages import (
    architect_complete, architect_fix_complete, architect_fix_prepare,
    architect_prepare, architect_review_complete, architect_review_prepare,
)
from .dev_qa_stages import (
    dev_complete, dev_fix_complete, dev_fix_prepare, dev_prepare, qa_complete,
    qa_prepare, review_complete, review_prepare,
)
from .distill_stages import (
    _stage_completed_in_history, distill_complete, distill_prepare,
)
from .epic_stages import (
    _epic_stage_completed_in_history, adr_distill_complete, adr_distill_prepare,
    epic_analysis_complete, epic_analysis_prepare, epic_breakdown_complete,
    epic_breakdown_prepare, epic_design_complete, epic_design_fix_complete,
    epic_design_fix_prepare, epic_design_prepare, epic_review_complete,
    epic_review_prepare,
)
from .steps import preflight_step_models
from .wezterm import spawn_ai_wezterm


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
        # ADR distill (this branch is what auto-triggers it once the review is
        # approved — see the write-path comment above) runs before breakdown.
        # Guarded on vault_root() so vault-less epics skip straight to breakdown
        # (FC-1/backward-compat).
        if vault_root() is not None:
            if not adr_distill_prompt_path(epic).exists():
                return "adr-distill-prepare"
            if current_stage == "adr_distill_prepare":
                return "adr-distill-complete"
            if not _epic_stage_completed_in_history(epic, "adr_distill_complete"):
                return "adr-distill-complete"

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
        "adr-distill-prepare": adr_distill_prepare,
        "adr-distill-complete": adr_distill_complete,
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
    "adr-distill-prepare": adr_distill_prompt_path,
}


def epic_next_step(epic: str, execute: bool = False, run_auto: bool = False, engine: str = "claude") -> None:
    step = epic_next_action(epic)
    if run_auto or execute:
        if run_auto:
            preflight_step_models(engine)
        run_named_epic_step(epic, step)
        if run_auto and step in _EPIC_PREPARE_STEP_PROMPT:
            prompt_path = _EPIC_PREPARE_STEP_PROMPT[step](epic)  # type: ignore[operator]
            spawn_ai_wezterm(prompt_path, str(Path.cwd()), engine=engine, step=step)
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
            # Rule 0 (explicit, evaluated first): a vault-disabled project must reach
            # "done" deterministically, not via an incidental fallback through rules
            # 1-4 below — distill_prepare's no-op path leaves current_stage untouched,
            # so nothing else here could reliably distinguish "disabled" from "not yet
            # started" without this check running first.
            if vault_root() is None:
                return "done"

            # Rule 1: prompt just built, waiting on distill-complete.
            if current_stage == "distill_prepare":
                return "distill-complete"

            # Rule 2: parked on the overview terminal block until a human trims it.
            if vault_cap_exceeded_path(ticket).exists() and not _stage_completed_in_history(
                ticket, "distill_complete"
            ):
                return "distill-complete"

            # Rule 3: distill already completed (pass or warn-and-proceed).
            if _stage_completed_in_history(ticket, "distill_complete"):
                return "done"

            # Rule 4: fallback — distill prompt not yet built.
            return "distill-prepare"

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
        "distill-prepare": distill_prepare,
        "distill-complete": distill_complete,
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
    "distill-prepare": distill_prompt_path,
}


_PREPARE_TO_COMPLETE: Dict[str, str] = {
    "architect-prepare":        "architect-complete",
    "architect-review-prepare": "architect-review-complete",
    "architect-fix-prepare":    "architect-fix-complete",
    "dev-prepare":              "dev-complete",
    "dev-fix-prepare":          "dev-fix-complete",
    "review-prepare":           "review-complete",
    "qa-prepare":               "qa-complete",
    "distill-prepare":          "distill-complete",
}


_EPIC_PREPARE_TO_COMPLETE: Dict[str, str] = {
    "epic-analysis-prepare":   "epic-analysis-complete",
    "epic-design-prepare":     "epic-design-complete",
    "epic-design-fix-prepare": "epic-design-fix-complete",
    "epic-review-prepare":     "epic-review-complete",
    "epic-breakdown-prepare":  "epic-breakdown-complete",
    "adr-distill-prepare":     "adr-distill-complete",
}


def next_step(ticket: str, execute: bool = False, run_auto: bool = False, engine: str = "claude") -> None:
    step = next_action(ticket)
    if run_auto or execute:
        if run_auto:
            preflight_step_models(engine)
        run_named_step(ticket, step)
        if run_auto and step in _PREPARE_STEP_PROMPT:
            prompt_path = _PREPARE_STEP_PROMPT[step](ticket)  # type: ignore[operator]
            spawn_ai_wezterm(prompt_path, str(Path.cwd()), engine=engine, step=step)
    else:
        print(step)


def show_status(ticket: str) -> None:
    print(json.dumps(load_status(ticket), indent=2, ensure_ascii=False))
