"""Unattended ticket and epic autoflow loops."""

import sys
from pathlib import Path

from .constants import make_sentinel, make_sentinel_instruction
from .paths import now
from .routing import (
    _EPIC_PREPARE_STEP_PROMPT, _EPIC_PREPARE_TO_COMPLETE, _PREPARE_STEP_PROMPT,
    _PREPARE_TO_COMPLETE, epic_next_action, next_action, run_named_epic_step,
    run_named_step,
)
from .steps import preflight_step_models
from .wezterm import (
    close_wezterm_pane, get_autoflow_config, spawn_ai_wezterm, wait_for_sentinel,
)


def run_ticket_autoflow(ticket: str, engine: str = "claude") -> None:
    preflight_step_models(engine)
    cfg = get_autoflow_config()
    poll_interval = cfg["poll_interval"]
    timeout = cfg["timeout"]

    print(
        f"[AUTOFLOW] Starting ticket autoflow for {ticket} "
        f"(poll={poll_interval}s, timeout={timeout}s)"
    )

    while True:
        step = next_action(ticket)
        print(f"[AUTOFLOW] [{now()}] Next step: {step}")

        if step == "done":
            print("[DONE] Workflow complete.")
            return

        if step in _PREPARE_STEP_PROMPT:
            try:
                run_named_step(ticket, step)
            except Exception as exc:
                print(f"[ERROR] Prepare step '{step}' failed: {exc}", file=sys.stderr)
                sys.exit(1)
            prompt_path = _PREPARE_STEP_PROMPT[step](ticket)  # type: ignore[operator]
            pane_id = spawn_ai_wezterm(
                prompt_path, str(Path.cwd()), sentinel_instruction=make_sentinel_instruction(ticket), engine=engine, step=step
            )

            if pane_id is None:
                print("[ERROR] WezTerm spawn failed. Stopping autoflow.", file=sys.stderr)
                sys.exit(1)

            success = wait_for_sentinel(pane_id, make_sentinel(ticket), poll_interval, timeout)

            if not success:
                print(
                    f"[ERROR] Timeout waiting for Claude ({step}). Stopping.",
                    file=sys.stderr,
                )
                close_wezterm_pane(pane_id)
                sys.exit(1)

            complete_step = _PREPARE_TO_COMPLETE[step]
            try:
                run_named_step(ticket, complete_step)
            except Exception as exc:
                print(f"[ERROR] Complete step '{complete_step}' failed: {exc}", file=sys.stderr)
                close_wezterm_pane(pane_id)
                sys.exit(1)

            close_wezterm_pane(pane_id)
        else:
            try:
                run_named_step(ticket, step)
            except Exception as exc:
                print(f"[ERROR] Step '{step}' failed: {exc}", file=sys.stderr)
                sys.exit(1)


def run_epic_autoflow(epic: str, engine: str = "claude") -> None:
    preflight_step_models(engine)
    cfg = get_autoflow_config()
    poll_interval = cfg["poll_interval"]
    timeout = cfg["timeout"]

    print(
        f"[AUTOFLOW] Starting epic autoflow for {epic} "
        f"(poll={poll_interval}s, timeout={timeout}s)"
    )

    while True:
        step = epic_next_action(epic)
        print(f"[AUTOFLOW] [{now()}] Next step: {step}")

        if step == "done":
            print("[DONE] Epic workflow complete.")
            return

        if step in _EPIC_PREPARE_STEP_PROMPT:
            try:
                run_named_epic_step(epic, step)
            except Exception as exc:
                print(f"[ERROR] Prepare step '{step}' failed: {exc}", file=sys.stderr)
                sys.exit(1)
            prompt_path = _EPIC_PREPARE_STEP_PROMPT[step](epic)  # type: ignore[operator]
            pane_id = spawn_ai_wezterm(
                prompt_path, str(Path.cwd()), sentinel_instruction=make_sentinel_instruction(epic), engine=engine, step=step
            )

            if pane_id is None:
                print("[ERROR] WezTerm spawn failed. Stopping autoflow.", file=sys.stderr)
                sys.exit(1)

            success = wait_for_sentinel(pane_id, make_sentinel(epic), poll_interval, timeout)

            if not success:
                print(
                    f"[ERROR] Timeout waiting for Claude ({step}). Stopping.",
                    file=sys.stderr,
                )
                close_wezterm_pane(pane_id)
                sys.exit(1)

            complete_step = _EPIC_PREPARE_TO_COMPLETE[step]
            try:
                run_named_epic_step(epic, complete_step)
            except Exception as exc:
                print(f"[ERROR] Complete step '{complete_step}' failed: {exc}", file=sys.stderr)
                close_wezterm_pane(pane_id)
                sys.exit(1)

            close_wezterm_pane(pane_id)
        else:
            try:
                run_named_epic_step(epic, step)
            except Exception as exc:
                print(f"[ERROR] Step '{step}' failed: {exc}", file=sys.stderr)
                sys.exit(1)
