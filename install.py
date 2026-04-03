#!/usr/bin/env python3
"""
AI Workflow Installer

Copies the AI workflow engine files into a target project directory.

Usage:
    python install.py --target /path/to/my-project [options]

Options:
    --target <path>             Target project directory (required)
    --force-project-files       Overwrite project_config.json and CLAUDE.md if they exist
    --with-skills <profile>     Copy examples/<profile>/skills/ into target .ai/skills/
    --dry-run                   Simulate actions without making any changes
    --yes                       Skip interactive confirmation prompt
    --backup                    Backup existing managed files before overwriting
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Files/dirs excluded from all copy operations
EXCLUDE_PATTERNS = {".DS_Store", "._.DS_Store", "Thumbs.db", "__pycache__", ".git"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo"}

# Managed assets: always overwritten on install/upgrade
MANAGED_DIRS = [
    Path(".ai/bin"),
    Path(".ai/agents"),
    Path(".ai/templates"),
]

# Sentinel file to verify we are running from inside the source repo
SOURCE_SENTINEL = Path(".ai/bin/ai_run.py")


def should_exclude(path: Path) -> bool:
    """Return True if this path matches an exclusion pattern."""
    for part in path.parts:
        if part in EXCLUDE_PATTERNS:
            return True
    if path.suffix in EXCLUDE_EXTENSIONS:
        return True
    return False


def collect_files(src_dir: Path) -> list[Path]:
    """Return all non-excluded files under src_dir, relative to src_dir."""
    result = []
    for f in sorted(src_dir.rglob("*")):
        if f.is_file() and not should_exclude(f.relative_to(src_dir)):
            result.append(f.relative_to(src_dir))
    return result


def copy_file(src: Path, dst: Path, dry_run: bool) -> str:
    """
    Copy src to dst. Returns action token: 'COPIED' or 'OVERWRITTEN'.
    Raises OSError on failure.
    """
    existed = dst.exists()
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return "OVERWRITTEN" if existed else "COPIED"


def backup_managed_files(
    target: Path,
    source_root: Path,
    timestamp: str,
    dry_run: bool,
    include_project_files: bool = False,
) -> list[str]:
    """
    Copy all existing managed files from target to a backup directory.
    When include_project_files is True, also backs up project_config.json and CLAUDE.md.
    Returns list of backed-up relative paths.
    """
    backup_dir = target / f".ai_backup_{timestamp}"
    backed_up = []
    for managed_rel in MANAGED_DIRS:
        target_dir = target / managed_rel
        if not target_dir.exists():
            continue
        for f in sorted(target_dir.rglob("*")):
            if f.is_file() and not should_exclude(f.relative_to(target_dir)):
                rel = f.relative_to(target)
                dst = backup_dir / rel
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
                backed_up.append(str(rel))
    if include_project_files:
        for project_file_rel in [Path(".ai/project_config.json"), Path(".ai/CLAUDE.md")]:
            src = target / project_file_rel
            if src.exists():
                dst = backup_dir / project_file_rel
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                backed_up.append(str(project_file_rel))
    return backed_up


def find_available_profiles(source_root: Path) -> list[str]:
    """Return list of profile names available under examples/."""
    examples_dir = source_root / "examples"
    if not examples_dir.is_dir():
        return []
    return sorted(
        d.name for d in examples_dir.iterdir()
        if d.is_dir() and not should_exclude(Path(d.name))
    )


def print_action(token: str, rel_path: str, note: str = "", dry_run: bool = False) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""
    token_str = f"[{token}]"
    print(f"{prefix}{token_str:<15} {rel_path:<50} {note}")


def confirm_proceed(planned_actions: list[str]) -> bool:
    """Print planned actions and ask user to confirm. Returns True if confirmed."""
    print("\nPlanned actions:")
    for line in planned_actions:
        print(f"  {line}")
    print()
    answer = input("Proceed? [y/N] ").strip().lower()
    return answer == "y"


def run_install(args: argparse.Namespace) -> int:
    source_root = Path(__file__).resolve().parent
    target = Path(args.target).resolve()
    dry_run = args.dry_run

    # AC-14: Verify we're running from inside the source repo
    if not (source_root / SOURCE_SENTINEL).exists():
        print(
            f"ERROR: Source files not found. Run this script from the ai-agent-team repo root.",
            file=sys.stderr,
        )
        return 1

    # AC-10: Validate target path
    if target.exists() and not target.is_dir():
        print(f"ERROR: --target '{target}' exists but is not a directory.", file=sys.stderr)
        return 1
    if target.exists() and not os.access(target, os.W_OK):
        print(f"ERROR: --target '{target}' is not writable.", file=sys.stderr)
        return 1
    if not target.exists():
        parent = target.parent
        if not parent.exists():
            print(
                f"ERROR: --target '{target}' cannot be created: parent directory '{parent}' does not exist.",
                file=sys.stderr,
            )
            return 1
        if not os.access(parent, os.W_OK):
            print(
                f"ERROR: --target '{target}' cannot be created: parent directory '{parent}' is not writable.",
                file=sys.stderr,
            )
            return 1

    # AC-11: Validate --with-skills profile
    if args.with_skills:
        profile_dir = source_root / "examples" / args.with_skills / "skills"
        if not profile_dir.is_dir():
            available = find_available_profiles(source_root)
            print(
                f"ERROR: Skills profile '{args.with_skills}' not found.",
                file=sys.stderr,
            )
            if available:
                print(f"Available profiles: {', '.join(available)}", file=sys.stderr)
            else:
                print("No profiles found under examples/.", file=sys.stderr)
            return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    project_name = target.name

    # --- Build list of planned actions for confirmation ---
    planned_summary = []

    # Managed dirs
    for managed_rel in MANAGED_DIRS:
        src_dir = source_root / managed_rel
        if src_dir.is_dir():
            for rel_file in collect_files(src_dir):
                dst = target / managed_rel / rel_file
                existed = dst.exists()
                token = "OVERWRITTEN" if existed else "COPIED"
                planned_summary.append(f"[{token}] {managed_rel / rel_file}")

    # project_config.json
    config_dst = target / ".ai" / "project_config.json"
    config_template = source_root / ".ai" / "templates" / "project_config.template.json"
    if config_dst.exists() and not args.force_project_files:
        planned_summary.append(f"[SKIP] .ai/project_config.json (already exists)")
    else:
        planned_summary.append(f"[INIT] .ai/project_config.json (from template)")

    # CLAUDE.md
    claude_src = source_root / "CLAUDE.md"
    claude_dst = target / ".ai" / "CLAUDE.md"
    if claude_dst.exists() and not args.force_project_files:
        planned_summary.append(f"[SKIP] .ai/CLAUDE.md (already exists)")
    else:
        planned_summary.append(f"[INIT] .ai/CLAUDE.md")

    # Skills
    if args.with_skills:
        skills_src = source_root / "examples" / args.with_skills / "skills"
        for rel_file in collect_files(skills_src):
            dst = target / ".ai" / "skills" / rel_file
            if dst.exists():
                planned_summary.append(f"[SKIP] .ai/skills/{rel_file} (already exists)")
            else:
                planned_summary.append(f"[COPIED] .ai/skills/{rel_file}")

    # Check for existing managed files to warn about overwrites
    has_existing_managed = any(
        (target / d).exists() for d in MANAGED_DIRS
    )

    # --- Print header ---
    print("AI Workflow Installer")
    print("=====================")
    print(f"Target: {target}")
    if dry_run:
        print("[DRY-RUN MODE] No files will be written.\n")
    print()

    if has_existing_managed and not dry_run:
        print("[WARNING]       Existing managed files (.ai/bin, .ai/agents, .ai/templates) will be overwritten.")
        print()

    # --- Confirm (unless --yes or --dry-run) ---
    if not args.yes and not dry_run:
        if not confirm_proceed(planned_summary):
            print("Aborted.")
            return 0

    # --- Backup ---
    if args.backup:
        backup_dir_name = f".ai_backup_{timestamp}"
        try:
            backed_up = backup_managed_files(
                target, source_root, timestamp, dry_run,
                include_project_files=args.force_project_files,
            )
        except OSError as e:
            print(f"ERROR: Backup failed: {e}", file=sys.stderr)
            return 1
        if backed_up:
            print_action("BACKUP", backup_dir_name, f"({len(backed_up)} files backed up)", dry_run=dry_run)
        else:
            print_action("BACKUP", backup_dir_name, "(nothing to back up)", dry_run=dry_run)

    # --- Copy managed assets ---
    copied_before_error = []
    for managed_rel in MANAGED_DIRS:
        src_dir = source_root / managed_rel
        if not src_dir.is_dir():
            continue
        for rel_file in collect_files(src_dir):
            src = src_dir / rel_file
            dst = target / managed_rel / rel_file
            rel_display = str(managed_rel / rel_file)
            try:
                token = copy_file(src, dst, dry_run)
                note = "(new file)" if token == "COPIED" else "(replaced existing)"
                print_action(token, rel_display, note, dry_run=dry_run)
                copied_before_error.append(rel_display)
            except OSError as e:
                print(f"ERROR: Failed to copy '{rel_display}': {e}", file=sys.stderr)
                print(f"\nFiles successfully copied before failure:", file=sys.stderr)
                for f in copied_before_error:
                    print(f"  {f}", file=sys.stderr)
                print(
                    "[WARNING] Install incomplete — target .ai/ may be in a partial state. "
                    "Fix the error and re-run to complete.",
                    file=sys.stderr,
                )
                return 1

    # --- Initialize project-owned files ---
    # project_config.json
    if config_dst.exists() and not args.force_project_files:
        print_action("SKIP", ".ai/project_config.json", "(already exists, use --force-project-files to overwrite)", dry_run=dry_run)
    else:
        if config_template.exists():
            try:
                template_text = config_template.read_text(encoding="utf-8")
                config_content = template_text.replace("<PROJECT_NAME>", project_name)
                if not dry_run:
                    config_dst.parent.mkdir(parents=True, exist_ok=True)
                    config_dst.write_text(config_content, encoding="utf-8")
                print_action("INIT", ".ai/project_config.json", "(created from template)", dry_run=dry_run)
            except OSError as e:
                print(f"ERROR: Failed to write project_config.json: {e}", file=sys.stderr)
                return 1
        else:
            print_action("WARNING", ".ai/project_config.json", "template not found — skipped", dry_run=dry_run)

    # CLAUDE.md
    if claude_dst.exists() and not args.force_project_files:
        print_action("SKIP", ".ai/CLAUDE.md", "(already exists, use --force-project-files to overwrite)", dry_run=dry_run)
    else:
        if claude_src.exists():
            try:
                if not dry_run:
                    claude_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(claude_src, claude_dst)
                print_action("INIT", ".ai/CLAUDE.md", "(copied from repo CLAUDE.md)", dry_run=dry_run)
            except OSError as e:
                print(f"ERROR: Failed to copy CLAUDE.md: {e}", file=sys.stderr)
                return 1
        else:
            print_action("WARNING", ".ai/CLAUDE.md", "source CLAUDE.md not found — skipped", dry_run=dry_run)

    # --- Copy skills (--with-skills) ---
    if args.with_skills:
        skills_src = source_root / "examples" / args.with_skills / "skills"
        skills_dst_base = target / ".ai" / "skills"
        skills_copied_before_error = []
        for rel_file in collect_files(skills_src):
            src = skills_src / rel_file
            dst = skills_dst_base / rel_file
            rel_display = f".ai/skills/{rel_file}"
            if dst.exists():
                print_action("SKIP", rel_display, "(already exists)", dry_run=dry_run)
            else:
                try:
                    if not dry_run:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                    print_action("COPIED", rel_display, "(new file)", dry_run=dry_run)
                    skills_copied_before_error.append(rel_display)
                except OSError as e:
                    print(f"ERROR: Failed to copy skill '{rel_display}': {e}", file=sys.stderr)
                    if skills_copied_before_error:
                        print(f"\nSkill files copied before failure:", file=sys.stderr)
                        for f in skills_copied_before_error:
                            print(f"  {f}", file=sys.stderr)
                    print(
                        "[WARNING] Install incomplete — target .ai/ may be in a partial state. "
                        "Fix the error and re-run to complete.",
                        file=sys.stderr,
                    )
                    return 1
    else:
        print_action("WARNING", ".ai/skills/", "not copied — use --with-skills <profile> to add skills", dry_run=dry_run)

    # --- Done ---
    print()
    if dry_run:
        print("[DRY-RUN] No changes were made.")
    else:
        print('Done. Run: python .ai/bin/ai_run.py init <TICKET> "<requirement>"')

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install or upgrade the AI workflow engine into a target project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        required=True,
        metavar="<path>",
        help="Target project directory",
    )
    parser.add_argument(
        "--force-project-files",
        action="store_true",
        help="Overwrite project_config.json and CLAUDE.md even if they already exist",
    )
    parser.add_argument(
        "--with-skills",
        metavar="<profile>",
        help="Copy examples/<profile>/skills/ into target .ai/skills/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate all actions without making any filesystem changes",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing managed files to .ai_backup_<timestamp>/ before overwriting",
    )

    args = parser.parse_args()
    sys.exit(run_install(args))


if __name__ == "__main__":
    main()
