# Epic: Living Architecture Doc (Context Vault)

## Problem

The AI workflow has zero memory across tickets and epics. Every prompt built by `ai_run.py` contains only static project context (project name, domain, relevant paths from `project_config.json`) plus role instructions and skills. There is no place to store high-level architecture knowledge, so every new ticket/epic forces agents to re-investigate the whole system from scratch — wasted tokens, slower runs, inconsistent understanding between runs.

## Goal

Introduce a repo-internal, machine-maintained "living architecture doc" under `.ai/vault/` that:

1. Gives every agent an always-fresh, token-capped map of the system.
2. Is updated by the workflow itself when tickets land — freshness guaranteed by process, not discipline.
3. Doubles as a human-browsable knowledge base (Obsidian-compatible plain markdown; Obsidian is a viewer only, never a dependency).

## Proposed Design (starting point for analysis/design stages)

### Vault structure

```
.ai/vault/
  architecture/
    system-overview.md        # components, boundaries, data flows — hard cap ~150-200 lines
    modules/<domain>.md       # per-domain detail, matches domains in project_config.json
    decisions/ADR-NNN-*.md    # why choices were made, linked to originating tickets
```

### Injection rules (token control — do NOT inject whole vault)

- `system-overview.md`: always injected into every role prompt (ticket + epic pipelines). Small by design (~2-4k tokens).
- `modules/<domain>.md`: injected only for the ticket's/epic's resolved domain(s). Reuse existing domain resolution (`get_ticket_domain`, `get_epic_domains`) and content loading (`load_skill_contents`) mechanisms in `ai_run.py`.
- ADRs: never auto-injected. Overview links to them; agents read on demand.
- Missing vault files must degrade gracefully (empty section, no crash) so existing projects keep working.

### Update loop (keeps doc alive)

1. Developer's `implementation_report.md` gains a required `## Architecture Impact` section ("none" is a valid value).
2. New distill step when a ticket finishes (after QA pass / as part of finalize): an agent merges the architecture impact + design_note delta into `system-overview.md` and the domain module doc. Must respect the line cap — adding a component requires compressing/pruning elsewhere.
3. Epic level: after epic design approval, distill target architecture into module docs marked `status: planned`; flipped to `current` as implementing tickets land.

### ADR lifecycle (two-level: epic = birthplace, ticket = evidence trail)

ADR frontmatter links both levels:

```yaml
---
id: ADR-NNN
status: proposed | accepted | superseded
epic: <epic-id>            # origin of decision (omitted for ticket-only ADRs)
tickets: [US-XXX, ...]     # implementing tickets, appended as they land
supersedes: ADR-MMM        # optional
---
```

Lifecycle mapped onto existing stage flow:

1. **Epic design approved** (`epic-review-complete` → approve): distill trade-offs from `epic_design.md` into ADR(s) with `status: proposed`, linked to the epic. Big architecture decisions are made and reviewed at epic level — this captures the "why / alternatives considered" that otherwise stays buried in `.ai/epics/<EPIC>/design/`.
2. **Ticket lands** (distill step): append ticket to the ADR's `tickets:` list; flip `proposed → accepted` when the first implementing ticket ships. Pairs with the `planned → current` flip on module docs.
3. **Ticket-level ADR**: decisions made during implementation with no parent epic are still valid ADRs — `epic:` field omitted.
4. **Prune signal**: `status: proposed` ADRs with zero linked tickets after an epic is abandoned mark the stale `planned` module-doc entries to prune.

### Bootstrap

- New `arch-init` command in `ai_run.py`: one-time agent pass that sweeps the codebase and writes the initial `system-overview.md` + per-domain module docs.

### CLAUDE.md integration (avoid stale/duplicate docs)

Survey of the 10 projects in `projects.json` (all use this workflow):

- Root CLAUDE.md: 4 projects have none, 4 have GitNexus-boilerplate-only, 2 (ecommerce-shopify-backend, mi-portal) have hand-written `## Architecture` sections that directly overlap with system-overview content.
- `.ai/CLAUDE.md`: exists in 9/10 projects and is loaded in addition to root CLAUDE.md whenever an agent touches files under `.ai/` (every workflow run does). Contents vary: 4 are copies of the workflow Operating Guide, opslane has 412 lines including Architectural Notes + Vision & Strategy, pclab/shopify-template-jp/-in carry stack guides and role rules, and mi-portal duplicates its root CLAUDE.md (architecture loaded twice per session).

Rules:
- Canonical placement: `.ai/CLAUDE.md` = workflow operating guide only (installer-shipped, project-agnostic). Root CLAUDE.md = project conventions + `@` import of the overview: `@.ai/vault/architecture/system-overview.md`. Architecture prose lives in neither — single source of truth is the vault, and vault updates propagate through the import automatically.
- `arch-init` migration scans BOTH root CLAUDE.md and `.ai/CLAUDE.md` for architecture/stack content, dedupes across the two, and uses the union as a seed source for the vault (alongside the codebase sweep). Project-wide architecture goes to `system-overview.md`; domain/stack-specific detail (e.g. opslane Architectural Notes, pclab Backend Stack, shopify storefront/extensions sections) goes to `modules/<domain>.md`.
- After seeding, migration replaces the root `## Architecture` section with the import line and strips migrated sections from `.ai/CLAUDE.md`. These one-time edits are human-reviewed via git diff.
- If root CLAUDE.md is absent or boilerplate-only: generate vault, append the import line (create a thin CLAUDE.md if missing).
- Non-architecture content (commands, conventions, tool rules, role output rules) is untouched and stays hand-maintained in its current file.
- The ongoing distill step never edits either CLAUDE.md; it may flag contradictions between CLAUDE.md and reality as a note in the report.
- Workflow prompts inject vault content directly and do not depend on CLAUDE.md; the import only serves interactive Claude sessions.

### Keeping system-overview short but sufficient

The cap only works if the overview is a map, not an encyclopedia. Three-layer progressive disclosure, each layer answering one question:

| Layer | Question | Size |
|---|---|---|
| `system-overview.md` | what exists, where, how connected | ~150-200 lines |
| `modules/<domain>.md` | how it works | larger, own cap |
| ADRs | why | unbounded, read on demand |

Mechanisms:
1. Fixed template with mandated sections: Components (table: name, 1-line responsibility, entry-point path, module-doc link), Data flows (numbered arrows), Invariants/constraints, ADR index. Tables over prose.
2. Distill prompt rule: every line must pass "would an agent make a wrong decision without this line?" — otherwise cut or push down to the module doc. New components get a link, not a description.
3. Enforcement: `*-complete` verification checks the line cap; over cap → distill re-runs with a compress instruction. Cap configurable in `project_config.json` with sane defaults.
4. `arch-refresh` command: agent re-derives the overview from the codebase and diffs against the current one — catches "short but wrong" drift that the cap alone cannot.

### Configuration

- Extend `project_config.json` if needed (e.g., vault path override, cap sizes), with sensible defaults so zero config changes are required for existing projects.

## Scope

In scope:
- `.ai/vault/` structure + templates
- `ai_run.py` changes: injection into `build_project_context`/`build_role_prompt`/`build_epic_role_prompt` (or equivalent), `arch-init` command, distill step wiring into the stage flow
- Agent role instruction updates (developer report section, new distill role or reuse of existing roles)
- ADR creation/update wiring: distill ADRs at epic design approval, update ADR ticket links + status flips in the ticket distill step
- Prompt/verification updates in `*-complete` steps (e.g., check `## Architecture Impact` present, enforce overview line cap)
- Install/template flow: ship empty vault skeleton for new projects
- CLAUDE.md migration in `arch-init` (seed from existing `## Architecture` section, replace with `@` import line) + `arch-refresh` drift-check command

Out of scope:
- RAG/embedding retrieval — plain file injection only
- Obsidian plugins, MCP servers, or any Obsidian-specific syntax requirements (wikilinks optional garnish only)
- Cross-project/global vault — vault is per-project inside the repo
- Injecting raw run history into prompts

## Success Criteria

- New ticket in a bootstrapped project: architect/developer prompts contain system overview + correct domain module doc, and prompt size increase stays within the defined cap.
- Completing a ticket with architecture impact updates the vault automatically; overview stays under the line cap.
- Project without a vault runs the full pipeline unchanged (backward compatible).
- `arch-init` produces a usable overview + module docs on this repo itself as the reference case.

## Risks / Open Questions

- Distill step bloating the overview over time → cap enforced in prompt AND verified in complete step.
- Stale planned-vs-current drift if epics are abandoned → distill step should prune `planned` entries with no active tickets.
- Where exactly the distill step hooks in: `qa-complete`, a new `finalize` stage, or a standalone command? Design stage to decide.
- Whether reviewer/QA roles also need module docs injected, or only architect/developer (token trade-off).
