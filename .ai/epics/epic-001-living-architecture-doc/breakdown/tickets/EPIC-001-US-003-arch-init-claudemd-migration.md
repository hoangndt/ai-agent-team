## Summary

Add the two-phase `arch-init` command: conditional config bootstrap (infer domains/paths/skills when `project_config.json` has none), then vault bootstrap (codebase sweep + CLAUDE.md migration) that seeds `system-overview.md` + module docs and rewires CLAUDE.md to an `@` import.

## Goal

Provide a one-time operator command that seeds a usable vault from the codebase and existing CLAUDE.md architecture prose, producing git-diff-reviewable edits, validated on this repo as the reference case.

## Scope

- New `arch-init` subcommand registered in `KNOWN_SUBCOMMANDS` and `sub.add_parser`.
- Phase 1 (conditional — only if `domains` absent in `project_config.json`): agent sweeps repo, infers domain names, `domains.<name>.paths`, and `domains.<name>.skills.<role>` file lists (wiring existing files or empty lists only); writes `project_config.json`. No-op when domains exist.
- Phase 2 (vault bootstrap): sweep code + parse `## Architecture` sections from root `CLAUDE.md` and `.ai/CLAUDE.md`, dedupe the union, write `system-overview.md` (project-wide) + `modules/<domain>.md` (domain/stack detail); replace root `## Architecture` with `@.ai/vault/architecture/system-overview.md` import (create thin root CLAUDE.md if absent); strip migrated sections from `.ai/CLAUDE.md`.
- Generate the `arch-init` prompt file(s) and produce output as agent-written vault files (prepare/act/complete shape).

## Out of Scope

- `arch-refresh` drift check (US-007).
- Distill write path and ADR generation (US-005, US-006).
- Authoring new skill *file content* from scratch (only wire existing files / empty lists).
- Injection logic (US-002).

## Acceptance Criteria

- Running `arch-init` on this repo (already has `domains`) skips phase 1 and produces `system-overview.md` plus one `modules/workflow.md` with real content derived from the codebase.
- After `arch-init`, the root `CLAUDE.md` contains the line `@.ai/vault/architecture/system-overview.md` and no `## Architecture` prose section remains duplicated in `.ai/CLAUDE.md`.
- On a fixture project with no `domains` in `project_config.json`, phase 1 writes a `domains` block with at least one domain having `paths` and per-role `skills` keys before phase 2 runs.
- All `arch-init` edits appear only as git working-tree changes (nothing auto-committed), reviewable via `git diff`.

## Dependencies

- US-001 (vault structure/templates to write into).
- US-002 (config block + `vault_root` resolution so seeded content is readable).

## Suggested Order

3

## Domain

workflow

## Notes

Design D8 (two-phase), §3.4, §4.4, §8 step 3. Phase 1 is the higher-risk step (misroutes future tickets if wrong) — keep it a separate reviewable diff. Migration must not drop hand-written non-architecture content.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
