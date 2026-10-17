"""Project-level arch-init and arch-refresh prepare/complete handlers."""

import hashlib
import sys
from pathlib import Path
from typing import Optional

from .constants import ARCH_INIT_TICKET, ARCH_REFRESH_TICKET, BASE
from .paths import (
    arch_init_dir, arch_init_prompt_path, arch_refresh_dir, arch_refresh_prompt_path,
    now, status_file,
)
from .state import (
    complete_stage, ensure_arch_init_status, ensure_arch_refresh_status, fail_stage,
    load_project_config, load_status, read, save_status, set_artifact, set_runner,
    update_stage, write,
)
from .context import ensure_non_empty_files, vault_root
from .prompts import build_role_prompt


# ── ARCH-INIT WORKFLOW ─────────────────────────────────────────────────────────
# Project-level, ticket-less bootstrap: seeds project_config.json domains (if
# missing) and the architecture vault from the codebase + CLAUDE.md files.
# Uses ARCH_INIT_TICKET as a sentinel id so the ordinary per-ticket status/
# prompt machinery can be reused unmodified.

def arch_init_prepare() -> None:
    ticket = ARCH_INIT_TICKET
    ensure_arch_init_status()

    root = vault_root()
    if root is None:
        msg = (
            "Vault missing or disabled (vault.enabled=false or .ai/vault absent). "
            "Run the US-001 vault skeleton setup first, then re-run arch-init."
        )
        fail_stage(ticket, "arch_init_prepare", msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        sys.exit(1)

    update_stage(ticket, "arch_init_prepare")
    set_runner(ticket, "arch-init-prepare")

    overview_path = root / "architecture" / "system-overview.md"
    modules_dir = root / "architecture" / "modules"
    root_claude_path = Path("CLAUDE.md")
    dot_ai_claude_path = BASE / "CLAUDE.md"
    import_line = "@.ai/vault/architecture/system-overview.md"

    task_instruction = f"""Work inside the current repository. This is a project-level bootstrap
with no ticket id — do not create or touch any `.ai/runs/<TICKET>/` directory other than
`{arch_init_dir(ticket).as_posix()}`.

Run the following two phases in order.

## Phase 1 — config bootstrap (conditional)

Read `.ai/project_config.json`.

- If it already has a non-empty `"domains"` block: this phase is a no-op. Do NOT modify
  `.ai/project_config.json`. Move on to Phase 2.
- If it has NO `"domains"` block (or an empty one): sweep the repository, infer one or more
  domains, and write a `"domains"` block to `.ai/project_config.json` where each domain has:
  - `paths`: a list of directories/paths that belong to that domain
  - `skills`: a map of role name (`architect`, `developer`, `reviewer`, `qa`) to a list of
    existing skill file paths for that domain — wire in skill files that already exist in the
    repo; if none exist for a role, leave that role's list empty. Do NOT author new skill file
    content.
  - Preserve every other existing key in `.ai/project_config.json` untouched.

## Phase 2 — vault bootstrap (always)

1. Resolve the domain list from `.ai/project_config.json["domains"]` (all entries — read the
   file fresh, in case Phase 1 just wrote it).
2. Sweep the codebase to understand components, entry points, data flows, and invariants.
3. Read `{root_claude_path.as_posix()}` and `{dot_ai_claude_path.as_posix()}` (either or both may
   not exist — treat a missing file as having no architecture prose). Extract any `## Architecture`
   section content from each. If the same architecture prose appears in both files, include it only
   once in the seeded vault content (dedupe the union).
4. Re-run / template-detection rule (apply to every vault file below before overwriting it):
   a vault file is "still a template" if and only if it contains at least one HTML comment
   (`<!-- ... -->`). If it contains one, it is safe to overwrite. If it contains none, treat it as
   already-real content: do NOT overwrite it, and instead add a line to your implementation output
   like `skipped <file>, already contains real content`.
5. Write `{overview_path.as_posix()}`:
   - Project-wide content derived from the repo sweep, plus any migrated architecture prose.
   - Keep the exact fixed headings and their order: `## Components`, `## Data Flows`,
     `## Invariants / Constraints`, `## ADR Index` (this is a contract read by later tooling —
     do not rename or reorder them).
   - Remove all HTML-comment placeholders; every heading must have real content.
6. Write `{modules_dir.as_posix()}/<domain>.md` for each resolved domain (one file per domain),
   following the structure of `{modules_dir.as_posix()}/_domain.template.md` (Responsibility, Key
   Components, How It Works, Entry Points, Dependencies, Gotchas / Invariants) with real,
   domain-specific content and no HTML-comment placeholders remaining.
7. Update `{root_claude_path.as_posix()}`:
   - If it has an `## Architecture` heading, replace that section's prose with a single line:
     `{import_line}`
   - If it has no `## Architecture` heading, insert a new `## Architecture` section containing
     only that import line, placed immediately after the top-level H1 title/intro and before the
     next existing section.
   - If `{root_claude_path.as_posix()}` does not exist at all, create a minimal one containing just
     an `## Architecture` section with the import line.
   - If the import line is already present, leave it as-is (idempotent).
8. Update `{dot_ai_claude_path.as_posix()}` if it exists: strip out any `## Architecture` section(s)
   whose content was migrated into the vault in step 3, preserving every other section verbatim.
   If the file does not exist, this step is a no-op — do not create it.

## Rules

- Do not invent domains, paths, or skills that don't reflect the actual repository.
- Preserve all non-architecture, hand-written content in both CLAUDE.md files verbatim.
- Do not author new skill file content (Phase 1) or new ADRs (out of scope).
- Do not run `git add`/`git commit`/`git push`. Leave every edit as a working-tree change for
  human review via `git diff`.
- Target the caps of roughly 200 lines for system-overview.md and 400 lines per module doc, but
  do not fail the task if you go over — that is enforced elsewhere.

## Important

- Do not reply in chat with the file contents.
- Write every file directly to the paths above.
- In your final output, summarize what Phase 1 did (or that it was a no-op) and list every vault
  file written vs. skipped (per the template-detection rule in step 4).
"""
    prompt = build_role_prompt(ticket, "arch_init", task_instruction)
    write(arch_init_prompt_path(ticket), prompt)
    set_artifact(ticket, "arch_init_prompt", arch_init_prompt_path(ticket))
    complete_stage(ticket, "arch_init_prepare", "Generated arch-init prompt.")
    print(f"[OK] Wrote {arch_init_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it perform the sweep and write "
        "the config/vault/CLAUDE.md files directly, then run arch-init-complete."
    )


def arch_init_complete() -> None:
    ticket = ARCH_INIT_TICKET
    if not status_file(ticket).exists():
        msg = (
            "No arch-init run found (missing .ai/runs/_arch-init/status.json). "
            "Run arch-init-prepare first."
        )
        print(f"[ERROR] {msg}", file=sys.stderr)
        raise FileNotFoundError(msg)
    update_stage(ticket, "arch_init_complete")
    set_runner(ticket, "arch-init-complete")

    root = vault_root()
    if root is None:
        msg = "Vault missing or disabled — cannot verify arch-init outputs."
        fail_stage(ticket, "arch_init_complete", msg)
        raise FileNotFoundError(msg)

    overview_path = root / "architecture" / "system-overview.md"
    ensure_non_empty_files([overview_path], "arch_init_complete", ticket)

    config = load_project_config()
    domains = config.get("domains", {})
    if not domains:
        msg = "project_config.json has no domains after arch-init act (Phase 1 must populate it)."
        fail_stage(ticket, "arch_init_complete", msg)
        raise ValueError(msg)

    modules_dir = root / "architecture" / "modules"
    module_candidates = [modules_dir / f"{domain}.md" for domain in domains]
    non_empty_modules = [p for p in module_candidates if p.exists() and read(p).strip()]
    if not non_empty_modules:
        msg = (
            "No non-empty module doc found among: "
            + ", ".join(p.as_posix() for p in module_candidates)
        )
        fail_stage(ticket, "arch_init_complete", msg)
        raise FileNotFoundError(msg)

    root_claude_path = Path("CLAUDE.md")
    import_line = "@.ai/vault/architecture/system-overview.md"
    if import_line not in read(root_claude_path):
        msg = f"{root_claude_path.as_posix()} is missing the import line: {import_line}"
        fail_stage(ticket, "arch_init_complete", msg)
        raise FileNotFoundError(msg)

    set_artifact(ticket, "vault_overview", overview_path)
    set_artifact(ticket, "vault_modules_dir", modules_dir)

    complete_stage(ticket, "arch_init_complete", f"arch-init outputs verified ({len(non_empty_modules)} module doc(s)).")
    print(f"[OK] arch-init outputs verified ({len(non_empty_modules)} module doc(s)).")
    print("[REVIEW] Run `git diff` to review every arch-init edit before committing — nothing was auto-committed.")


# ── ARCH-REFRESH WORKFLOW ───────────────────────────────────────────────────────
# Project-level, ticket-less drift check: an agent re-derives the
# system overview from the current codebase, diffs it against the committed
# system-overview.md, and writes a report — it never edits system-overview.md
# itself. A sha256 baseline captured at prepare and re-checked at complete
# turns "overview unchanged" into an enforced guarantee rather than a trust-based
# instruction.

def _sha256_of(path: Path) -> str:
    return hashlib.sha256(read(path).encode("utf-8")).hexdigest()


def _set_overview_baseline(ticket: str, sha: str) -> None:
    s = load_status(ticket)
    s.setdefault("artifacts", {})["overview_baseline_sha"] = sha
    s["updated_at"] = now()
    save_status(ticket, s)


def _get_overview_baseline(ticket: str) -> Optional[str]:
    s = load_status(ticket)
    return s.get("artifacts", {}).get("overview_baseline_sha")


def arch_refresh_prepare() -> None:
    ticket = ARCH_REFRESH_TICKET
    ensure_arch_refresh_status()

    root = vault_root()
    if root is None:
        msg = (
            "Vault missing or disabled (vault.enabled=false or .ai/vault absent). "
            "Run the US-001 vault skeleton setup first, then re-run arch-refresh."
        )
        fail_stage(ticket, "arch_refresh_prepare", msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        sys.exit(1)

    update_stage(ticket, "arch_refresh_prepare")
    set_runner(ticket, "arch-refresh-prepare")

    overview_path = root / "architecture" / "system-overview.md"
    drift_report_path = root / "architecture" / "_drift_report.md"

    _set_overview_baseline(ticket, _sha256_of(overview_path))

    task_instruction = f"""Work inside the current repository. This is a project-level drift
check with no ticket id — do not create or touch any `.ai/runs/<TICKET>/` directory other than
`{arch_refresh_dir(ticket).as_posix()}`.

## Step 1 — re-derive the overview (blind sweep)

Sweep the codebase (components, entry points, data flows, invariants/constraints) and mentally
re-derive what `{overview_path.as_posix()}` *should* say, **without reading the current file
first** — this avoids anchoring on its existing wording.

## Step 2 — read the current overview

Now read `{overview_path.as_posix()}`.

## Step 3 — diff and classify

Compare your re-derivation against the current file. Classify every divergence into exactly
these categories:

- **Missing components** — present in code but absent from the overview.
- **Stale entries** — present in the overview but no longer true / removed from code.
- **Wrong links** — module-doc or entry-point references that are broken or point elsewhere.

## Step 4 — write the drift report

Write `{drift_report_path.as_posix()}`, overwriting any prior report, with one section per
category above. If a category has no findings, state that explicitly (e.g. "none") — do not
omit the section.

## Rules

- Do **not** modify `{overview_path.as_posix()}` or any other vault file — this is a report-only
  check; humans apply changes manually.
- Do not run `git add`/`git commit`/`git push`.
- Do not reply in chat with the report contents — write it directly to the path above.
"""
    prompt = build_role_prompt(ticket, "arch_init", task_instruction)
    write(arch_refresh_prompt_path(ticket), prompt)
    set_artifact(ticket, "arch_refresh_prompt", arch_refresh_prompt_path(ticket))
    complete_stage(ticket, "arch_refresh_prepare", "Generated arch-refresh prompt.")
    print(f"[OK] Wrote {arch_refresh_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it sweep the code, diff against "
        "the current overview, and write the drift report, then run arch-refresh-complete."
    )


def arch_refresh_complete() -> None:
    ticket = ARCH_REFRESH_TICKET
    if not status_file(ticket).exists():
        msg = (
            "No arch-refresh run found (missing .ai/runs/_arch-refresh/status.json). "
            "Run arch-refresh-prepare first."
        )
        print(f"[ERROR] {msg}", file=sys.stderr)
        raise FileNotFoundError(msg)
    update_stage(ticket, "arch_refresh_complete")
    set_runner(ticket, "arch-refresh-complete")

    root = vault_root()
    if root is None:
        msg = "Vault missing or disabled — cannot verify arch-refresh outputs."
        fail_stage(ticket, "arch_refresh_complete", msg)
        raise FileNotFoundError(msg)

    overview_path = root / "architecture" / "system-overview.md"
    drift_report_path = root / "architecture" / "_drift_report.md"

    ensure_non_empty_files([drift_report_path], "arch_refresh_complete", ticket)

    baseline = _get_overview_baseline(ticket)
    current_sha = _sha256_of(overview_path)
    if baseline is None or current_sha != baseline:
        msg = (
            f"{overview_path.as_posix()} was modified during arch-refresh — it must stay "
            f"byte-for-byte unchanged. Restore it (e.g. `git checkout -- "
            f"{overview_path.as_posix()}`) and re-run arch-refresh."
        )
        fail_stage(ticket, "arch_refresh_complete", msg)
        raise ValueError(msg)

    set_artifact(ticket, "drift_report", drift_report_path)
    complete_stage(ticket, "arch_refresh_complete", "Drift report verified; overview unchanged.")
    print(f"[OK] arch-refresh drift report written to {drift_report_path.as_posix()}")
    print("[REVIEW] Review the report and apply changes to system-overview.md manually.")
