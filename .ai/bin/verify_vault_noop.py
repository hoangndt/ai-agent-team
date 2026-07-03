#!/usr/bin/env python3
"""Verify vault injection is a byte-for-byte no-op when the vault is absent/disabled.

Diffs live `build_role_prompt` / `build_epic_role_prompt` output against golden
fixtures captured before vault wiring landed. See design_note.md
"Verification approach" in .ai/runs/EPIC-001-US-002-vault-injection-read-path/architect/.

Usage:
    python .ai/bin/verify_vault_noop.py            # verify (default, exits non-zero on mismatch)
    python .ai/bin/verify_vault_noop.py --capture   # (re-)capture golden fixtures from current code
"""
import difflib
import json
import shutil
import sys
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parent
BASE = BIN_DIR.parent
GOLDEN_DIR = BIN_DIR / "testdata" / "vault_noop_golden"
CONFIG_PATH = BASE / "project_config.json"
VAULT_DIR = BASE / "vault"

sys.path.insert(0, str(BIN_DIR))
import ai_run  # noqa: E402

TASK_INSTRUCTION = "Test task instruction for no-op verification."

TICKET_CASES = [
    ("EPIC-001-US-001-vault-skeleton-templates", "architect"),
    ("EPIC-001-US-001-vault-skeleton-templates", "developer"),
    ("EPIC-001-US-001-vault-skeleton-templates", "reviewer"),
    ("EPIC-001-US-001-vault-skeleton-templates", "qa"),
]

EPIC_CASES = [
    ("epic-001-living-architecture-doc", "epic_analyst"),
    ("epic-001-living-architecture-doc", "epic_designer"),
    ("epic-001-living-architecture-doc", "epic_reviewer"),
    ("epic-001-living-architecture-doc", "epic_planner"),
]


def golden_path(role: str, ticket_or_epic: str) -> Path:
    return GOLDEN_DIR / f"{role}_{ticket_or_epic}.txt"


def render_all():
    outputs = {}
    for ticket, role in TICKET_CASES:
        outputs[golden_path(role, ticket)] = ai_run.build_role_prompt(
            ticket, role, TASK_INSTRUCTION
        )
    for epic, role in EPIC_CASES:
        outputs[golden_path(role, epic)] = ai_run.build_epic_role_prompt(
            epic, role, TASK_INSTRUCTION
        )
    return outputs


def capture():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    outputs = render_all()
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    print(f"[capture] wrote {len(outputs)} golden fixtures to {GOLDEN_DIR}")
    return 0


def diff_against_golden(label: str) -> bool:
    ok = True
    outputs = render_all()
    for path, content in outputs.items():
        golden = path.read_text(encoding="utf-8") if path.exists() else None
        if golden is None:
            print(f"[FAIL] {label}: missing golden fixture {path}")
            ok = False
            continue
        if content != golden:
            ok = False
            print(f"[FAIL] {label}: mismatch for {path.name}")
            diff = difflib.unified_diff(
                golden.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"golden/{path.name}",
                tofile=f"live/{path.name}",
            )
            sys.stdout.writelines(diff)
    if ok:
        print(f"[OK] {label}: {len(outputs)} outputs match golden byte-for-byte")
    return ok


def verify_no_vault_dir() -> bool:
    if not VAULT_DIR.exists():
        return diff_against_golden("no vault dir")
    backup_dir = VAULT_DIR.parent / (VAULT_DIR.name + ".noop_backup")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.move(str(VAULT_DIR), str(backup_dir))
    try:
        return diff_against_golden("no vault dir")
    finally:
        shutil.move(str(backup_dir), str(VAULT_DIR))


def verify_disabled() -> bool:
    if not VAULT_DIR.is_dir():
        print("[SKIP] enabled=false case: no vault dir present to test against")
        return True
    original = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        config = json.loads(original)
        config.setdefault("vault", {})["enabled"] = False
        CONFIG_PATH.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return diff_against_golden("enabled=false")
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")


def main() -> int:
    if "--capture" in sys.argv:
        return capture()

    if not GOLDEN_DIR.exists() or not any(GOLDEN_DIR.iterdir()):
        print(f"[ERROR] No golden fixtures found in {GOLDEN_DIR}. Run with --capture first.")
        return 1

    ok = verify_no_vault_dir()
    ok = verify_disabled() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
