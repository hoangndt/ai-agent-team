"""install.py scaffolding of .ai/step_models.json. Run: python3 -m unittest discover -s tests"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.py"


def run(*args):
    return subprocess.run([sys.executable, "-B", str(INSTALL), *args], capture_output=True, text=True, input="n\n")


class StepModelsInstallTests(unittest.TestCase):
    def test_fresh_install_scaffolds_and_second_install_preserves_edits(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / ".ai" / "step_models.json"
            r = run("--target", d, "--yes")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(cfg.read_text(), (ROOT / ".ai/templates/step_models.template.json").read_text())
            self.assertTrue((Path(d) / ".ai/bin/ai_runner/steps.py").is_file())
            cfg.write_text('{"default": {"model": "x", "effort": "y"}}')
            r = run("--target", d, "--yes")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(any("[SKIP]" in l and "step_models.json" in l for l in r.stdout.splitlines()))
            self.assertEqual(cfg.read_text(), '{"default": {"model": "x", "effort": "y"}}')

    def test_force_project_files_overwrites_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / ".ai" / "step_models.json"
            run("--target", d, "--yes")
            cfg.write_text("edited")
            r = run("--target", d, "--yes", "--force-project-files", "--backup")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(cfg.read_text(), (ROOT / ".ai/templates/step_models.template.json").read_text())
            backups = [p for p in Path(d).rglob("step_models.json") if p.read_text() == "edited"]
            self.assertEqual(len(backups), 1)

    def test_dry_run_writes_nothing_and_lists_action(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("--target", d, "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(list(Path(d).iterdir()), [])
            self.assertIn(".ai/step_models.json", r.stdout)


if __name__ == "__main__":
    unittest.main()
