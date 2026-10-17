"""WezTerm pane spawning and sentinel polling."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from .constants import ENGINE_REGISTRY
from .state import load_project_config
from .steps import get_step_model


def spawn_ai_wezterm(
    prompt_path: Path,
    cwd: str,
    wait_seconds: float = 1.0,
    sentinel_instruction: Optional[str] = None,
    engine: str = "claude",
    step: Optional[str] = None,
) -> Optional[str]:
    engine_cfg = ENGINE_REGISTRY[engine]
    cmd = list(engine_cfg["base"])
    if engine_cfg.get("supports_model_effort") and step:
        model, effort = get_step_model(step)
        cmd += ["--model", model, "--effort", effort]
        print(f"[AUTO] Step '{step}' -> model={model}, effort={effort}")

    # Step 1: open a new WezTerm tab (bare shell, no engine command yet).
    result = subprocess.run(
        ["wezterm", "cli", "spawn", "--cwd", cwd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[WARN] wezterm spawn failed: {result.stderr.strip()}", file=sys.stderr)
        return None

    pane_id = result.stdout.strip()
    if not pane_id:
        print(
            "[WARN] Could not get WezTerm pane ID, skipping auto-paste.",
            file=sys.stderr,
        )
        return None

    print(f"[AUTO] Spawned WezTerm pane {pane_id}. Waiting 2s for shell to load...")
    time.sleep(2.0)

    # Step 2: launch the engine command, then hit Enter.
    cmd_text = " ".join(cmd)
    subprocess.run(
        ["wezterm", "cli", "send-text", "--pane-id", pane_id, "--no-paste"],
        input=cmd_text,
        text=True,
    )
    subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to key code 36'],
        capture_output=True,
    )
    print(f"[AUTO] Launched {engine} in pane {pane_id}. Waiting 1s before sending prompt...")
    time.sleep(1.0)

    # Step 3: send the prompt text.
    prompt_text = prompt_path.read_text(encoding="utf-8").rstrip("\n")
    if sentinel_instruction:
        prompt_text = prompt_text + "\n\n" + sentinel_instruction
    subprocess.run(
        ["wezterm", "cli", "send-text", "--pane-id", pane_id],
        input=prompt_text,
        text=True,
    )
    time.sleep(wait_seconds)
    subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to key code 36'],
        capture_output=True,
    )
    print(f"[AUTO] Prompt sent and Enter keystroke fired for pane {pane_id}. {engine} is processing.")
    return pane_id


def close_wezterm_pane(pane_id: str) -> None:
    result = subprocess.run(
        ["wezterm", "cli", "kill-pane", "--pane-id", pane_id],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"[WARN] Could not close WezTerm pane {pane_id}: {result.stderr.strip()}",
            file=sys.stderr,
        )
    else:
        print(f"[AUTO] Closed WezTerm pane {pane_id}.")


def get_autoflow_config() -> Dict:
    cfg = load_project_config()
    autoflow = cfg.get("autoflow", {})
    return {
        "poll_interval": float(autoflow.get("poll_interval_seconds", 1)),
        "timeout": float(autoflow.get("timeout_seconds", 1800)),
    }


def wait_for_sentinel(
    pane_id: str,
    sentinel: str,
    poll_interval: float,
    timeout: float,
) -> bool:
    # Two-phase state machine:
    #   State 0 (INIT):       Haven't seen sentinel yet.
    #   State 1 (FIRST_SEEN): Sentinel appeared once — likely the instruction text.
    #   State 2 (GONE):       Sentinel count dropped to 0 — instruction scrolled off.
    state = 0
    elapsed = 0.0
    while elapsed < timeout:
        result = subprocess.run(
            ["wezterm", "cli", "get-text", "--pane-id", pane_id],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[WAIT] get-text error (returncode={result.returncode}), skipping poll... ({elapsed:.0f}s elapsed, state={state})")
            time.sleep(poll_interval)
            elapsed += poll_interval
            continue

        count = result.stdout.count(sentinel)

        if state == 0 and count >= 1:
            state = 1
        elif state == 1:
            if count >= 2:
                print(f"[WAIT] Sentinel detected after {elapsed:.0f}s. Claude finished.")
                return True
            elif count == 0:
                state = 2
        elif state == 2 and count >= 1:
            print(f"[WAIT] Sentinel detected after {elapsed:.0f}s. Claude finished.")
            return True

        time.sleep(poll_interval)
        elapsed += poll_interval
    return False
