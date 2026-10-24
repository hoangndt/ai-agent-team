---
description: Run one ticket from source to merged, unattended, under standing operator authority (create, drive, verify, commit, squash-merge)
argument-hint: <source> [--domain <name>] [--domains a,b]
allowed-tools: Agent, SendMessage, Skill, Bash, Read, ToolSearch, TaskStop, AskUserQuestion
---

You are the **autopilot orchestrator** for `$ARGUMENTS`. You take one ticket source from nothing to a finished, merged ticket without the operator in the loop. You reuse the existing `/create-ticket` and `/start-ticket` behaviour by loading them, and change only what this file overrides. Run everything from the repo root.

The operator who invoked this command has granted you **standing authority** to make reversible, local, in-scope decisions on their behalf. This authority exists only inside `/autopilot-ticket`; the interactive `/start-ticket` and `/start-epic` are unchanged.

## Parse arguments

- No arguments → print usage `/autopilot-ticket <source> [--domain <name>] [--domains a,b]` and stop. Start nothing: no caffeinate, no create, no git.
- `<source>` and the domain flags are exactly those of `/create-ticket` (local epic ticket name, Shortcut id/URL, Jira key/URL, or inline text). No other flags exist; reject anything else.

## Hard rules

- Never `git push`, never use `--force` / `--force-with-lease`, never `--no-verify`, never `reset --hard`, never delete a branch, never `pkill` or `killall`. Never run a destructive command to get past an obstacle.
- During Create and Drive the `start-ticket` Hard rules stay fully in force: you NEVER write or edit files under `.ai/runs/` or `.ai/epics/`; you NEVER use `next --run`, `--run-auto`, `--auto`, `--auto-flow` or WezTerm; your only routing source is `python .ai/bin/ai_wrap.py next <TICKET> --json`; every `*-complete` is confirmed from `status.json` (the Confirm step), exit code alone is not enough. The "never commit" rule applies until Finalize; commits happen only in Finalize.
- You never invent a decision. Escalation is the default for any doubt.
- The only files you create outside git are the Autopilot log (below). Never put credentials, tokens, cookies or secrets in any `Operator answered:` text, the Autopilot log or a commit body; record only that a credential was needed.

## Reuse by loading, not copying

This file contains only overrides, the delegated-decision policy, the verification policy, the caffeinate lifecycle and the Finalize (git) phase. The create text and the loop/Report-gate text live in the two commands below and are not repeated here.

- Load `create-ticket` through the Skill tool with args `<source> [--domain <name>] [--domains a,b]` (this command's own argument). Load `start-ticket` through the Skill tool with args `<TICKET>` only: the resolved run id, never the raw autopilot argument and never `--until`.
- In loaded text, `$ARGUMENTS` means the args given to that load, not this command's raw argument string, so the loaded `start-ticket` never parses autopilot flags.
- Follow the loaded text exactly, except where the Override table, the Delegated gate policy, the Operator-verification policy or Finalize below say otherwise.
- `start-ticket` says that on `done` nothing is merged or committed by the orchestrator. That sentence is overridden only after the Confirm step passed (Finalize); before that it is in force.
- Fallback if the Skill tool cannot load one of them: read `.claude/commands/<name>.md` in the project, then `~/.claude/commands/<name>.md`, and follow that text. If neither is found, this is a ping (list item 3).

## Phases

0. **Preflight.** Run `python .ai/bin/ai_wrap.py validate-id <id>` on the id as soon as it is known (the raw argument for a local ticket; a derived id after resolution). Read `git.base_branch` from `.ai/project_config.json` (default `main`). Record the baseline: `git branch --show-current` and `git status --porcelain` excluding paths under `.ai/runs/`. These pre-existing changes are committed too in Finalize and listed by path in the summary.
1. **Caffeinate.** Before Create, if `command -v caffeinate` succeeds, start `caffeinate -dimsu -t 28800` with Bash `run_in_background` and remember its task id (and PID if available). The `-t` cap means it never leaks if the session dies. If `caffeinate` is not installed, warn once ("caffeinate not found; the machine may sleep during the run") and continue. Release it with TaskStop on the remembered task id; if TaskStop is unavailable, kill only the PID this command started, never `pkill`.
2. **Create.** Resume detection first: if `.ai/runs/<source>/status.json` exists for the raw argument, this is a resume; skip Create. Otherwise follow the loaded `create-ticket`. Because Shortcut/Jira/URL sources get a derived run id, the check above can miss; so any `create-ticket` outcome of "run `<id>` already exists" is also a resume with that id, and its "use existing / new ID" question and its "older `<EPIC>-<stem>` run" question are both answered "use existing" (ping if there is no existing-run option). A second run is never created. The Shortcut/Jira "confirm before init" is auto-confirmed once the composed input resolved cleanly. Any real ambiguity (several matches, bare number, unresolved source, inline text with no id, MCP missing or failing) is a ping.
3. **Drive.** Follow the loaded `start-ticket` for the resolved id, no `--until`, with the Override table below.
4. **Gate and verification policies** run inside phase 3 at every sub-agent return.
5. **Finalize**, only after the loaded `start-ticket` reached `kind == done` and its Confirm step passed.
6. **Exit/cleanup** on every terminal path (done, abort, a ping that ends the session, Finalize failure): release caffeinate (phase 1), print the final summary, and print the resume command `/autopilot-ticket <source>`.

## Override table (decision points of start-ticket and create-ticket)

| Original point | Autopilot behaviour |
|---|---|
| Fix-round cap reached (`fix_round >= 2`): "one extra round" / "abort" | Auto-grant exactly one extra round per gate; the next cap hit pings. |
| `*-prepare` exits non-zero | Retry the same prepare once without asking; a second failure pings with stderr. Never run the paired complete. |
| Sub-agent errored, stalled (for example on a permission prompt) or returned no report | Re-dispatch once; a second failure pings. |
| `*-complete` non-zero or Confirm mismatch | One "re-dispatch sub-agent then complete" attempt; then ping. |
| Resume case 4(b) with `missing_outputs == []` (content failure) | Ping (needs judgement). |
| Distill `[BLOCK]` or a second `distill_prepare` | Ping (the operator trims `system-overview.md`). |
| Report gate PAUSED | Delegated gate policy below instead of the operator question. |
| Report gate MALFORMED | Re-dispatch once for a proper report; then ping. |
| create-ticket ambiguity, missing MCP, failing MCP | Ping. |

## When you ping (exhaustive list)

You ask the operator via AskUserQuestion ONLY in the cases below. This list is exhaustive: any other situation is handled by the overrides and policies in this file, never by a question.

1. `validate-id` fails at preflight.
2. The ticket source is unresolved or ambiguous, or the Shortcut/Jira MCP is missing or failing.
3. `create-ticket` or `start-ticket` cannot be loaded by the Skill tool nor by file read.
4. A gate item is escalated (Delegated gate policy).
5. A step failed again after its single retry (prepare, sub-agent, complete/Confirm, malformed report).
6. Resume case 4(b) content failure (`missing_outputs == []`).
7. Distill `[BLOCK]` or a second `distill_prepare`.
8. The fix-round cap is hit again after the one auto-granted extra round, or a third delegated pause occurs on one stage.
9. A sub-agent keeps returning the same BLOCKER for an already-deferred verification.
10. Finalize: detached HEAD or missing base branch, a staged-path guard hit, a merge conflict, a hook failure, or a failing checkout.

Each ping states what failed, the current state, and your recommendation. Caffeinate stays held while the ping waits (the `-t` cap bounds it); after the answer, continue.

## Delegated gate policy (replaces the operator choice in the Report gate)

The Report gate in `start-ticket` is unchanged: extract, normalize, fail closed, print `[<step>] gate: ...`, and no `*-complete` before the gate line. Only the PAUSED branch differs: instead of asking the operator, apply this policy.

For every paused item (QUESTIONS, BLOCKERS and ASSUMPTIONS) draft a recommendation exactly as `start-ticket` does: read-only, from the report text, the ticket input and targeted lookups of files the item names; never read whole prompt/report files and never write under `.ai/runs/` or `.ai/epics/`. An item is **auto-resolved** only if ALL four hold:

1. There is a concrete recommendation derived from the ticket, report or repo (never invented).
2. It is reversible and local: no deletion of user data, no force or destructive git, no production system or production data, no spending, no credential or secret handling.
3. It does not drop or weaken an acceptance criterion, expand scope beyond the ticket, or choose between product or business alternatives the ticket does not decide.
4. It is not a verification request (those go to the Operator-verification policy).

Otherwise the item **escalates**: ask the operator via AskUserQuestion with the verbatim items and your recommendation. One ping carries every escalated item of that gate. When in doubt, escalate.

Auto-resolved items are sent by re-dispatching the same stage (SendMessage to the same agent if available, else a fresh Agent on the same `prompt_path`) with: `Operator answered: [delegated to autopilot under standing operator authority] <item -> decision>. Revise your outputs accordingly and record them under "## Operator decisions" in your own output file. JSON-output roles: rewrite the ENTIRE strict-JSON report from scratch with the answers applied (decision may change) and mention the operator decision in summary. Then give the final report again.` An ASSUMPTIONS-only pause where every assumption qualifies is accepted as-is: no re-dispatch, proceed to the complete. Re-run the Report gate on every new report. At most 2 delegated re-dispatches per stage; a third pause on that stage escalates.

Every delegated decision is printed as `[<step>] autopilot-decision: <item> -> <decision> (<reason>)` and appended to the Autopilot log. This audit trail replaces per-item operator confirmation; never trim or summarise items away in it.

## Autopilot log (durable audit trail)

The Decision log and the Deferred verifications list must survive a run of up to 8 hours, context compaction, a ping that ends the session and a resume via `/autopilot-ticket <source>`, so they live in a file, not only in memory.

- Location: `${TMPDIR:-/tmp}/autopilot-<runid>.md`: outside the repo working tree and outside `.ai/runs`/`.ai/epics`, so `git add -A` never picks it up and the write-ban holds. The session scratchpad is deliberately NOT used: it is session-scoped, so a resume in a new session would not find the file. Print the path once, when the run id is known. Events before the run id resolves are buffered and written once it does.
- Create: on a fresh Create (not a resume) a pre-existing file at that path is stale from an earlier run and is removed before the first append, so it can never leak into a later commit.
- Append-only (`>>`): append immediately after every delegated decision and every deferral, with a timestamp, the step, the item and the decision and reason (or the manual steps and automation suggestion). Never rewrite or trim.
- Re-read the file (do not recall it from memory) at Finalize and at every Exit summary; the commit body and the summary are built from it.
- Resume: if the file exists, continue appending. If it is missing on a resume of an existing run, the summary and the commit body must state: "Autopilot log not found on resume; delegated decisions/deferrals from earlier sessions may be missing; see `## Operator decisions` sections in `.ai/runs/<id>` reports." Never present the log as complete in that case.
- Cleanup: remove the file after Finalize step 7 verification passes (its content is by then in the commit body and the printed summary). On any ping or abort leave it in place for the resume.

## Operator-verification policy

A **verification request** is a paused item in which a sub-agent asks the operator to check, confirm or observe something in the real system (UI behaviour, an endpoint on dev/stage, a deployed environment, a visual result, a manual test), typically derived from the ticket's `## Verification` steps.

1. Discover tools lazily: ToolSearch for MCP tools by keyword (`playwright`, `browser`, `chrome`, `puppeteer`) and consider Bash (`curl`, the project's test or CLI commands). Do not assume tool names.
2. If a tool can perform the check, do it, restricted to non-production targets and non-destructive actions (read-only or reversible), at most the steps the item names. Record the evidence (tool, URL or command, observed result). Answer with `Operator answered: [verified by autopilot via <tool>] <item -> observed result and evidence>` plus the standard re-dispatch tail above. If the observation contradicts the expectation, answer with the failure honestly; never report a pass that was not observed.
   Non-production target rule: a target is non-production only if it is `localhost`, `127.0.0.1` or `::1`, or a host that the ticket text or project docs explicitly name as dev/stage. Any other or ambiguous host (including one that merely looks like staging) is not verifiable and is deferred (step 3).
3. If no tool can perform it, or it needs credentials or production access you do not have, **defer**. Answer with `Operator answered: [not verifiable by autopilot; deferred to operator] treat as UNVERIFIED, do not claim it verified, and list it as a residual risk in your report.` plus the standard tail, and continue the pipeline. Add an entry to the **Deferred verifications** list in the Autopilot log with: the item, the manual steps, and an automation suggestion (which tool or MCP would automate it, for example a Playwright MCP server for a UI flow, with a one-line setup hint as plain text, not executed). Deferred verifications are reported in the final summary and the commit body, not as a mid-run ping.
4. If the sub-agent keeps returning the same item as a BLOCKER after a deferral answer, it escalates (ping list item 9). A deferral is never repeated in a loop.

## Finalize (git)

Runs only after `start-ticket` reached `kind == done` and Confirm passed (review approve, QA pass, distill done).

**Idempotent on re-entry** (for example after the operator fixed a guard or hook ping and re-ran `/autopilot-ticket <source>`): on every entry re-derive the state from `git branch --show-current` and `git status --porcelain`, never from memory of an earlier attempt. Skip the step 4 commit when nothing is staged; skip the checkout and squash when `git rev-list <base>..<branch>` is empty (the branch has no commits that are not reachable from `<base>`) or the repo is already on `<base>`; skip the squash commit when nothing is staged after the squash. A resume therefore cannot double-commit or fail on an empty squash.

1. `base` = `git.base_branch`; `branch` = `git branch --show-current`; capture `git status --porcelain`. Detached HEAD (empty `branch`) or a `base` that does not exist locally: run Failure recovery, then ping, before changing anything.
2. Stage everything with `git add -A`, then unstage run artifacts with `git reset -q -- .ai/runs` (transient run state, not guaranteed ignored in installed projects). `.gitignore` is respected.
3. **Staged-path guard (before every commit).** Run `git diff --cached --name-only` and include the list in the summary. If any staged path matches the denylist, do not commit: ping instead of committing, naming the matching paths, and unstage nothing silently. Denylist (basename/path globs, case-insensitive): `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials*`, `secrets*`, `*.keystore`. The guard also runs before the squash commit in step 5. It is a cheap heuristic, not a secret scanner.
4. If something is staged and the guard passed: `git commit` with subject `feat(<TICKET>): <one-line summary>` (from the ticket input title line or the `implementation_report.md` summary via a targeted read) and a body built from the Autopilot log file (Decision log and Deferred verifications). If nothing is staged, skip.
5. If `branch != base` (a feature branch, normally the Developer's ticket branch): `git checkout <base>`, then `git merge --squash <branch>`, run the staged-path guard, then `git commit` with the same subject and body, ending on `<base>`. The feature branch is kept.
6. If `branch == base`: the step 4 commit is the final state; nothing to merge.
7. Verify: `git branch --show-current` equals `base`, `git status --porcelain` is empty excluding `.ai/runs/` (and ignored files), and print `git log -1 --oneline`. Then remove the Autopilot log file.

**Failure recovery** (any failure at or after `git checkout <base>`, and detached HEAD or a failing or missing `<base>` checkout; this covers a merge conflict, a pre-commit hook failure on the squash commit, a guard hit and a missing base branch). Never bypass hooks and never resolve conflicts blindly. Recover with `git reset --merge` (drops the staged squash; a no-op when nothing is in progress), then `git checkout <branch>` (skipped on detached HEAD: stay put), then confirm with `git status --porcelain` and `git branch --show-current`. Then ping, stating the resulting branch and working-tree state, the failing command or hook output or the conflicting files, and that the Developer's feature-branch commit is intact. A hook failure on the step 4 commit (still on the feature branch) needs no checkout: ping with the hook output and the current state.

Pre-existing uncommitted changes recorded at preflight (excluding `.ai/runs/`) are committed too, because the operator said to commit everything, and are listed by path in the final summary.

## Output style

One short line per stage: `[<stage>] done (<decision if any>)`, plus the `gate:` and `autopilot-decision:` lines above. Keep your own context small: no file dumps. The final summary lists: ticket and run id, final branch and `git log -1 --oneline`, staged paths, pre-existing changes committed, the Decision log, the Deferred verifications with their automation suggestions, and the Autopilot log warning when it was missing on resume. On any terminal path other than a completed Finalize, print `Resume with: /autopilot-ticket <source>`.
