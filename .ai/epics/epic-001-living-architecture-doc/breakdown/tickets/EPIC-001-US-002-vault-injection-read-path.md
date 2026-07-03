## Summary

Add the `vault` config block and the read-path injection so every agent prompt carries the system overview (all roles) plus the resolved domain module doc (architect/developer/epic_analyst/epic_designer only), with graceful no-op when the vault is absent.

## Goal

Inject token-capped vault content into ticket and epic role prompts, reusing existing domain resolution, so agents start with an accurate map instead of re-deriving the system — while keeping vault-less projects byte-for-byte unchanged.

## Scope

- New optional `vault` block in `project_config.json` with defaults: `enabled`, `path` (`.ai/vault`), `overview_cap_lines` (200), `module_cap_lines` (400), `inject_modules_for` (`["architect","developer","epic_analyst","epic_designer"]`). `enabled` effective only when the vault dir exists.
- `ai_run.py` helpers: `vault_root()` (returns `None` when disabled/absent), `read_vault_overview()` (returns `""` on missing), `read_vault_modules(domains, role)` (concatenated, deduped, empty unless role in `inject_modules_for`), `build_vault_context(domains, role)` (assembles `# Architecture (Vault)` section, `""` when nothing to inject).
- Wire `build_vault_context` into `build_role_prompt` (after Project Context, before skills) and `build_epic_role_prompt` symmetrically. Tickets use `get_ticket_domain` (single); epics use `get_epic_domains` (union, deduped).

## Out of Scope

- Vault directory/template creation (US-001).
- Content generation via `arch-init` (US-003).
- Any write/distill logic (US-005+).
- Cap enforcement (verification lives in distill-complete, US-005).

## Acceptance Criteria

- With a populated vault, an architect ticket prompt contains the `# Architecture (Vault)` section with overview text and exactly the resolved domain's module doc; a reviewer prompt contains overview but no module doc.
- An epic_designer prompt for a multi-domain epic contains the deduped union of module docs across resolved domains.
- With no `.ai/vault/` present (or `enabled` false), `build_role_prompt` and `build_epic_role_prompt` produce output identical to pre-change (no `# Architecture (Vault)` section), verified by a diff test.
- `build_project_context` signature is unchanged; vault injection is a sibling section.

## Dependencies

- US-001 (vault structure + templates must exist to populate/read).

## Suggested Order

2

## Domain

workflow

## Notes

Design D3 (injection breadth), D6 (config), D7 (multi-domain union/dedup), §3.2, §4.1. Reuse `get_ticket_domain`, `get_epic_domains`, mirror `build_epic_project_context` path-union at `ai_run.py:910`.

## References

- [Epic Analysis](.ai/epics/epic-001-living-architecture-doc/analysis/epic_analysis.md)
- [Epic Design](.ai/epics/epic-001-living-architecture-doc/design/epic_design.md)
- [Epic Story Status](.ai/epics/epic-001-living-architecture-doc/breakdown/epic_story_status.md)
