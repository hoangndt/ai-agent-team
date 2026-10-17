"""Epic analysis/breakdown review gates, breakdown validation and multi-domain tickets.

Run: python3 -m unittest discover -s tests
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".ai" / "bin"
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True

import ai_run  # noqa: E402
import ai_wrap  # noqa: E402

EPIC = "EPIC-001"
NEW_STEPS = [
    "epic-analysis-review", "epic-analysis-fix", "epic-breakdown-review", "epic-breakdown-fix",
]

# Per-day sizing and single-domain wording that planner text must not contain; the fixture
# proves the phrases are what the absence checks look for, so those cannot pass vacuously.
LEGACY_PLANNER_TEXT = (
    "- Be small enough (1–3 days typical)\n"
    "- [ ] Every ticket estimable within 1–3 days\n"
    "A ticket may only belong to a single domain. Use cross-cutting notes.\n"
)
LEGACY_PHRASES = ["1–3 days", "A ticket may only belong to a single domain"]
SIZING_NUMBER_RES = [
    re.compile(r"\d+\s*(-|–|to)?\s*\d*\s*(working\s+)?days?", re.IGNORECASE),
    re.compile(r"\d+\s+tickets", re.IGNORECASE),
]

CONFIG = {
    "project_name": "Demo",
    "default_domain": "backend",
    "vault": {"enabled": False},
    "domains": {
        "backend": {"paths": ["api/", "shared/"], "skills": {"developer": ["skills/be.md", "skills/common.md"]}},
        "frontend": {"paths": ["web/", "shared/"], "skills": {"developer": ["skills/common.md", "skills/fe.md"]}},
        "data": {"paths": ["etl/"], "skills": {}},
    },
}

TRACKER = """# Epic Story Status

## Status Key

| Symbol | Meaning |
|--------|---------|
| done | Done |

## Stream

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
{rows}

## Progress Summary

- Done: 0 / 1
"""


def quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


def ticket_text(domains="backend", checklist="", verification="1. Open the page.", heading="## Domains"):
    parts = [
        "## Summary\n\nS\n",
        "## Goal\n\nG\n",
        "## Scope\n\nSc\n",
        "## Out of Scope\n\nNone\n",
        "## Acceptance Criteria\n\n- one\n- two\n",
        f"{heading}\n\n{domains}\n",
    ]
    if checklist:
        parts.append(f"## Domain Checklist\n\n{checklist}\n")
    if verification is not None:
        parts.append(f"## Verification\n\n{verification}\n")
    parts += ["## Dependencies\n\n- none\n", "## Notes\n\nn\n", "## References\n\n- [a](a.md)\n"]
    return "\n".join(parts)


TWO_DOMAIN_CHECKLIST = "### backend\n\n- [ ] api\n\n### frontend\n\n- [ ] ui\n"


class EpicProject(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(os.chdir, self.prev)
        shutil.copytree(ROOT / ".ai" / "agents", self.tmp / ".ai" / "agents")
        (self.tmp / ".ai" / "project_config.json").write_text(json.dumps(CONFIG))
        shutil.copy(ROOT / ".ai" / "step_models.json", self.tmp / ".ai" / "step_models.json")
        for name in ("be", "fe", "common"):
            p = self.tmp / "skills" / f"{name}.md"
            p.parent.mkdir(exist_ok=True)
            p.write_text(f"{name} skill")
        quiet(ai_run.epic_init, EPIC, "Build the thing")

    # helpers
    def w(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def status(self):
        return ai_run.load_epic_status(EPIC)

    def set_stage(self, stage, state="ready"):
        s = self.status()
        s["current_stage"], s["state"] = stage, state
        ai_run.save_epic_status(EPIC, s)

    def add_history(self, stage, note=""):
        s = self.status()
        s.setdefault("history", []).append({"stage": stage, "status": "done", "note": note})
        ai_run.save_epic_status(EPIC, s)

    def write_analysis(self):
        self.w(ai_run.epic_analysis_path(EPIC), "analysis")

    def write_design(self):
        self.w(ai_run.epic_design_path(EPIC), "design")

    def write_breakdown(self, tickets=None, rows=None):
        tickets = tickets if tickets is not None else {"EPIC-001-US-001-one.md": ticket_text()}
        self.w(ai_run.epic_story_map_path(EPIC), "story map")
        ids = rows if rows is not None else [
            re.match(r"EPIC-\d+-([A-Z]+-\d+)-", n).group(1) for n in tickets
        ]  # tickets with a non-conforming name need explicit rows
        table = "\n".join(f"| {i} | t | x | - | - |" for i in ids)
        self.w(ai_run.epic_story_status_path(EPIC), TRACKER.format(rows=table))
        for name, text in tickets.items():
            self.w(ai_run.epic_tickets_dir(EPIC) / name, text)

    def write_review(self, phase, decision="approve", issues=None):
        path = {"analysis": ai_run.epic_analysis_review_report_path,
                "breakdown": ai_run.epic_breakdown_review_report_path}[phase](EPIC)
        body = {"decision": decision, "issues": issues or [], "summary": "s"}
        self.w(path, json.dumps(body))
        return path

    def write_design_review(self, decision="approve"):
        self.w(ai_run.epic_review_report_path(EPIC), json.dumps({"decision": decision, "issues": [], "summary": ""}))

    def nxt(self):
        return ai_run.epic_next_action(EPIC)

    def assertFailed(self, exc, fn, *args):
        with self.assertRaises(exc):
            quiet(fn, *args)
        self.assertEqual(self.status()["state"], "failed")


class StructureTests(EpicProject):
    def test_subcommands_and_parser(self):
        for base in NEW_STEPS:
            for kind in ("prepare", "complete"):
                step = f"{base}-{kind}"
                self.assertIn(step, ai_run.KNOWN_SUBCOMMANDS)
                self.assertEqual(ai_run.build_parser().parse_args([step, EPIC]).epic, EPIC)
                self.assertTrue(hasattr(ai_run, step.replace("-", "_")))

    def test_prepare_tables(self):
        for base in NEW_STEPS:
            prep = f"{base}-prepare"
            self.assertIn(prep, ai_run.KNOWN_PREPARE_STEPS)
            self.assertEqual(ai_run._EPIC_PREPARE_TO_COMPLETE[prep], f"{base}-complete")
            self.assertIn(prep, ai_run._EPIC_PREPARE_STEP_PROMPT)

    def test_run_named_epic_step_dispatches_new_steps(self):
        self.assertFailed(FileNotFoundError, ai_run.run_named_epic_step, EPIC, "epic-analysis-review-prepare")

    def test_role_files_structure(self):
        for role, name in (("epic_analysis_reviewer", "analysis"), ("epic_breakdown_reviewer", "breakdown")):
            text = (ROOT / ".ai" / "agents" / f"{role}.md").read_text()
            self.assertTrue(text.splitlines()[0].lower().startswith("you are epic"), role)
            low = text.lower()
            for heading in ("input", "output", "what to produce", "rules", "success criteria"):
                self.assertRegex(low, rf"(?m)^#+\s*{heading}\s*$", f"{role}: {heading}")
            self.assertIn(f".ai/epics/<EPIC>/review/epic_{name}_review.json", text)
            for key in ("decision", "issues", "severity", "area", "message", "summary"):
                self.assertIn(f'"{key}"', text)

    def test_ticket_side_roles_carry_checklist_rule(self):
        for role in ("architect", "developer", "reviewer", "qa"):
            text = (ROOT / ".ai" / "agents" / f"{role}.md").read_text()
            self.assertIn("## Domain Checklist", text, role)
            self.assertIn("## Verification", text, role)
        dev = (ROOT / ".ai" / "agents" / "developer.md").read_text()
        self.assertIn("## Verification Evidence", dev)


class ReviewPrepareTests(EpicProject):
    def test_analysis_prepare_requires_inputs(self):
        self.assertFailed(FileNotFoundError, ai_run.epic_analysis_review_prepare, EPIC)

    def test_analysis_prepare_writes_prompt(self):
        self.write_analysis()
        quiet(ai_run.epic_analysis_review_prepare, EPIC)
        prompt = ai_run.epic_analysis_review_prompt_path(EPIC).read_text()
        reviewer = (ROOT / ".ai" / "agents" / "epic_analysis_reviewer.md").read_text().strip()
        self.assertIn(reviewer, prompt)
        self.assertIn(ai_run.epic_input_file(EPIC).as_posix(), prompt)
        self.assertIn(ai_run.epic_analysis_path(EPIC).as_posix(), prompt)
        self.assertIn('"decision": "approve|request_changes|block"', prompt)
        self.assertIn(ai_run.epic_analysis_review_report_path(EPIC).as_posix(), prompt)
        self.assertEqual(self.status()["current_stage"], "epic_analysis_review_prepare")
        self.assertIn("epic_analysis_review_prompt", self.status()["artifacts"])

    def test_breakdown_prepare_requires_tickets_and_lists_them(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown(tickets={})
        self.assertFailed(FileNotFoundError, ai_run.epic_breakdown_review_prepare, EPIC)
        self.write_breakdown()
        quiet(ai_run.epic_breakdown_review_prepare, EPIC)
        prompt = ai_run.epic_breakdown_review_prompt_path(EPIC).read_text()
        ticket = ai_run.epic_tickets_dir(EPIC) / "EPIC-001-US-001-one.md"
        self.assertIn(ticket.as_posix(), prompt)
        self.assertIn(ai_run.epic_story_status_path(EPIC).as_posix(), prompt)

    def test_followup_block_only_with_previous_review(self):
        self.write_analysis()
        quiet(ai_run.epic_analysis_review_prepare, EPIC)
        self.assertNotIn("This is a follow-up review after a fix round", ai_run.epic_analysis_review_prompt_path(EPIC).read_text())
        self.w(ai_run.previous_epic_analysis_review_path(EPIC), "{}")
        self.w(ai_run.epic_analysis_review_fix_context_path(EPIC), "ctx")
        quiet(ai_run.epic_analysis_review_prepare, EPIC)
        prompt = ai_run.epic_analysis_review_prompt_path(EPIC).read_text()
        self.assertIn("This is a follow-up review after a fix round", prompt)
        self.assertIn(ai_run.previous_epic_analysis_review_path(EPIC).as_posix(), prompt)
        self.assertIn(ai_run.epic_analysis_review_fix_context_path(EPIC).as_posix(), prompt)

    def test_seeded_runs_warn_without_blocking(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        (ai_run.RUNS / f"{EPIC}-EPIC-001-US-001-one").mkdir(parents=True)
        out = quiet(ai_run.epic_breakdown_review_prepare, EPIC)
        self.assertIn("[WARN] 1 ticket run(s) already seeded", out)
        self.assertTrue(ai_run.epic_breakdown_review_prompt_path(EPIC).exists())


class ReviewCompleteTests(EpicProject):
    def test_roundtrip_both_phases(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        for phase in ("analysis", "breakdown"):
            issues = [{"severity": "high", "area": "scope", "message": "m"}]
            self.write_review(phase, "request_changes", issues)
            quiet(getattr(ai_run, f"epic_{phase}_review_complete"), EPIC)
            note = self.status()["history"][-1]["note"]
            self.assertEqual(ai_wrap.DECISION_RE.search(note).group(1), "request_changes")
            ctx = {"analysis": ai_run.epic_analysis_review_fix_context_path,
                   "breakdown": ai_run.epic_breakdown_review_fix_context_path}[phase](EPIC)
            self.assertIn("m", ctx.read_text())
            self.assertIn(f"epic_{phase}_review_report", self.status()["artifacts"])

    def test_invalid_inputs_fail(self):
        report = ai_run.epic_analysis_review_report_path(EPIC)
        self.assertFailed(FileNotFoundError, ai_run.epic_analysis_review_complete, EPIC)
        self.w(report, "not json")
        self.assertFailed(ValueError, ai_run.epic_analysis_review_complete, EPIC)
        self.w(report, json.dumps({"decision": "maybe", "issues": [], "summary": ""}))
        self.assertFailed(ValueError, ai_run.epic_analysis_review_complete, EPIC)
        self.w(ai_run.epic_breakdown_review_report_path(EPIC), json.dumps({"issues": []}))
        self.assertFailed(ValueError, ai_run.epic_breakdown_review_complete, EPIC)


class FixTests(EpicProject):
    def test_fix_prepare_archives_and_deletes(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        for phase, role_marker in (("analysis", "Epic Analyst"), ("breakdown", "Epic Planner")):
            report = self.write_review(phase, "request_changes", [{"severity": "high", "area": "a", "message": "mm"}])
            quiet(getattr(ai_run, f"epic_{phase}_review_complete"), EPIC)
            quiet(getattr(ai_run, f"epic_{phase}_fix_prepare"), EPIC)
            self.assertFalse(report.exists())
            prev = {"analysis": ai_run.previous_epic_analysis_review_path,
                    "breakdown": ai_run.previous_epic_breakdown_review_path}[phase](EPIC)
            self.assertIn("request_changes", prev.read_text())
            fix_prompt = {"analysis": ai_run.epic_analysis_fix_prompt_path,
                          "breakdown": ai_run.epic_breakdown_fix_prompt_path}[phase](EPIC).read_text()
            self.assertIn(role_marker, fix_prompt)
            self.assertIn(prev.as_posix(), fix_prompt)

    def test_fix_prepare_without_review_fails_without_mutation(self):
        self.write_analysis()
        before = dict(self.status()["artifacts"])
        self.assertFailed(FileNotFoundError, ai_run.epic_analysis_fix_prepare, EPIC)
        self.assertEqual(self.status()["artifacts"], before)
        self.assertFailed(FileNotFoundError, ai_run.epic_breakdown_fix_prepare, EPIC)

    def test_breakdown_fix_prompt_mentions_seeded_tickets(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        (ai_run.RUNS / f"{EPIC}-EPIC-001-US-001-one").mkdir(parents=True)
        self.write_review("breakdown", "request_changes")
        out = quiet(ai_run.epic_breakdown_fix_prepare, EPIC)
        self.assertIn("[WARN] 1 ticket run(s) already seeded", out)
        prompt = ai_run.epic_breakdown_fix_prompt_path(EPIC).read_text()
        self.assertIn("QUESTIONS", prompt)
        self.assertIn(f"{EPIC}-EPIC-001-US-001-one", prompt)
        self.assertIn("## Verification", prompt)

    def test_analysis_fix_complete(self):
        self.assertFailed(FileNotFoundError, ai_run.epic_analysis_fix_complete, EPIC)
        self.write_analysis()
        quiet(ai_run.epic_analysis_fix_complete, EPIC)
        self.assertEqual(self.status()["current_stage"], "epic_analysis_fix_complete")

    def test_breakdown_fix_complete_uses_full_validation(self):
        self.write_breakdown()
        quiet(ai_run.epic_breakdown_fix_complete, EPIC)
        for f in ai_run.epic_tickets_dir(EPIC).glob("*.md"):
            f.unlink()
        self.assertFailed(FileNotFoundError, ai_run.epic_breakdown_fix_complete, EPIC)
        self.write_breakdown(tickets={"merged.md": ticket_text()}, rows=["US-001"])
        self.assertFailed(ValueError, ai_run.epic_breakdown_fix_complete, EPIC)
        (ai_run.epic_tickets_dir(EPIC) / "merged.md").unlink()
        self.write_breakdown()
        ai_run.epic_story_status_path(EPIC).write_text("")
        self.assertFailed(FileNotFoundError, ai_run.epic_breakdown_fix_complete, EPIC)


class RoutingTests(EpicProject):
    def test_analysis_gate_order(self):
        self.assertEqual(self.nxt(), "epic-analysis-prepare")
        self.w(ai_run.epic_analysis_prompt_path(EPIC), "p")
        self.assertEqual(self.nxt(), "epic-analysis-complete")
        self.write_analysis()
        self.set_stage("epic_analysis_prepare")
        self.assertEqual(self.nxt(), "epic-analysis-complete")
        self.set_stage("epic_analysis_complete")
        self.assertEqual(self.nxt(), "epic-analysis-review-prepare")
        self.set_stage("epic_analysis_review_prepare")
        self.write_review("analysis", "request_changes")
        self.assertEqual(self.nxt(), "epic-analysis-review-complete")
        self.write_review("analysis", "block")
        self.assertEqual(self.nxt(), "epic-analysis-review-complete")
        self.set_stage("epic_analysis_review_complete")
        self.assertEqual(self.nxt(), "epic-analysis-fix-prepare")
        self.set_stage("epic_analysis_fix_prepare")
        ai_run.epic_analysis_review_report_path(EPIC).unlink()
        self.assertEqual(self.nxt(), "epic-analysis-fix-complete")
        self.set_stage("epic_analysis_fix_complete")
        self.assertEqual(self.nxt(), "epic-analysis-review-prepare")
        self.write_review("analysis", "approve")
        self.set_stage("epic_analysis_review_complete")
        self.assertEqual(self.nxt(), "epic-design-prepare")
        self.write_review("analysis", "weird")
        self.assertEqual(self.nxt(), "epic-analysis-review-prepare")

    def test_epics_past_analysis_are_not_pulled_back(self):
        self.write_analysis()
        self.write_design()
        self.set_stage("epic_design_complete")
        self.assertNotIn("analysis-review", self.nxt())
        self.assertNotIn("analysis-fix", self.nxt())
        ai_run.epic_design_path(EPIC).unlink()
        self.w(ai_run.epic_design_prompt_path(EPIC), "p")
        self.assertEqual(self.nxt(), "epic-design-complete")

    def approve_design(self):
        self.write_analysis()
        self.write_design()
        self.write_design_review("approve")
        self.set_stage("epic_review_complete")

    def test_design_flow_unchanged(self):
        self.write_analysis()
        self.write_design()
        self.set_stage("epic_design_complete")
        self.assertEqual(self.nxt(), "epic-review-prepare")
        self.write_design_review("request_changes")
        self.assertEqual(self.nxt(), "epic-design-fix-prepare")
        self.write_design_review("approve")
        self.set_stage("epic_review_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-prepare")

    def test_breakdown_gate_order(self):
        self.approve_design()
        self.assertEqual(self.nxt(), "epic-breakdown-prepare")
        self.set_stage("epic_breakdown_prepare")
        self.assertEqual(self.nxt(), "epic-breakdown-complete")
        self.write_breakdown()
        self.assertEqual(self.nxt(), "epic-breakdown-complete")
        self.set_stage("epic_breakdown_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-review-prepare")
        self.set_stage("epic_breakdown_review_prepare")
        self.write_review("breakdown", "request_changes")
        self.assertEqual(self.nxt(), "epic-breakdown-review-complete")
        self.set_stage("epic_breakdown_review_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-fix-prepare")
        self.set_stage("epic_breakdown_fix_prepare")
        ai_run.epic_breakdown_review_report_path(EPIC).unlink()
        self.assertEqual(self.nxt(), "epic-breakdown-fix-complete")
        self.set_stage("epic_breakdown_fix_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-review-prepare")
        self.write_review("breakdown", "approve")
        self.set_stage("epic_breakdown_review_complete")
        self.assertEqual(self.nxt(), "done")
        self.write_review("breakdown", "nonsense")
        self.assertEqual(self.nxt(), "epic-breakdown-review-prepare")

    def test_breakdown_edge_routes(self):
        self.approve_design()
        self.set_stage("epic_design_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-prepare")
        self.write_breakdown()
        self.set_stage("epic_breakdown_complete", state="failed")
        self.assertEqual(self.nxt(), "epic-breakdown-complete")
        self.set_stage("epic_breakdown_fix_complete", state="failed")
        self.assertEqual(self.nxt(), "epic-breakdown-fix-complete")
        for f in ai_run.epic_tickets_dir(EPIC).glob("*.md"):
            f.unlink()
        self.set_stage("epic_breakdown_complete")
        self.assertEqual(self.nxt(), "epic-breakdown-complete")

    def test_every_new_prepare_route_has_prompt_entry(self):
        for step in ("epic-analysis-review-prepare", "epic-analysis-fix-prepare",
                     "epic-breakdown-review-prepare", "epic-breakdown-fix-prepare"):
            self.assertTrue(callable(ai_run._EPIC_PREPARE_STEP_PROMPT[step]))


class ParseDomainsTests(unittest.TestCase):
    def test_forms(self):
        parse = ai_run.parse_ticket_domains
        cases = {
            "## Domains\n\nbackend\n": ["backend"],
            "## Domains\n\nbackend, frontend\n": ["backend", "frontend"],
            "## Domains\n\n- backend\n- frontend\n": ["backend", "frontend"],
            "## Domains\n\n`backend`, `frontend`\n": ["backend", "frontend"],
            "## Domains\n\nbackend, backend, data\n": ["backend", "data"],
            "## Domains\r\n\r\nbackend, frontend\r\n": ["backend", "frontend"],
            "## Domain\n\nbackend\n": ["backend"],
            "## Domain Checklist\n\n- [ ] x\n": [],
            "## Domains\n\n## Verification\nx\n": [],
            "no heading": [],
        }
        for text, expected in cases.items():
            self.assertEqual(parse(text), expected, repr(text))


class BreakdownValidationTests(EpicProject):
    def check(self, text, name="EPIC-001-US-001-one.md"):
        self.write_breakdown(tickets={name: text})
        return quiet(ai_run.epic_breakdown_complete, EPIC)

    def assertRejects(self, text, needle):
        with self.assertRaises(ValueError) as cm:
            self.check(text)
        self.assertIn(needle, str(cm.exception))
        self.assertIn("EPIC-001-US-001-one.md", str(cm.exception))
        self.assertEqual(self.status()["state"], "failed")

    def test_accepts_valid_shapes(self):
        self.check(ticket_text())
        self.check(ticket_text("backend, frontend", TWO_DOMAIN_CHECKLIST))
        self.check(ticket_text("backend", heading="## Domain"))
        self.check(ticket_text("backend, backend"))
        self.check(ticket_text("backend, frontend", TWO_DOMAIN_CHECKLIST.replace("### backend", "### Backend")))

    def test_crlf_matches_lf(self):
        self.check(ticket_text("backend, frontend", TWO_DOMAIN_CHECKLIST).replace("\n", "\r\n"))
        with self.assertRaises(ValueError):
            self.check(ticket_text("backend, frontend", "### backend\n\n- [ ] a\n").replace("\n", "\r\n"))

    def test_rejects_domain_problems(self):
        self.assertRejects(ticket_text("mobile"), "mobile")
        self.assertRejects(ticket_text(""), "## Domains")

    def test_rejects_verification_problems(self):
        self.assertRejects(ticket_text(verification=None), "## Verification")
        self.assertRejects(ticket_text(verification=""), "## Verification")

    def test_rejects_checklist_problems(self):
        two = "backend, frontend"
        self.assertRejects(ticket_text(two), "Domain Checklist")
        self.assertRejects(ticket_text(two, "### backend\n\n- [ ] a\n"), "### frontend")
        self.assertRejects(ticket_text(two, "### backend\n\n- [ ] a\n\n### frontend\n\nnothing\n"), "### frontend")
        self.assertRejects(ticket_text(two, "- [ ] a\n- [ ] b\n"), "### backend")
        self.assertRejects(ticket_text(two, "### backend\n\n- [ ] a\n- [ ] b\n\n### frontend\n"), "### frontend")

    def test_checklist_subsections_do_not_end_the_section(self):
        self.check(ticket_text("backend, frontend", "### backend\n- [ ] a\n### frontend\n- [x] b\n"))

    def test_existing_failures_still_fail(self):
        with self.assertRaises(ValueError):
            self.write_breakdown(tickets={"bad-name.md": ticket_text()}, rows=["US-001"])
            quiet(ai_run.epic_breakdown_complete, EPIC)
        for section in ("Goal", "Scope", "References"):
            broken = ticket_text().replace(f"## {section}\n\n", f"## {section}\n\n## Empty{section}\n\n", 1)
            with self.assertRaises(ValueError):
                self.check(broken)

    def test_tracker_consistency(self):
        two = {"EPIC-001-US-001-a.md": ticket_text(), "EPIC-001-US-002-b.md": ticket_text()}
        self.write_breakdown(tickets=two, rows=["US-001", "US-002"])
        quiet(ai_run.epic_breakdown_complete, EPIC)
        self.write_breakdown(tickets=two, rows=["US-001"])
        with self.assertRaises(ValueError) as cm:
            quiet(ai_run.epic_breakdown_complete, EPIC)
        self.assertIn("US-002", str(cm.exception))
        self.write_breakdown(tickets=two, rows=["US-001", "US-002", "US-003"])
        with self.assertRaises(ValueError) as cm:
            quiet(ai_run.epic_breakdown_complete, EPIC)
        self.assertIn("US-003", str(cm.exception))
        dup = {"EPIC-001-US-001-a.md": ticket_text(), "EPIC-001-US-001-b.md": ticket_text()}
        self.write_breakdown(tickets=dup, rows=["US-001"])
        for f in ai_run.epic_tickets_dir(EPIC).glob("EPIC-001-US-002*"):
            f.unlink()
        with self.assertRaises(ValueError) as cm:
            quiet(ai_run.epic_breakdown_complete, EPIC)
        self.assertIn("US-001", str(cm.exception))


class GenerateTicketsTests(EpicProject):
    def gen(self):
        return quiet(ai_run.epic_generate_tickets, EPIC)

    def run_gen_exit(self):
        with self.assertRaises(SystemExit) as cm:
            self.gen()
        return cm.exception.code

    def run_status(self, ticket):
        return json.loads((ai_run.RUNS / ticket / "status.json").read_text())

    def test_multi_and_single_domain_seeding(self):
        self.write_breakdown(tickets={
            "EPIC-001-US-001-multi.md": ticket_text("backend, frontend", TWO_DOMAIN_CHECKLIST),
            "EPIC-001-US-002-single.md": ticket_text("frontend"),
            "EPIC-001-US-003-unknown.md": ticket_text("mobile, data"),
            "EPIC-001-US-004-none.md": ticket_text("mobile"),
        })
        out = self.gen()
        self.assertIn("[WARN] EPIC-001-US-003-unknown: unknown domain 'mobile' dropped", out)
        multi = self.run_status(f"{EPIC}-EPIC-001-US-001-multi")
        self.assertEqual((multi["domain"], multi["domains"]), ("backend", ["backend", "frontend"]))
        single = self.run_status(f"{EPIC}-EPIC-001-US-002-single")
        self.assertEqual(single["domain"], "frontend")
        self.assertNotIn("domains", single)
        self.assertEqual(self.run_status(f"{EPIC}-EPIC-001-US-003-unknown")["domain"], "data")
        self.assertEqual(self.run_status(f"{EPIC}-EPIC-001-US-004-none")["domain"], "backend")

    def test_gate(self):
        self.write_breakdown()
        self.assertIn("[WARN] no breakdown review recorded", self.gen())
        shutil.rmtree(ai_run.RUNS / f"{EPIC}-EPIC-001-US-001-one")
        self.write_review("breakdown", "request_changes")
        self.assertEqual(self.run_gen_exit(), 1)
        self.assertFalse((ai_run.RUNS / f"{EPIC}-EPIC-001-US-001-one").exists())
        self.write_review("breakdown", "approve")
        self.gen()
        self.assertTrue((ai_run.RUNS / f"{EPIC}-EPIC-001-US-001-one").exists())

    def test_mid_fix_blocks(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        self.write_review("breakdown", "request_changes")
        quiet(ai_run.epic_breakdown_fix_prepare, EPIC)
        self.assertEqual(self.run_gen_exit(), 1)
        self.assertEqual(list(ai_run.RUNS.glob(f"{EPIC}-*")), [])

    def test_history_alone_marks_review_started(self):
        self.write_breakdown()
        self.add_history("epic_breakdown_review_prepare")
        self.assertTrue(ai_run.breakdown_review_started(EPIC))
        self.assertEqual(self.run_gen_exit(), 1)

    def test_skip_and_stale(self):
        self.write_breakdown()
        self.write_review("breakdown", "approve")
        self.gen()
        self.assertIn("[SKIP]", self.gen())
        ticket = ai_run.epic_tickets_dir(EPIC) / "EPIC-001-US-001-one.md"
        ticket.write_text(ticket.read_text() + "\nmore\n")
        out = self.gen()
        self.assertIn("[STALE] EPIC-001-US-001-one", out)
        self.assertNotIn("more", ai_run.input_file(f"{EPIC}-EPIC-001-US-001-one").read_text())


class MultiDomainPromptTests(EpicProject):
    def test_single_domain_context_is_pinned(self):
        quiet(ai_run.init_ticket, "T-1", "req")
        self.assertEqual(
            ai_run.build_project_context("T-1"),
            "Project: Demo\nDomain: backend\nBase branch: main\nRelevant paths:\n- api/\n- shared/",
        )
        self.assertEqual(ai_run.get_role_skills("T-1", "developer"),
                         [Path("skills/be.md"), Path("skills/common.md")])
        self.assertNotIn("domains", json.loads(ai_run.status_file("T-1").read_text()))

    def test_multi_domain_context_skills_and_vault(self):
        quiet(ai_run.init_ticket, "T-2", "req", "backend", ["backend", "frontend"])
        ctx = ai_run.build_project_context("T-2")
        self.assertIn("Domain: backend\nDomains: backend, frontend\n", ctx)
        self.assertEqual(ctx.count("- shared/"), 1)
        self.assertIn("- web/", ctx)
        self.assertEqual(
            ai_run.get_role_skills("T-2", "developer"),
            [Path("skills/be.md"), Path("skills/common.md"), Path("skills/fe.md")],
        )
        self.assertEqual(ai_run.get_ticket_domains("T-2"), ["backend", "frontend"])
        prompt = ai_run.build_role_prompt("T-2", "developer", "do it")
        self.assertIn("Domains: backend, frontend", prompt)
        self.assertIn("fe skill", prompt)
        calls = []
        orig = ai_run.build_vault_context
        import ai_runner.prompts as prompts_mod
        prompts_mod.build_vault_context = lambda domains, role: calls.append(list(domains)) or ""
        try:
            ai_run.build_role_prompt("T-2", "developer", "do it")
        finally:
            prompts_mod.build_vault_context = orig
        self.assertEqual(calls, [["backend", "frontend"]])


class PlannerRuleTests(EpicProject):
    def test_legacy_fixture_contains_phrases(self):
        for phrase in LEGACY_PHRASES:
            self.assertIn(phrase, LEGACY_PLANNER_TEXT)

    def texts(self):
        self.write_analysis()
        self.write_design()
        self.write_design_review("approve")
        quiet(ai_run.epic_breakdown_prepare, EPIC)
        return {
            "planner": (ROOT / ".ai" / "agents" / "epic_planner.md").read_text(),
            "prepare": ai_run.epic_breakdown_prompt_path(EPIC).read_text(),
        }

    def test_legacy_wording_removed_and_new_rules_present(self):
        for name, text in self.texts().items():
            for phrase in LEGACY_PHRASES:
                self.assertNotIn(phrase, text, name)
            for needle in ("## Domains", "## Domain Checklist", "## Verification",
                           "one independently verifiable feature/outcome per ticket, spanning all needed domains",
                           "per-domain", "per-layer", "## Quality Notes"):
                self.assertIn(needle.lower(), text.lower(), f"{name}: {needle}")

    def test_no_numeric_sizing(self):
        for name, text in self.texts().items():
            for rx in SIZING_NUMBER_RES:
                self.assertIsNone(rx.search(text), f"{name}: {rx.pattern}")
        for role in ("epic_analysis_reviewer", "epic_breakdown_reviewer"):
            text = (ROOT / ".ai" / "agents" / f"{role}.md").read_text()
            for rx in SIZING_NUMBER_RES:
                self.assertIsNone(rx.search(text), role)


class WrapTests(EpicProject):
    def route(self):
        return ai_wrap.route(EPIC, epic=True)

    def test_new_steps_route_with_models_and_outputs(self):
        self.write_analysis()
        self.set_stage("epic_analysis_complete")
        info = self.route()
        self.assertEqual((info["step"], info["kind"]), ("epic-analysis-review-prepare", "prepare"))
        self.assertEqual(info["next_complete"], "epic-analysis-review-complete")
        self.assertEqual((info["model"], info["effort"]), ("sonnet", "medium"))
        self.set_stage("epic_analysis_review_complete", state="failed")
        info = self.route()
        self.assertEqual((info["step"], info["kind"]), ("epic-analysis-review-complete", "complete"))
        self.assertEqual(info["missing_outputs"], [ai_run.epic_analysis_review_report_path(EPIC).as_posix()])

    def test_breakdown_fix_complete_missing_outputs(self):
        missing = ai_wrap.missing_outputs("epic-breakdown-fix-complete", EPIC, True)
        self.assertIn(ai_run.epic_story_map_path(EPIC).as_posix(), missing)
        self.assertIn(ai_run.epic_story_status_path(EPIC).as_posix(), missing)
        self.assertEqual(len(missing), 3)
        self.assertEqual(
            ai_wrap.missing_outputs("epic-analysis-fix-complete", EPIC, True),
            [ai_run.epic_analysis_path(EPIC).as_posix()],
        )

    def test_fix_rounds_are_independent_and_reset(self):
        def h(stage, note=""):
            return {"stage": stage, "status": "done", "note": note}
        hist = [
            h("epic_review_complete", "Epic reviewer decision: request_changes"),
            h("epic_design_fix_complete"),
            h("epic_analysis_review_complete", "Epic analysis reviewer decision: request_changes"),
            h("epic_analysis_fix_complete"),
            h("epic_analysis_fix_complete"),
            h("epic_breakdown_review_complete", "Epic breakdown reviewer decision: block"),
        ]
        self.assertEqual(ai_wrap.fix_round("epic-design-fix-prepare", hist, True), 1)
        self.assertEqual(ai_wrap.fix_round("epic-analysis-fix-prepare", hist, True), 2)
        self.assertEqual(ai_wrap.fix_round("epic-breakdown-fix-prepare", hist, True), 0)
        hist.append(h("epic_analysis_review_complete", "Epic analysis reviewer decision: approve"))
        self.assertEqual(ai_wrap.fix_round("epic-analysis-fix-prepare", hist, True), 0)


if __name__ == "__main__":
    unittest.main()
