"""Path helpers for ticket and epic run directories."""

from datetime import datetime
from pathlib import Path

from .constants import BASE, EPICS, RUNS


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


def distill_dir(ticket: str) -> Path:
    return run_path(ticket) / "distill"


def distill_prompt_path(ticket: str) -> Path:
    return distill_dir(ticket) / "distill_prompt.md"


def vault_cap_exceeded_path(ticket: str) -> Path:
    return fix_dir(ticket) / "vault_cap_exceeded.md"


def arch_init_dir(ticket: str) -> Path:
    return run_path(ticket) / "arch_init"


def arch_init_prompt_path(ticket: str) -> Path:
    return arch_init_dir(ticket) / "arch_init_prompt.md"


def arch_refresh_dir(ticket: str) -> Path:
    return run_path(ticket) / "arch_refresh"


def arch_refresh_prompt_path(ticket: str) -> Path:
    return arch_refresh_dir(ticket) / "arch_refresh_prompt.md"


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


def epic_story_status_path(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "epic_story_status.md"


def adr_distill_dir(epic: str) -> Path:
    return epic_path(epic) / "adr_distill"


def adr_distill_prompt_path(epic: str) -> Path:
    return adr_distill_dir(epic) / "adr_distill_prompt.md"


def epic_analysis_review_prompt_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_analysis_review_prompt.md"


def epic_analysis_review_report_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_analysis_review.json"


def epic_analysis_fix_prompt_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_analysis_fix_prompt.md"


def epic_analysis_review_fix_context_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_analysis_review_fix_context.md"


def previous_epic_analysis_review_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "previous_epic_analysis_review.json"


def epic_breakdown_review_prompt_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_breakdown_review_prompt.md"


def epic_breakdown_review_report_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_breakdown_review.json"


def epic_breakdown_fix_prompt_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_breakdown_fix_prompt.md"


def epic_breakdown_review_fix_context_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_breakdown_review_fix_context.md"


def previous_epic_breakdown_review_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "previous_epic_breakdown_review.json"
