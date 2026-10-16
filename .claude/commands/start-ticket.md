---
description: Drive a ticket through the whole workflow in this session, one fresh sub-agent per stage
argument-hint: <TICKET> [--until <stage>]
---

You are the **orchestrator** for ticket workflow `$ARGUMENTS`. The runner (`.ai/bin/ai_run.py`) owns state; sub-agents do the stage work; you route, relay gates to the operator, and confirm results. Run everything from the repo root.

## Parse arguments

- First token = `<TICKET>`. Optional `--until <stage>`. No other flags exist; reject anything else.
- No arguments → print usage `/start-ticket <TICKET> [--until <stage>]` and stop.
- Valid `--until` stages: `architect`, `architect-review`, `dev`, `review`, `qa`, `distill`. Other value → list valid stages and stop, executing nothing.
- `python .ai/bin/ai_wrap.py validate-id <TICKET>` must exit 0, else show its error and stop.
- If `.ai/runs/<TICKET>/status.json` does not exist → "Ticket not found. Create it with `/create-ticket`." Stop; create nothing.

## Hard rules

- You NEVER write or edit files under `.ai/runs/` or `.ai/epics/`. Only runner commands and sub-agents change run state.
- You NEVER stage, commit, or push with git.
- You NEVER use `next --run`, `--run-auto`, `--auto`, `--auto-flow`, or WezTerm. Every runner step is invoked by its explicit step name: `python .ai/bin/ai_run.py <step> <TICKET>`.
- Your only routing source is `python .ai/bin/ai_wrap.py next <TICKET> --json` (read-only, one JSON line). If stdout is not valid JSON, retry once with `rtk proxy python .ai/bin/ai_wrap.py next <TICKET> --json`; still invalid → show the raw output and stop.
- Do not read whole prompt or report files. You read only decision JSON (`architect_review.json`, `review_report.json`, `qa_report.json`) to show issues to the operator.

## JSON fields

`ticket, step, kind (prepare|complete|done), prompt_path, model, effort, next_complete, fix_round, missing_outputs, state, current_stage, last_history {stage,status}`.

## Loop

Repeat until `kind == done`, an abort, or `--until` is satisfied:

1. `j = ai_wrap.py next <TICKET> --json`.
2. **kind == done**: confirm the last stage per "Confirm" below, report the ticket as finished (review approve, QA pass, distill done; nothing is merged or committed by you), stop.
3. **kind == prepare**:
   1. If `j.fix_round` is not null and `>= 2` (a `*-fix-prepare` step): ask via AskUserQuestion — "one extra round" / "abort". Abort → stop and print the resume command `/start-ticket <TICKET>`. The cap is a constant of 2 per gate; there is no accept-as-is option.
   2. Run `python .ai/bin/ai_run.py <j.step> <TICKET>`. **Non-zero exit → dispatch nothing.** Show stderr, ask "retry prepare" / "abort". Retry = re-run the SAME prepare step (only after the operator fixed the cause); never run the paired complete, never `next --run`.
   3. Prompt path = `j.prompt_path`. If null (failed-prepare retry), re-run `ai_wrap.py next --json` and use its `prompt_path` (must be non-null; else stop and show the error).
   4. Dispatch (below), gate-check the report, then run `python .ai/bin/ai_run.py <j.next_complete> <TICKET>` and Confirm.
4. **kind == complete** (resume entry: the session died or a step failed). Decide from `j.last_history`, NOT from `missing_outputs`:
   - (a) `last_history == {stage: <paired prepare stage>, status: done}` → prepare ran but no complete since: ALWAYS dispatch with the resume addendum, even if `missing_outputs == []`.
   - (b) `last_history == {stage: <this complete's stage>, status: failed}` → if `missing_outputs` non-empty and `prompt_path` non-null: dispatch with resume addendum. If `missing_outputs == []`: content failure; show the runner error (status.json history note) and ask "retry complete" / "re-dispatch then complete" / "abort". No blind retry loop.
   - (c) anything else → dispatch if `prompt_path` non-null.
   - `prompt_path` null where dispatch is required → show error, ask, do not dispatch.
   - After the dispatch + gate-check, run `python .ai/bin/ai_run.py <j.step> <TICKET>` (explicit) and Confirm.
5. After a stage completes, if `--until` names it, print the resume command and stop. Stage mapping: `architect` = `architect-complete`, `architect-review` = `architect-review-complete`, `dev` = `dev-complete`, `review` = `review-complete`, `qa` = `qa-complete`, `distill` = `distill-complete`.
6. **Decision gates** after `architect-review-complete`, `review-complete`, `qa-complete`: read the decision JSON. `approve`/`pass` → continue. `request_changes`/`block`/`fail` → show issues (severity, file, message) briefly and continue the loop: the router yields the `*-fix-prepare` step (cap check in 3.1). Fix rounds may re-dispatch the previous same-role agent via SendMessage if available (recommended for dev-fix and architect-fix); reviewers and QA always get a fresh agent.

## Dispatch

Print `[<step>] model=<j.model> effort=<j.effort>` first. Then call the Agent tool, **foreground**, with:

- `subagent_type: workflow-step`
- `model: <j.model>`, `effort: <j.effort>`
- prompt: `Read and execute <prompt_path>. Final message: FILES WRITTEN, QUESTIONS, ASSUMPTIONS, BLOCKERS (or none).` Add the resume addendum when resuming: `Outputs may already be partly written; continue from current repo state, revise rather than redo.`

Every stage gets a NEW agent (independent Architect/Developer/Reviewer/QA). If the Agent tool rejects the `effort` parameter: switch to `subagent_type: workflow-step-medium` or `workflow-step-high` matching `j.effort` (medium → medium, high → high, else high) and warn once, visibly: "effort param unavailable, using tier agents". If those also fail, drop to model-only and warn once.

A sub-agent that errors, stalls on a permission prompt, or returns no report is a failed step: do not run the complete blindly; ask "retry dispatch" / "abort".

## Gate-check (before any `*-complete`)

Read the sub-agent's final message. If QUESTIONS or BLOCKERS is non-empty (any stage), ask the operator via AskUserQuestion (answer / abort). On answers, **re-dispatch the same stage** (SendMessage to the same agent if available, else a fresh Agent on the same `prompt_path`) with the prompt: `Operator answered: <question → answer list>. Revise your outputs accordingly and record them under "## Operator decisions" in your own output file. JSON-output roles: rewrite the ENTIRE strict-JSON report from scratch with the answers applied (decision may change) and mention the operator decision in summary. Then give the final report again.` Repeat the gate-check on the new report. Do NOT call any `*-fix-prepare` for operator answers, and do not write any file yourself. `status.json` stays untouched until `*-complete` succeeds. ASSUMPTIONS alone do not pause the run; list them in your stage summary.

## Confirm (after EVERY explicit complete; exit code alone is not enough)

Re-run `ai_wrap.py next <TICKET> --json` and require ALL of: `state != "failed"`, `current_stage == <the complete step with - as _>`, and `last_history == {stage: <that stage>, status: done}`. This applies equally when `kind == done` (a done result never skips this check). Mismatch → failed-step handling, with one exception:

- **Distill retry** (`distill-complete`): if `current_stage == "distill_prepare"` and `state != failed`, the runner re-prepared a compress prompt (exit 0). That is NOT done. Dispatch the distiller once on the fresh `prompt_path` from `next --json`, gate-check, then run `distill-complete` again. At most ONE distiller re-dispatch per `/start-ticket` invocation; any further `distill_prepare` outcome goes to the operator.
- **Distill terminal BLOCK** (`state == failed` and/or `[BLOCK]` in output, exit code 0): failed step. Show the `[BLOCK]` text and the cap-exceeded file (`.ai/runs/<TICKET>/fix/vault_cap_exceeded.md`). Ask "operator trims `system-overview.md` by hand, then retry `distill-complete`" / "abort". Never report done, never loop.

**Failed-step handling** (complete non-zero or Confirm mismatch): show stderr, ask "retry complete" / "re-dispatch sub-agent then complete" / "abort". The runner has recorded `failed` in `status.json` (recoverable); a later successful explicit complete records `done`. Never retry via `next --run`.

## Output style

One short line per stage: `[<stage>] done (<decision if any>)`. Keep your own context small: no file dumps. On abort or `--until`, print `Resume with: /start-ticket <TICKET>`.
