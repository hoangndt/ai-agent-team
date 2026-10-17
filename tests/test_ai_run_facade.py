"""ai_run.py facade and ai_runner package layout. Run: python3 -m unittest discover -s tests"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".ai" / "bin"
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True

import ai_run  # noqa: E402

# Names the single-file runner exposed, saved before the split.
OLD_NAMES = json.loads((Path(__file__).parent / "data" / "ai_run_names.json").read_text())
MODULES = sorted(p.stem for p in (BIN / "ai_runner").glob("*.py") if p.stem != "__init__")


class FacadeTests(unittest.TestCase):
    def test_every_old_name_still_exposed(self):
        missing = [n for n in OLD_NAMES if not hasattr(ai_run, n)]
        self.assertEqual(missing, [])

    def test_private_routing_tables_exposed(self):
        for name in ("_PREPARE_TO_COMPLETE", "_PREPARE_STEP_PROMPT",
                     "_EPIC_PREPARE_TO_COMPLETE", "_EPIC_PREPARE_STEP_PROMPT"):
            self.assertIsInstance(getattr(ai_run, name), dict)

    def test_facade_is_thin_and_holds_no_logic(self):
        text = (BIN / "ai_run.py").read_text()
        self.assertLessEqual(len(text.splitlines()), 300)
        self.assertNotIn("\ndef ", text)
        self.assertNotIn("\nclass ", text)

    def test_modules_stay_small(self):
        for stem in MODULES:
            n = len((BIN / "ai_runner" / f"{stem}.py").read_text().splitlines())
            self.assertLessEqual(n, 1000, stem)

    def test_each_module_imports_in_a_fresh_interpreter(self):
        for stem in MODULES:
            r = subprocess.run([sys.executable, "-B", "-c", f"import ai_runner.{stem}"],
                               cwd=BIN, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{stem}: {r.stderr}")

    def test_each_name_has_one_defining_module(self):
        import ast
        seen = {}
        for stem in MODULES:
            tree = ast.parse((BIN / "ai_runner" / f"{stem}.py").read_text())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    names = [node.name]
                elif isinstance(node, ast.Assign):
                    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                else:
                    continue
                for n in names:
                    self.assertNotIn(n, seen, f"{n} defined in {seen.get(n)} and {stem}")
                    seen[n] = stem

    def test_main_runs_as_script(self):
        r = subprocess.run([sys.executable, "-B", str(BIN / "ai_run.py"), "--help"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage:", r.stdout)


if __name__ == "__main__":
    unittest.main()
