"""Tests for the per-step model/effort config. Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".ai" / "bin"
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True

import ai_run  # noqa: E402
from ai_runner import steps, wezterm  # noqa: E402

# Reference model/effort table the shipped config must match.
OLD_DEFAULT = ("sonnet", "high")
OLD_TABLE = {
    "architect-prepare": ("sonnet", "high"),
    "architect-fix-prepare": ("sonnet", "medium"),
    "epic-analysis-prepare": ("opus", "high"),
    "epic-design-prepare": ("opus", "high"),
    "epic-design-fix-prepare": ("sonnet", "high"),
    "architect-review-prepare": ("sonnet", "high"),
    "dev-prepare": ("sonnet", "high"),
    "review-prepare": ("sonnet", "high"),
    "dev-fix-prepare": ("sonnet", "medium"),
    "qa-prepare": ("sonnet", "medium"),
    "distill-prepare": ("sonnet", "medium"),
    "epic-review-prepare": ("sonnet", "medium"),
    "epic-breakdown-prepare": ("sonnet", "high"),
    "adr-distill-prepare": ("sonnet", "medium"),
}


class InTempProject(unittest.TestCase):
    """Runs each test with cwd in a temp project dir (the runner uses relative .ai/ paths)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".ai").mkdir()
        self.prev_cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(os.chdir, self.prev_cwd)
        steps._warned_missing.clear()

    def write_cfg(self, data):
        text = data if isinstance(data, str) else json.dumps(data)
        (self.tmp / ".ai" / "step_models.json").write_text(text)


class ShippedConfigTests(unittest.TestCase):
    def test_live_config_matches_old_table(self):
        data = json.loads((ROOT / ".ai" / "step_models.json").read_text())
        self.assertEqual(tuple(data["default"].values()), OLD_DEFAULT)
        self.assertEqual({k: (v["model"], v["effort"]) for k, v in data["steps"].items()}, OLD_TABLE)

    def test_template_equals_live_config(self):
        live = (ROOT / ".ai" / "step_models.json").read_text()
        tmpl = (ROOT / ".ai" / "templates" / "step_models.template.json").read_text()
        self.assertEqual(json.loads(live), json.loads(tmpl))

    def test_known_steps_match_routing_tables(self):
        routed = set(ai_run._PREPARE_TO_COMPLETE) | set(ai_run._EPIC_PREPARE_TO_COMPLETE)
        self.assertEqual(set(ai_run.KNOWN_PREPARE_STEPS), routed)

    def test_old_names_removed(self):
        self.assertFalse(hasattr(ai_run, "STEP_MODEL"))
        self.assertFalse(hasattr(ai_run, "_DEFAULT_STEP_MODEL"))


class GetStepModelTests(InTempProject):
    def test_every_step_matches_old_table(self):
        shutil.copy(ROOT / ".ai" / "step_models.json", self.tmp / ".ai" / "step_models.json")
        for step, pair in OLD_TABLE.items():
            self.assertEqual(steps.get_step_model(step), pair, step)

    def test_unlisted_step_uses_default(self):
        self.write_cfg({"default": {"model": "haiku", "effort": "low"}, "steps": {}})
        self.assertEqual(steps.get_step_model("dev-prepare"), ("haiku", "low"))
        self.assertEqual(steps.get_step_model("not-a-step"), ("haiku", "low"))

    def test_edit_is_picked_up_without_restart(self):
        self.write_cfg({"default": {"model": "sonnet", "effort": "high"}, "steps": {"dev-prepare": {"model": "opus", "effort": "high"}}})
        self.assertEqual(steps.get_step_model("dev-prepare"), ("opus", "high"))
        self.write_cfg({"default": {"model": "sonnet", "effort": "high"}, "steps": {"dev-prepare": {"model": "haiku", "effort": "low"}}})
        self.assertEqual(steps.get_step_model("dev-prepare"), ("haiku", "low"))

    def test_arbitrary_strings_accepted_and_comment_ignored(self):
        self.write_cfg({"_comment": "x", "default": {"model": "claude-x-1", "effort": "turbo"}})
        self.assertEqual(steps.get_step_model("qa-prepare"), ("claude-x-1", "turbo"))

    def test_missing_file_warns_once_and_falls_back(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(steps.get_step_model("epic-design-prepare"), ("sonnet", "high"))
            self.assertEqual(steps.get_step_model("dev-prepare"), ("sonnet", "high"))
        self.assertEqual(err.getvalue().count("[WARN]"), 1)
        self.assertIn("step_models.json", err.getvalue())


class ValidationTests(InTempProject):
    def assert_rejected(self, data, *fragments):
        self.write_cfg(data)
        with self.assertRaises(steps.StepConfigError) as cm:
            steps.load_step_models()
        msg = str(cm.exception)
        self.assertIn("step_models.json", msg)
        for frag in fragments:
            self.assertIn(frag, msg)

    def test_bad_json(self):
        self.assert_rejected("{not json")

    def test_non_object_root(self):
        self.assert_rejected([1, 2])

    def test_missing_default(self):
        self.assert_rejected({"steps": {}}, "default")

    def test_empty_or_non_string_values(self):
        self.assert_rejected({"default": {"model": "", "effort": "high"}}, "default.model")
        self.assert_rejected({"default": {"model": "sonnet", "effort": 3}}, "default.effort")
        self.assert_rejected({"default": {"model": "sonnet"}}, "default.effort")
        self.assert_rejected({"default": "sonnet"}, "default")
        good = {"model": "sonnet", "effort": "high"}
        self.assert_rejected({"default": good, "steps": {"dev-prepare": {"model": " ", "effort": "high"}}}, "steps.dev-prepare.model")

    def test_unknown_step_key(self):
        good = {"model": "sonnet", "effort": "high"}
        self.assert_rejected({"default": good, "steps": {"dev-prepar": good}}, "dev-prepar")

    def test_steps_must_be_object(self):
        good = {"model": "sonnet", "effort": "high"}
        self.assert_rejected({"default": good, "steps": []}, "steps")

    def test_cli_reports_error_without_traceback(self):
        proj = self.tmp
        shutil.copytree(ROOT / ".ai" / "bin", proj / ".ai" / "bin", ignore=shutil.ignore_patterns("__pycache__"))
        self.write_cfg("{bad")
        r = subprocess.run(
            [sys.executable, "-B", ".ai/bin/ai_wrap.py", "next", "nope", "--json"],
            cwd=proj, capture_output=True, text=True,
        )
        self.assertNotIn("Traceback", r.stderr)
        self.assertNotEqual(r.returncode, 0)


class SpawnTests(InTempProject):
    def spawn(self, engine, step):
        calls = []

        def fake_run(cmd, **kw):
            calls.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, stdout="7\n", stderr="")

        prompt = self.tmp / "p.md"
        prompt.write_text("hello")
        out = io.StringIO()
        with mock.patch.object(wezterm.subprocess, "run", fake_run), \
                mock.patch.object(wezterm.time, "sleep"), contextlib.redirect_stdout(out):
            wezterm.spawn_ai_wezterm(prompt, str(self.tmp), engine=engine, step=step)
        launched = [kw["input"] for cmd, kw in calls if "--no-paste" in cmd]
        return launched[0], out.getvalue()

    def test_claude_flags_follow_config(self):
        self.write_cfg({"default": {"model": "sonnet", "effort": "high"},
                        "steps": {"dev-prepare": {"model": "opus", "effort": "low"}}})
        launched, out = self.spawn("claude", "dev-prepare")
        self.assertTrue(launched.endswith("--model opus --effort low"))
        self.assertIn("[AUTO] Step 'dev-prepare' -> model=opus, effort=low", out)

    def test_codex_adds_no_flags_and_does_not_need_config(self):
        launched, out = self.spawn("codex", "dev-prepare")
        self.assertNotIn("--model", launched)
        self.assertNotIn("[AUTO] Step", out)
        self.assertFalse((self.tmp / ".ai" / "step_models.json").exists())

    def test_preflight_skips_codex_and_fails_for_bad_claude_config(self):
        self.write_cfg("{bad")
        steps.preflight_step_models("codex")
        with self.assertRaises(steps.StepConfigError):
            steps.preflight_step_models("claude")


if __name__ == "__main__":
    unittest.main()
