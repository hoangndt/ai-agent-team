## Summary

Add the ticket distill stage: `distiller.md` role, new `distill-prepare`/`distill-complete` subcommands auto-triggered by a passing `qa-complete`, that merge architecture deltas into `system-overview.md` + the domain module doc, with cap enforcement (bounded auto-retry, then human-block on overview over-cap).

## Goal

Keep the vault fresh by process: when a ticket passes QA, produce a distill prompt, let the distill agent rewrite the vault, and verify the overview/module line caps so the load-bearing overview never silently exceeds budget.

## Scope

- New `.ai/agents/distiller.md` role (loads architect domain skills, per D2): cap rule, "map not encyclopedia" line test, prune signal for stale `planned` entries.
- New `distill-prepare` subcommand: registered in `KNOWN_SUBCOMMANDS`, `sub.add_parser`, `_PREPARE_STEP_PROMPT`, and the `next` stage router. Builds `distill/distill_prompt.md` from current overview + domain module + developer `## Architecture Impact` + design_note delta + next free ADR id (`next_adr_id()` helper). Pure-Python; auto-called by `qa_complete` on `decision == "pass"`.
- New `distill-complete` subcommand: added to `_PREPARE_TO_COMPLETE`. Verifies overview ≤ `overview_cap_lines` and module ≤ `module_cap_lines`.
- Cap enforcement (D5): over module cap → one auto-retry with compress instruction, then warn-and-proceed. Over overview cap → one auto-retry, then block the stage (write `fix/vault_cap_exceeded.md`, park on `distill-complete`, no silent proceed).
- `next_adr_id()` helper: `max(existing NNN) + 1`, zero-padded 3 digits.

## Out of Scope

- Epic-level ADR generation subcommands (US-006) — this ticket only passes the next ADR id into the prompt and flips ticket-land status where the module docs are concerned.
- `arch-init` / `arch-refresh` (US-003, US-007).
- Developer report section (US-004).

## Acceptance Criteria

- After a `qa-complete` with `decision == "pass"`, `next`/`next --run-auto` resolves to `distill-prepare` and a `distill/distill_prompt.md` is written containing the current overview, domain module, the developer `## Architecture Impact`, and a concrete next ADR id.
- On QA `fail`, `distill-prepare` is not invoked and the existing fix loop runs unchanged.
- `distill-complete` with an overview over `overview_cap_lines` triggers exactly one auto-retry; if still over, the stage does not complete and `fix/vault_cap_exceeded.md` is written listing the overage and largest sections.
- `distill-complete` with a module doc over `module_cap_lines` triggers one auto-retry then warns and proceeds (stage completes).
- `next_adr_id()` returns `001` on an empty `decisions/` dir and `max+1` zero-padded otherwise.

## Dependencies

- US-002 (readers/config), US-004 (`## Architecture Impact` input).

## Suggested Order

5

## Domain

workflow

## Notes

Design D1 (distill as full stage, no synchronous LLM call), D2 (role), D4 (ADR id), D5 (cap terminal states), §3.3, §4.2, §8 step 5. `qa_complete` auto-call is pure Python, same pattern as `build_qa_fix_context`.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
