---
id: ADR-004
status: proposed
epic: ""
tickets: [autonomous-ticket-agent]
supersedes: ""
---

## Context

`/start-ticket` pauses for the operator at every Report gate and never commits, so a ticket cannot run source-to-merge unattended.

## Decision

Add `/autopilot-ticket` in the wrapper layer: standing operator authority replaces questions with a delegated gate policy (narrow auto-resolve, escalate by default, cap 2 per stage) and a verification policy; every decision is appended to a durable audit log (`${TMPDIR:-/tmp}/autopilot-<runid>.md`); Finalize commits only after Confirm, then pushes the current branch when `origin` exists, else squash-merges into `git.base_branch`.

## Alternatives

- Flag on `/start-ticket`: rejected — would weaken its operator-waiver and no-commit invariants.
- Runner-side auto-merge: rejected — runner never runs git.

## Consequences

Waiver/no-commit invariants are relaxed only inside `/autopilot-ticket`; never force-push (only the single plain Finalize push to `origin`)/`--no-verify`/`reset --hard`/branch deletion; `.ai/runs/` never committed.
