## Summary

Mandate a `## Architecture Impact` section in the developer's `implementation_report.md` and enforce its presence in the `dev-complete` verification step.

## Goal

Capture each ticket's architecture delta at the source (developer report) so the distill step (US-005) has a structured input, and guarantee its presence via verification.

## Scope

- Update `.ai/agents/developer.md`: require a `## Architecture Impact` section in `implementation_report.md`, with `"none"` an explicit valid value; define the section shape (freeform vs. structured bullets — resolve here per design open question §9).
- Update `dev-complete` verification in `ai_run.py` to check the `## Architecture Impact` heading is present and non-empty in `implementation_report.md`; fail completion with a clear message when missing.
- Apply the same presence check on the fix-round path (`dev-fix-complete`) if it re-verifies the report.

## Out of Scope

- Consuming the section (distill, US-005).
- Any vault read/write logic.
- Overview/module cap enforcement (US-005).

## Acceptance Criteria

- A `dev-complete` run fails with an explicit "missing ## Architecture Impact" message when the section is absent from `implementation_report.md`.
- A `dev-complete` run succeeds when the section is present, including when its content is exactly `none`.
- `.ai/agents/developer.md` documents the section, its `none` sentinel, and the chosen content shape.

## Dependencies

- None strictly required for the role/verification change, but sequenced after US-002 so the developer prompt can already carry vault context. Distill (US-005) depends on this ticket.

## Suggested Order

4

## Domain

workflow

## Notes

Design §3.5, §8 step 4, open question §9 (Architecture Impact schema — decide in this ticket). Keep the check narrow (presence + non-empty), not content-quality.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
