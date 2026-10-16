"""Tests for the read-only sidecar .ai/bin/ai_wrap.py. Run: python3 -m unittest discover -s tests"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".ai" / "bin"
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True

import ai_wrap  # noqa: E402


def h(stage, status="done", note=""):
    return {"stage": stage, "status": status, "note": note}


class FixRoundTests(unittest.TestCase):
    def test_architect_reset_on_approve_and_real_notes(self):
        hist = [
            h("architect_review_complete", note="Architect reviewer decision: request_changes — fix loop required"),
            h("architect_fix_complete"),
            h("architect_review_complete", note="Architect reviewer decision: request_changes — fix loop required"),
        ]
        self.assertEqual(ai_wrap.fix_round("architect-fix-prepare", hist, False), 1)
        hist += [h("architect_fix_complete")]
        self.assertEqual(ai_wrap.fix_round("architect-fix-prepare", hist, False), 2)
        hist += [h("architect_review_complete", note="Architect reviewer decision: approve")]
        self.assertEqual(ai_wrap.fix_round("architect-fix-prepare", hist, False), 0)

    def test_epic_gate(self):
        hist = [
            h("epic_review_complete", note="Epic reviewer decision: block"),
            h("epic_design_fix_complete"),
        ]
        self.assertEqual(ai_wrap.fix_round("epic-design-fix-prepare", hist, True), 1)
        hist.append(h("epic_review_complete", note="Epic reviewer decision: approve"))
        self.assertEqual(ai_wrap.fix_round("epic-design-fix-prepare", hist, True), 0)

    def test_qa_not_reset_by_review_approve(self):
        hist = [
            h("review_complete", note="Reviewer decision: approve"),
            h("qa_complete", note="QA decision: fail"),
            h("dev_fix_complete"),
            h("review_complete", note="Reviewer decision: approve"),
            h("qa_complete", note="QA decision: fail"),
            h("dev_fix_complete"),
            h("review_complete", note="Reviewer decision: approve"),
            h("qa_complete", note="QA decision: fail"),
        ]
        self.assertEqual(ai_wrap.fix_round("dev-fix-prepare", hist, False), 2)

    def test_qa_reset_on_pass(self):
        hist = [
            h("qa_complete", note="QA decision: fail"),
            h("dev_fix_complete"),
            h("qa_complete", note="QA decision: pass"),
        ]
        self.assertEqual(ai_wrap.fix_round("dev-fix-complete", hist, False), 0)

    def test_review_rounds_only(self):
        hist = [
            h("review_complete", note="Reviewer decision: request_changes"),
            h("dev_fix_complete"),
            h("review_complete", note="Reviewer decision: block"),
            h("dev_fix_complete"),
            h("review_complete", note="Reviewer decision: request_changes"),
        ]
        self.assertEqual(ai_wrap.fix_round("dev-fix-prepare", hist, False), 2)

    def test_failed_entries_ignored_and_unknown_decision_not_approve(self):
        hist = [
            h("review_complete", note="Reviewer decision: request_changes"),
            h("dev_fix_complete", status="failed"),
            h("dev_fix_complete"),
            h("review_complete", status="failed", note="Reviewer decision: approve"),
            h("review_complete", note="Reviewer decision: weird"),
        ]
        self.assertEqual(ai_wrap.fix_round("dev-fix-prepare", hist, False), 1)

    def test_null_off_fix_steps(self):
        self.assertIsNone(ai_wrap.fix_round("dev-prepare", [], False))

    def test_rederivation_stable(self):
        hist = [h("qa_complete", note="QA decision: fail"), h("dev_fix_complete")]
        self.assertEqual(
            ai_wrap.fix_round("dev-fix-prepare", hist, False),
            ai_wrap.fix_round("dev-fix-prepare", list(hist), False),
        )


class ValidateIdTests(unittest.TestCase):
    def test_validate(self):
        for bad in ["../x", "a/b", "", "x" * 81, ".a", "-a", "a..b"]:
            self.assertFalse(ai_wrap.validate_id(bad), bad)
        self.assertTrue(ai_wrap.validate_id("US-008-foo.bar_1"))
        self.assertTrue(ai_wrap.validate_id("x" * 80))


class RunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        ai = cls.tmp / ".ai"
        ai.mkdir()
        for d in ("agents", "templates", "skills", "bin"):
            shutil.copytree(ROOT / ".ai" / d, ai / d, ignore=shutil.ignore_patterns("__pycache__"))
        cfg = json.loads((ROOT / ".ai" / "project_config.json").read_text())
        cfg["vault"]["enabled"] = False
        (ai / "project_config.json").write_text(json.dumps(cfg))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_py(self, script, *args):
        return subprocess.run(
            [sys.executable, "-B", f".ai/bin/{script}", *args],
            cwd=self.tmp, capture_output=True, text=True,
        )

    def nxt(self, t, epic=False):
        r = self.run_py("ai_wrap.py", "epic-next" if epic else "next", t, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def status_hash(self, t):
        return hashlib.sha256((self.tmp / ".ai/runs" / t / "status.json").read_bytes()).hexdigest()

    def test_unknown_ticket(self):
        r = self.run_py("ai_wrap.py", "next", "nope", "--json")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertTrue(r.stderr)

    def test_prepare_complete_flow_and_readonly(self):
        t = "T-1"
        self.assertEqual(self.run_py("ai_run.py", "init", t, "req").returncode, 0)
        before = self.status_hash(t)
        j = self.nxt(t)
        self.assertEqual(self.status_hash(t), before)
        self.assertEqual(
            set(j),
            {"ticket", "step", "kind", "prompt_path", "model", "effort", "next_complete", "fix_round",
             "missing_outputs", "state", "current_stage", "last_history"},
        )
        self.assertEqual((j["kind"], j["step"]), ("prepare", "architect-prepare"))
        self.assertEqual(j["next_complete"], "architect-complete")
        self.assertEqual(j["prompt_path"], f".ai/runs/{t}/architect/architect_prompt.md")
        self.assertEqual(self.run_py("ai_run.py", "next", t).stdout.strip(), j["step"])

        self.assertEqual(self.run_py("ai_run.py", "architect-prepare", t).returncode, 0)
        j = self.nxt(t)
        # architect outputs absent -> runner routes back to architect-complete
        self.assertEqual(j["step"], self.run_py("ai_run.py", "next", t).stdout.strip())

    def test_complete_missing_outputs_and_failed_override(self):
        t = "T-2"
        self.run_py("ai_run.py", "init", t, "req")
        self.run_py("ai_run.py", "architect-prepare", t)
        r = self.run_py("ai_run.py", "architect-complete", t)
        self.assertNotEqual(r.returncode, 0)
        j = self.nxt(t)
        self.assertEqual((j["kind"], j["step"]), ("complete", "architect-complete"))
        self.assertEqual(j["last_history"], {"stage": "architect_complete", "status": "failed"})
        self.assertEqual(len(j["missing_outputs"]), 4)
        self.assertIsNotNone(j["prompt_path"])
        for name in ("task_spec", "design_note", "acceptance_criteria", "assumptions"):
            (self.tmp / f".ai/runs/{t}/architect/{name}.md").write_text("x")
        j = self.nxt(t)
        self.assertEqual(j["missing_outputs"], [])
        self.assertEqual(self.run_py("ai_run.py", "architect-complete", t).returncode, 0)
        j = self.nxt(t)
        self.assertEqual(j["last_history"], {"stage": "architect_complete", "status": "done"})

    def test_prepare_done_then_complete_has_prompt(self):
        t = "T-3"
        self.run_py("ai_run.py", "init", t, "req")
        for name in ("task_spec", "design_note", "acceptance_criteria", "assumptions"):
            (self.tmp / f".ai/runs/{t}/architect/{name}.md").write_text("x")
        self.run_py("ai_run.py", "architect-complete", t)
        self.run_py("ai_run.py", "architect-review-prepare", t)
        j = self.nxt(t)
        self.assertEqual((j["kind"], j["step"]), ("complete", "architect-review-complete"))
        self.assertEqual(j["last_history"], {"stage": "architect_review_prepare", "status": "done"})
        self.assertEqual(j["prompt_path"], f".ai/runs/{t}/architect/architect_review_prompt.md")
        self.assertEqual(j["missing_outputs"], [f".ai/runs/{t}/architect/architect_review.json"])

    def test_failed_prepare_override(self):
        t = "T-4"
        self.run_py("ai_run.py", "init", t, "req")
        r = self.run_py("ai_run.py", "dev-fix-prepare", t)  # no review/qa report -> fails
        self.assertNotEqual(r.returncode, 0)
        j = self.nxt(t)
        self.assertEqual((j["kind"], j["step"]), ("prepare", "dev-fix-prepare"))
        self.assertIsNone(j["prompt_path"])
        self.assertEqual(j["next_complete"], "dev-fix-complete")
        self.assertEqual(j["fix_round"], 0)

    def test_epic_schema_and_done_fields(self):
        e = "E-1"
        self.assertEqual(self.run_py("ai_run.py", "epic-init", e, "req").returncode, 0)
        j = self.nxt(e, epic=True)
        self.assertIn("epic", j)
        self.assertNotIn("ticket", j)
        self.assertEqual((j["kind"], j["step"], j["model"], j["effort"]), ("prepare", "epic-analysis-prepare", "opus", "high"))

    def test_runner_unchanged_by_import(self):
        # ai_wrap must not write bytecode next to the runner
        self.assertEqual(list(BIN.glob("__pycache__/ai_wrap*")), [])


if __name__ == "__main__":
    unittest.main()
