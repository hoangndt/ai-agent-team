# Epic Analysis: Living Architecture Doc (Context Vault)

## 1. Problem Statement

The AI workflow (`ai_run.py`) has **no persistent architectural memory** across tickets and epics. Every prompt built for an agent (`build_role_prompt`, `build_epic_role_prompt`) contains only:

- Static project context — project name, domain, and relevant paths from `project_config.json` (`build_project_context`)
- The role instruction file
- Domain-specific skills (`load_skill_contents`)

There is nowhere to store durable, high-level architecture knowledge. Consequently, every new ticket or epic forces each agent to re-derive the system from scratch by reading code. This causes:

- **Wasted tokens** — the same investigation is repeated on every run.
- **Slower runs** — agents spend budget rediscovering rather than acting.
- **Inconsistent understanding** — two runs may reach different mental models of the same system, producing incoherent designs and reviews.

The epic proposes a repo-internal, machine-maintained "living architecture doc" under `.ai/vault/` that is injected into prompts (token-capped), kept fresh by the workflow itself as tickets land, and doubles as a human-browsable markdown knowledge base.

## 2. Business Goal

Success = agents start each ticket/epic with an accurate, always-fresh, token-bounded map of the system, and that map stays current **by process, not discipline**.

Concretely:

1. Every agent prompt carries a small, accurate system overview + the relevant domain module doc.
2. The vault is updated automatically when tickets finish — no manual upkeep.
3. Humans can browse the same content as plain markdown (Obsidian-compatible, but Obsidian never a dependency).
4. Existing projects without a vault keep working unchanged (backward compatible).

## 3. Success Criteria

Measurable indicators, drawn from the epic and made testable:

- **Injection correctness**: A new ticket in a bootstrapped project produces architect/developer prompts that contain `system-overview.md` plus the correct domain module doc, and nothing for unrelated domains.
- **Token budget respected**: Prompt-size increase from vault injection stays within the configured cap (overview ~150–200 lines / ~2–4k tokens; modules injected only for resolved domains).
- **Self-maintenance**: Completing a ticket that has architecture impact updates `system-overview.md` and the domain module doc automatically, and the overview remains under its line cap afterward.
- **Backward compatibility**: A project with no `.ai/vault/` runs the full ticket and epic pipelines with no crashes and no behavioral change (missing files degrade to empty sections).
- **Bootstrap quality**: `arch-init` run against *this* repository produces a usable `system-overview.md` + per-domain module docs (this repo is the reference case).
- **ADR trail integrity**: Epic design approval yields `proposed` ADRs linked to the epic; the first implementing ticket flips them to `accepted` and appends its ID to `tickets:`.

## 4. Scope

**In scope:**

- `.ai/vault/` directory structure + markdown templates (`architecture/system-overview.md`, `architecture/modules/<domain>.md`, `architecture/decisions/ADR-NNN-*.md`).
- `ai_run.py` injection changes: feed vault content through `build_project_context` / `build_role_prompt` / `build_epic_role_prompt` (or equivalent), reusing `get_ticket_domain`, `get_epic_domains`, and `load_skill_contents`.
- New `arch-init` command: one-time codebase sweep to seed the vault; includes CLAUDE.md migration (seed from `## Architecture` sections in root and `.ai/CLAUDE.md`, replace with `@.ai/vault/architecture/system-overview.md` import line).
- New `arch-refresh` command: agent re-derives the overview from code and diffs against the current vault to catch "short but wrong" drift.
- Distill step wired into the stage flow: merges developer `## Architecture Impact` + design-note delta into overview + module doc when a ticket finishes.
- ADR wiring: create `proposed` ADRs at epic design approval; update ticket links and flip status on ticket land.
- Agent role instruction updates: required `## Architecture Impact` section in `implementation_report.md`; a distill role (new or reused).
- `*-complete` verification updates: check `## Architecture Impact` is present; enforce overview line cap (over cap → distill re-runs with a compress instruction).
- Install/template flow: ship an empty vault skeleton for new projects.
- Optional `project_config.json` extensions (vault path override, cap sizes) with defaults so zero config change is required.

**Out of scope:**

- RAG / embedding retrieval — plain file injection only.
- Obsidian plugins, MCP servers, or Obsidian-specific syntax requirements (wikilinks are optional garnish).
- Cross-project / global vault — the vault is per-project, inside the repo.
- Injecting raw run history into prompts.

## 5. Stakeholders / Affected Areas

- **All workflow agents** (architect, developer, reviewer, QA, epic analyst/designer/reviewer/planner) — consume the injected vault; the developer additionally produces the `## Architecture Impact` section.
- **`ai_run.py` maintainers** — new commands (`arch-init`, `arch-refresh`), the distill step, and injection/verification changes concentrate here.
- **Project owners / installers** — every project on this template inherits the vault skeleton, CLAUDE.md restructuring, and config defaults.
- **Human developers** — gain a browsable, single-source-of-truth architecture doc; must review one-time `arch-init` migration edits via git diff.
- **This repo itself** — the reference project for validating `arch-init`.

## 6. Cross-Domain Dependencies

The template currently defines a single `workflow` domain (paths: `.ai/bin/`, `.ai/agents/`, `.ai/templates/`, `examples/`). Within *this* repo the epic is single-domain. However, the feature is **domain-generic** and must work for downstream multi-domain projects (the epic references opslane, pclab, shopify variants, mi-portal, ecommerce-shopify-backend):

- **Domain resolution ↔ module injection**: `modules/<domain>.md` selection must reuse `get_ticket_domain` (ticket) and `get_epic_domains` (epic). Multi-domain epics inject the union of module docs; tickets inject exactly one.
- **CLAUDE.md ↔ vault hand-off**: architecture prose migrates out of both root CLAUDE.md and `.ai/CLAUDE.md` into the vault; domain/stack-specific detail routes to `modules/<domain>.md`, project-wide detail to `system-overview.md`. This split must align with each project's declared domains.
- **Epic pipeline ↔ ticket pipeline**: the ADR two-level lifecycle (epic = birthplace / `proposed`; ticket = evidence trail / `accepted`) and the `planned → current` module-doc flip couple the epic and ticket flows through shared vault files.

## 7. External Dependencies

- **Obsidian** — target *viewer* for the markdown, explicitly never a runtime dependency; content must render as plain markdown without it.
- **Git** — one-time `arch-init` / migration edits are surfaced and reviewed via git diff.
- **The LLM agents themselves** — distill, `arch-init`, and `arch-refresh` are agent-driven passes; their quality bounds the vault's quality. No new third-party services, APIs, or embedding/RAG infrastructure are introduced.

## 8. Key Risks

- **Overview bloat over time** — the distill step keeps appending until the overview becomes an encyclopedia. Mitigation: cap enforced *in the distill prompt* AND *verified in the `*-complete` step*; adding a component requires pruning elsewhere.
- **"Short but wrong" drift** — a capped overview stays small yet silently diverges from reality; the cap alone cannot catch this. Mitigation: `arch-refresh` re-derives from code and diffs.
- **Stale `planned` entries** — abandoned epics leave `planned` module-doc entries and `proposed` ADRs with zero linked tickets. Mitigation: distill prune signal for `proposed` ADRs with no tickets.
- **Backward-compat breakage** — injection or verification could crash projects with no vault. Mitigation: missing vault files must degrade to empty sections, never error.
- **Token regression** — careless injection (e.g., whole vault, all module docs, ADRs) inflates every prompt. Mitigation: overview-only always-inject, domain-scoped modules, ADRs never auto-injected.
- **Migration data loss / duplication** — CLAUDE.md dedup/migration could drop hand-written content or double-load architecture. Mitigation: dedupe across both files, human git-diff review, distill never edits CLAUDE.md.
- **Distill quality/consistency** — an LLM distill that misjudges "would an agent make a wrong decision without this line?" degrades the map silently over many tickets.

## 9. Assumptions / Unknowns

Assumptions:

- Domain resolution helpers (`get_ticket_domain`, `get_epic_domains`) and content loading (`load_skill_contents`) are stable reuse points; injection hooks cleanly into `build_project_context` / `build_role_prompt` / `build_epic_role_prompt` (confirmed present in `ai_run.py`).
- A line cap is a good-enough proxy for token cap for the overview.
- Plain-markdown vault content is sufficient for both agent injection and human browsing.

Open questions (to resolve in analysis→design):

- **Distill hook point** — `qa-complete`, a new dedicated `finalize` stage, or a standalone command? (Epic leaves this to the design stage.)
- **Injection breadth** — do reviewer/QA roles also need module docs, or only architect/developer? Token-vs-context trade-off.
- **Distill role** — introduce a new distill role/agent file, or reuse an existing role (e.g., architect)?
- **Cap configuration shape** — exact `project_config.json` keys and defaults for vault path override and cap sizes.
- **Module-doc cap** — modules have their "own cap" but its value/enforcement is unspecified.
- **ADR numbering** — how `ADR-NNN` IDs are allocated and kept unique across concurrent epics/tickets.
- **Multi-domain ticket edge case** — current resolution assumes one domain per ticket; confirm no ticket needs multiple module docs.
