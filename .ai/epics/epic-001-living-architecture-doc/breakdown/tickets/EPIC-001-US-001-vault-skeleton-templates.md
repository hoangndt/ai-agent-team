## Summary

Create the `.ai/vault/` directory structure, markdown templates, and install/skeleton copy wiring so new and existing projects ship an empty vault skeleton. No behavior change to prompts yet.

## Goal

Establish the vault data layout and fixed-section templates that all later injection, distill, and ADR work targets, and make the skeleton part of the project install/template flow.

## Scope

- Create `.ai/vault/architecture/` structure: `system-overview.md`, `modules/` dir, `decisions/` dir.
- Add templates under `.ai/templates/vault/`:
  - `system-overview.md` template — fixed headings: Components (table: name, 1-line responsibility, entry-point path, module-doc link), Data Flows (numbered arrows), Invariants/Constraints, ADR Index.
  - `modules/<domain>.md` template — fixed "how it works" headings.
  - `decisions/ADR-NNN-template.md` — frontmatter (`id`, `status`, `epic`, `tickets`, `supersedes`) + Context / Decision / Alternatives / Consequences sections.
- Wire the install/skeleton flow to copy the empty vault skeleton into a project.
- Seed this repo's own `.ai/vault/architecture/system-overview.md` from the template as a placeholder (content generated later by `arch-init`).

## Out of Scope

- Any `ai_run.py` prompt injection logic (US-002).
- `arch-init` content generation / CLAUDE.md migration (US-003).
- Distill or ADR write logic (US-005, US-006).

## Acceptance Criteria

- Running the install/skeleton flow on a fresh directory produces `.ai/vault/architecture/` with `modules/` and `decisions/` subdirectories and the three template files copied in.
- `.ai/templates/vault/system-overview.md` contains all four mandated section headings (Components, Data Flows, Invariants/Constraints, ADR Index) verifiable by grep.
- The ADR template frontmatter contains all five keys (`id`, `status`, `epic`, `tickets`, `supersedes`), verifiable by parsing the YAML block.
- Existing ticket and epic pipelines run unchanged with the skeleton present (no prompt-content diff).

## Dependencies

- None (first ticket).

## Suggested Order

1

## Domain

workflow

## Notes

Fixed section headings are load-bearing: distill (US-005) and cap verification (US-005/US-006) target them by name. Keep headings stable. Design §3.1, §8 step 1.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
