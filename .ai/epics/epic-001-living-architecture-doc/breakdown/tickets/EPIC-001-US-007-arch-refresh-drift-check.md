## Summary

Add the `arch-refresh` operator command: an agent re-derives the system overview from the codebase, diffs it against the current vault, and writes a drift report — without auto-overwriting the vault.

## Goal

Catch "short but wrong" drift that the line cap alone cannot detect, giving operators a reviewable diff of where the overview has diverged from the actual code.

## Scope

- New `arch-refresh` subcommand registered in `KNOWN_SUBCOMMANDS` and `sub.add_parser`.
- Prepare/act/complete shape: build a prompt that has the agent re-derive `system-overview.md` from code and diff against the current one.
- Write the drift report to `.ai/vault/architecture/_drift_report.md` (leading underscore excludes it from injection readers per US-002; overwritten each run).
- Does NOT modify `system-overview.md` — humans apply changes manually after reviewing the report.

## Out of Scope

- Auto-overwriting the overview (explicitly excluded — report only).
- Scheduling/cron of the refresh (design §9 notes as follow-up epic).
- Distill / ADR write paths (US-005, US-006).

## Acceptance Criteria

- Running `arch-refresh` writes `.ai/vault/architecture/_drift_report.md` and leaves `system-overview.md` byte-for-byte unchanged.
- The `_drift_report.md` filename begins with `_` so the US-002 module/overview readers skip it (verified: injecting a role prompt after a refresh does not include drift-report content).
- The drift report lists at least the categories of divergence (missing components, stale entries, wrong links) when run against a deliberately outdated overview fixture.

## Dependencies

- US-002 (readers must exclude underscore-prefixed files), US-003 (a populated vault to diff against).

## Suggested Order

7

## Domain

workflow

## Notes

Design §3.4, §8 step 7 (last — depends on populated vault). Report-only by design; complements the cap, which catches size but not correctness.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
