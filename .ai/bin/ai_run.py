#!/usr/bin/env python3
"""Workflow runner entry point and compatibility facade.

The implementation lives in the `ai_runner` package next to this file, split by
responsibility (constants, paths, state, context, prompts, per-stage handlers,
routing, wezterm, autoflow, cli). This module re-exports every name the runner
exposed as a single file so `import ai_run` keeps working for `ai_wrap.py`,
tests and tools. It holds no logic of its own.

Names are bound here at import time: to patch behavior, patch the defining
`ai_runner` module, not this facade.
"""
import argparse  # noqa: F401
import hashlib  # noqa: F401
import json  # noqa: F401
import re  # noqa: F401
import subprocess  # noqa: F401
import sys  # noqa: F401
import time  # noqa: F401
from datetime import datetime  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Dict, List, Optional, Tuple  # noqa: F401

from ai_runner.constants import (  # noqa: F401
    AGENTS, ARCH_INIT_TICKET, ARCH_REFRESH_TICKET, BASE, ENGINE_REGISTRY, EPICS,
    FIGMA_URL_RE, KNOWN_PREPARE_STEPS, KNOWN_SUBCOMMANDS, make_sentinel, make_sentinel_instruction, RUNS,
)
from ai_runner.paths import (  # noqa: F401
    acceptance_criteria_path, adr_distill_dir, adr_distill_prompt_path, arch_init_dir,
    arch_init_prompt_path, arch_refresh_dir, arch_refresh_prompt_path, architect_dir,
    architect_fix_context_path, architect_fix_prompt_path, architect_prompt_path,
    architect_review_prompt_path, architect_review_report_path, assumptions_path,
    design_note_path, dev_dir, dev_fix_prompt_path, dev_prompt_path, distill_dir,
    distill_prompt_path, epic_analysis_dir, epic_analysis_path,
    epic_analysis_prompt_path, epic_breakdown_dir, epic_breakdown_prompt_path,
    epic_design_dir, epic_design_fix_prompt_path, epic_design_path,
    epic_design_prompt_path, epic_fix_dir, epic_input_dir, epic_input_file, epic_path,
    epic_review_dir, epic_review_fix_context_path, epic_review_prompt_path,
    epic_review_report_path, epic_status_file, epic_story_map_path,
    epic_story_status_path, epic_tickets_dir, fix_dir, implementation_report_path,
    input_dir, input_file, now, previous_architect_review_path,
    previous_epic_review_path, previous_qa_report_path, previous_review_report_path,
    project_config_path, qa_dir, qa_fix_context_path, qa_prompt_path, qa_report_path,
    review_dir, review_fix_context_path, review_prompt_path, review_report_path,
    run_path, status_file, task_spec_path, vault_cap_exceeded_path,
)
from ai_runner.state import (  # noqa: F401
    add_history, complete_epic_stage, complete_stage, ensure_arch_init_status,
    ensure_arch_refresh_status, ensure_base_dirs, ensure_epic_dirs,
    ensure_non_empty_epic_files, ensure_ticket_dirs, fail_epic_stage, fail_stage,
    get_base_branch, init_epic_status, init_status, init_ticket, load_epic_status,
    load_project_config, load_status, read, resolve_engine, save_epic_status,
    save_status, set_artifact, set_epic_artifact, set_epic_runner, set_runner,
    update_epic_stage, update_stage, write,
)
from ai_runner.context import (  # noqa: F401
    build_epic_project_context, build_figma_context, build_project_context,
    build_vault_context, _cap_lines, dedupe_paths, ensure_non_empty_files,
    ensure_section_present, extract_figma_urls, file_ref_list, get_domain_config,
    get_effective_role_skills, get_epic_domain, get_epic_domains, get_epic_role_skills,
    get_figma_skill_paths, get_role_skills, get_ticket_domain, get_ticket_figma_urls,
    load_skill_contents, next_adr_id, read_vault_modules, read_vault_overview,
    require_agent_file, vault_root,
)
from ai_runner.prompts import (  # noqa: F401
    build_architect_fix_context, build_epic_review_fix_context, build_epic_role_prompt,
    build_fix_context, build_qa_fix_context, build_role_prompt,
)
from ai_runner.architect_stages import (  # noqa: F401
    architect_complete, architect_fix_complete, architect_fix_prepare,
    architect_prepare, architect_review_complete, architect_review_prepare,
)
from ai_runner.dev_qa_stages import (  # noqa: F401
    archive_file, archive_quality_reports_for_fix, dev_complete, dev_fix_complete,
    dev_fix_prepare, dev_prepare, _epic_story_status_block, qa_complete, qa_prepare,
    review_complete, review_prepare,
)
from ai_runner.distill_stages import (  # noqa: F401
    distill_complete, distill_prepare, _distill_retry_state,
    _extract_architecture_impact, _largest_sections, _set_distill_retry_state,
    _stage_completed_in_history, _write_vault_cap_exceeded,
)
from ai_runner.arch_stages import (  # noqa: F401
    arch_init_complete, arch_init_prepare, arch_refresh_complete, arch_refresh_prepare,
    _get_overview_baseline, _set_overview_baseline, _sha256_of,
)
from ai_runner.epic_stages import (  # noqa: F401
    adr_distill_complete, adr_distill_prepare, _adr_frontmatter_errors,
    _ADR_VALID_STATUSES, epic_analysis_complete, epic_analysis_prepare,
    epic_breakdown_complete, epic_breakdown_prepare, epic_design_complete,
    epic_design_fix_complete, epic_design_fix_prepare, epic_design_prepare,
    epic_generate_tickets, epic_init, epic_review_complete, epic_review_prepare,
    _epic_stage_completed_in_history, _parse_adr_frontmatter,
)
from ai_runner.routing import (  # noqa: F401
    current_outcome, epic_current_review_decision, epic_next_action, epic_next_step,
    _EPIC_PREPARE_STEP_PROMPT, _EPIC_PREPARE_TO_COMPLETE, next_action, next_step,
    _PREPARE_STEP_PROMPT, _PREPARE_TO_COMPLETE, run_named_epic_step, run_named_step,
    show_epic_status, show_status,
)
from ai_runner.steps import (  # noqa: F401
    FALLBACK_STEP_MODEL, StepConfigError, get_step_model, load_step_models,
    preflight_step_models, step_models_path,
)
from ai_runner.wezterm import (  # noqa: F401
    close_wezterm_pane, get_autoflow_config, spawn_ai_wezterm, wait_for_sentinel,
)
from ai_runner.autoflow import (  # noqa: F401
    run_epic_autoflow, run_ticket_autoflow,
)
from ai_runner.cli import (  # noqa: F401
    build_parser, main, maybe_init_and_run,
)


if __name__ == "__main__":
    raise SystemExit(main())
