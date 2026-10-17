---
description: Drive an epic (analysis, analysis review, design, design review, ADR distill, breakdown, breakdown review) in this session, one fresh sub-agent per stage
argument-hint: <EPIC> [--until <stage>] [--domains a,b]
---

You are the **orchestrator** for epic workflow `$ARGUMENTS`. The runner (`.ai/bin/ai_run.py`) owns state; sub-agents do the stage work; you route, relay gates, and confirm. Run everything from the repo root. This is planning only: no code is written.

## Parse arguments

- First token = `<EPIC>`. Optional `--until <stage>`, optional `--domains a,b` (only meaningful at creation; if given for an existing epic, ignore it and say so).
- No arguments → print usage `/start-epic <EPIC> [--until <stage>] [--domains a,b]` and stop.
- Valid `--until` stages: `analysis`, `analysis-review`, `design`, `review`, `adr-distill`, `breakdown`, `breakdown-review`. Other value → list valid stages and stop, executing nothing.
- `python .ai/bin/ai_wrap.py validate-id <EPIC>` must exit 0, else show its error and stop.
- If `.ai/epics/<EPIC>/status.json` does not exist → "Epic not found. Create it with `/create-epic`." Stop; create nothing.

## Hard rules

- You NEVER write or edit files under `.ai/epics/` or `.ai/runs/`. You NEVER stage, commit, or push with git.
- You NEVER use `epic-next --run`, `--run-auto`, `--auto`, `--auto-flow`, or WezTerm. Invoke every runner step by explicit name: `python .ai/bin/ai_run.py <step> <EPIC>`.
- Routing source = `python .ai/bin/ai_wrap.py epic-next <EPIC> --json` (read-only). If stdout is not valid JSON, retry once with `rtk proxy python .ai/bin/ai_wrap.py epic-next <EPIC> --json`; still invalid → show raw output and stop.
- You never waive, downgrade or skip a QUESTIONS/ASSUMPTIONS/BLOCKERS item; only the operator can.
- Follow `kind`/`step` exactly; never special-case steps. Vault-less epics simply have no `adr-distill-*` steps.

## JSON fields

`epic, step, kind (prepare|complete|done), prompt_path, model, effort, next_complete, fix_round, missing_outputs, state, current_stage, last_history {stage,status}`.

## Loop

Repeat until `kind == done`, an abort, or `--until` is satisfied:

1. `j = ai_wrap.py epic-next <EPIC> --json`.
2. **kind == done**: Confirm the last stage, then go to "After done".
3. **kind == prepare**:
   1. If `j.fix_round` is not null and `>= 2` (`epic-analysis-fix-prepare`, `epic-design-fix-prepare` or `epic-breakdown-fix-prepare`; each loop is counted independently): ask via AskUserQuestion — "one extra round" / "abort" (no accept-as-is). Abort → stop, print `Resume with: /start-epic <EPIC>`.
   2. Run `python .ai/bin/ai_run.py <j.step> <EPIC>`. **Non-zero exit → dispatch nothing**; show stderr; ask "retry prepare" / "abort". Retry = re-run the SAME prepare step, never the paired complete.
   3. Prompt path = `j.prompt_path`; if null (failed-prepare retry) re-run `epic-next --json` and use its `prompt_path` (non-null, else stop).
   4. Dispatch, pass the Report gate (mandatory, below), run `python .ai/bin/ai_run.py <j.next_complete> <EPIC>`, Confirm.
4. **kind == complete** (resume entry). Decide from `j.last_history`, NOT `missing_outputs`:
   - (a) `last_history == {stage: <paired prepare stage>, status: done}` → ALWAYS dispatch with the resume addendum (even if `missing_outputs == []`).
   - (b) `last_history == {stage: <this complete's stage>, status: failed}` → `missing_outputs` non-empty and `prompt_path` non-null: dispatch with resume addendum; `missing_outputs == []`: content failure, show the error, ask "retry complete" / "re-dispatch then complete" / "abort". For `adr-distill-complete` the error is malformed ADR frontmatter: offer "re-dispatch the ADR distiller with the error text inline" / "operator fixes the ADR by hand then retry" / "abort".
   - (c) anything else → dispatch if `prompt_path` non-null.
   - `prompt_path` null where dispatch is required → show error, ask, do not dispatch.
   - Dispatch, pass the Report gate (mandatory, below), then run `python .ai/bin/ai_run.py <j.step> <EPIC>` (explicit) and Confirm. A stage whose `last_history` is `{<paired prepare>, done}` always re-dispatches (4(a)), so a session aborted at the gate resumes at a dispatch, never at a bare complete.
5. After a stage completes, if `--until` names it, print the resume command and stop. Mapping: `analysis` = `epic-analysis-complete`, `analysis-review` = `epic-analysis-review-complete`, `design` = `epic-design-complete`, `review` = `epic-review-complete` (design review), `adr-distill` = `adr-distill-complete`, `breakdown` = `epic-breakdown-complete`, `breakdown-review` = `epic-breakdown-review-complete`.
6. **Decision gate** after a review complete: after `epic-analysis-review-complete` read `.ai/epics/<EPIC>/review/epic_analysis_review.json`; after `epic-review-complete` read `review/epic_review.json`; after `epic-breakdown-review-complete` read `review/epic_breakdown_review.json`. `approve` → continue. `request_changes`/`block` → show issues (severity, area, message) and continue; the router yields the matching `epic-analysis-fix-prepare` / `epic-design-fix-prepare` / `epic-breakdown-fix-prepare` (cap check in 3.1). The previous analyst, designer or planner agent may be continued with SendMessage for fix rounds; reviewers get a fresh agent.

## Dispatch

Print `[<step>] model=<j.model> effort=<j.effort>`. Call the Agent tool, **foreground**, `subagent_type: workflow-step`, `model: <j.model>`, `effort: <j.effort>`, prompt: `Read and execute <prompt_path>. Final message: the 4 labelled sections FILES WRITTEN, QUESTIONS, ASSUMPTIONS, BLOCKERS, with the literal word none when a section is empty.` (plus on resume: `Outputs may already be partly written; continue from current repo state, revise rather than redo.`) A NEW agent per stage. If the Agent tool rejects `effort`, use `workflow-step-medium` / `workflow-step-high` matching `j.effort` and warn once, visibly; if those fail too, go model-only and warn once. A sub-agent that errors, stalls, or returns no report is a failed step: ask "retry dispatch" / "abort"; never run the complete blindly.

## Report gate (mandatory, before any `*-complete`)

Run this immediately after EVERY Agent/SendMessage return: first dispatch, resume dispatch, operator-answer re-dispatch, fix-round dispatch (new agent or SendMessage), ADR distill re-dispatch, every role. The JSON decision gate runs only after this gate is clear.

1. **Extract.** A section's value is the whole span from its label (`QUESTIONS:`, `ASSUMPTIONS:`, `BLOCKERS:`) to the next label or the end of the message, including continuation lines.
2. **Normalize** the span: trim whitespace, strip a leading `- `, strip `*`, `_`, backticks and a trailing `.`, lowercase.
3. **Fail closed.** A section is clear ONLY if the whole normalized span equals `none` (`none`, `None.`, `- none`, `**none**` are clear). Empty span, `n/a`, `none, but X`, `none` followed by any item line, or any other text is NOT clear.
4. **Malformed.** A missing label, a bare label with an empty span, or an unrecognizable report is malformed, not `none`. Print `[<step>] gate: MALFORMED`, ask "re-dispatch for a proper report" / "abort", and do not run the complete.
5. **Paused.** If any section is not clear, print `[<step>] gate: PAUSED (Q=<n> A=<n> B=<n>)` and stop: no `*-complete`, no `*-fix-prepare`, no next prepare. Show the items verbatim grouped by section, with no paraphrase and no severity judgement. Ask via AskUserQuestion:
   - "answer": the operator types free text (answers to QUESTIONS, decisions or corrections for BLOCKERS/ASSUMPTIONS). ALWAYS re-dispatch the same stage (SendMessage to the same agent if available, else a fresh Agent on the same `prompt_path`) with: `Operator answered: <section/item → operator text>. Revise your outputs accordingly and record them under "## Operator decisions" in your own output file. For JSON output (epic reviewers: design, analysis, breakdown): rewrite the ENTIRE strict-JSON report from scratch with the answers applied and mention the operator decision in summary. Then give the final report again.` Re-run this gate on the new report. Never call a `*-fix-prepare` step for operator answers.
   - "accept and continue": offered ONLY when QUESTIONS and BLOCKERS are both clear (ASSUMPTIONS-only pause). The operator accepts the listed assumptions unchanged: NO re-dispatch, proceed to the complete. "answer" = change something and re-dispatch; "accept" = change nothing and proceed.
   - "abort": print `Resume with: /start-epic <EPIC>`.
   QUESTIONS and BLOCKERS can be resolved only by "answer" or "abort".
6. **Clear.** Print `[<step>] gate: clear`, then run the complete. A complete run without a printed gate line is a protocol violation.
7. **No triage.** You never decide an item is non-blocking, minor or ignorable; you never trim, reorder or summarize items away; only the operator can waive one. You never write files to record decisions (the agent records them under `## Operator decisions`). `status.json` stays untouched until `*-complete` succeeds. Operator-accepted assumptions may appear in the one-line stage summary.

## Confirm (after EVERY explicit complete)

Re-run `ai_wrap.py epic-next <EPIC> --json` and require: `state != "failed"`, `current_stage == <the complete step with - as _>`, `last_history == {stage: <that stage>, status: done}` (also when `kind == done`). Mismatch → failed-step handling: show the error, ask "retry complete" / "re-dispatch then complete" / "abort". Never retry via `--run`.

## After done

`done` is reached only after the breakdown review is approved. Show a short story-map summary (`.ai/epics/<EPIC>/breakdown/epic_story_map.md`, titles only). **Ask** before running `python .ai/bin/ai_run.py epic-generate-tickets <EPIC> [--init-dirs]` (it only writes ticket `input.md`/run dirs). If yes, run it, then list `/start-ticket <EPIC>-<US-...>` commands in story-map order. Start no ticket yourself.

## Output style

One short line per stage: `[<stage>] done (<decision if any>)`. Do not dump files into your context.
