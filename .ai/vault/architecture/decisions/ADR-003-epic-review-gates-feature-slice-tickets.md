---
id: ADR-003
status: proposed
epic: ""
tickets: [epic-workflow-review-and-breakdown]
supersedes: ""
---

## Context

Epic planning had a review gate only after design; analysis and breakdown were unreviewed, and tickets were single-domain.

## Decision

Add review + fix gates to every epic planning phase (analysis, design, breakdown) via a shared phase-table implementation (`epic_review_stages.py`). Breakdown yields feature-slice tickets with `## Domains`, `## Verification` (and `## Domain Checklist` when multi-domain); `epic-generate-tickets` seeds `domain` + `domains`, and ticket prompts union paths/skills/vault modules across domains.

## Alternatives

- Per-phase copy-pasted stages: rejected — drift risk.
- One ticket per domain: rejected — splits a feature across tickets without a manager verification.

## Consequences

`epic_next_action` never returns `done` before breakdown review approval; `epic-generate-tickets` requires approval once a breakdown review exists. Distill refreshes only the primary domain's module doc for multi-domain tickets.
