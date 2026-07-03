## Summary

Add the epic ADR lifecycle: new `adr-distill-prepare`/`adr-distill-complete` subcommands auto-triggered by `epic-review-complete` on approve to emit `proposed` ADRs from epic design trade-offs, plus the ticket-land `proposed → accepted` / `planned → current` flips in ticket distill.

## Goal

Capture epic-level architecture decisions as `proposed` ADRs linked to the epic, then evolve them to `accepted` with a ticket evidence trail as implementing tickets land, keeping ADR frontmatter well-formed throughout.

## Scope

- New `adr-distill-prepare` subcommand: registered in `KNOWN_SUBCOMMANDS`, `sub.add_parser`, `_PREPARE_STEP_PROMPT`, and the `epic-next` router. Auto-called (pure Python) by `epic_review_complete` on `decision == "approve"`; builds a prompt to distill `epic_design.md` trade-offs into `proposed` ADR(s) linked to the epic and mark target module-doc entries `status: planned`.
- New `adr-distill-complete` subcommand: added to `_PREPARE_TO_COMPLETE`; verifies ADR frontmatter is well-formed (`id`, `status`, `epic`, `tickets`).
- Ticket-land flips (extend US-005's `distill-complete`/distiller role): append the ticket id to the relevant ADR `tickets:` list, flip `proposed → accepted` on first implementing ticket, flip module-doc entries `planned → current`.
- Prune signal: `proposed` ADRs with zero linked tickets flag their stale `planned` module entries.

## Out of Scope

- Ticket-level distill infrastructure itself (US-005).
- `arch-init`/`arch-refresh`.
- Concurrent-run ADR id locking (accepted risk per design §6).

## Acceptance Criteria

- After an `epic-review-complete` with `decision == "approve"`, `epic-next` resolves to `adr-distill-prepare` and a prompt is produced instructing creation of `proposed` ADR(s) with `epic:` set to the epic id.
- `adr-distill-complete` fails when an ADR file is missing any of `id`, `status`, or `epic` frontmatter keys, and passes when all are present and well-formed.
- When a ticket implementing an epic decision lands, `distill-complete` appends its `US-xxx` id to the ADR `tickets:` list and flips the ADR `status` from `proposed` to `accepted` on the first such ticket.
- A `proposed` ADR with an empty `tickets:` list is flagged (prune signal) with its associated `planned` module entry named in the distill output.

## Dependencies

- US-005 (ticket distill infrastructure, `next_adr_id`, distiller role).

## Suggested Order

6

## Domain

workflow

## Notes

Design D4, §3.3 (epic ADR distill), §4.3, §8 step 6. Symmetric to ticket distill; `epic_review_complete` auto-call is pure Python like the ticket side. Also update `epic_designer.md` to state alternatives-considered explicitly so ADRs have material.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
