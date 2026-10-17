"""Per-step model and effort settings read from `.ai/step_models.json`."""
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

from .constants import BASE, ENGINE_REGISTRY, KNOWN_PREPARE_STEPS

# Used only when step_models.json is absent, so a project that has not been
# (re)installed still runs.
FALLBACK_MODEL_EFFORT = ("sonnet", "high")

_warned_missing = set()


class StepConfigError(Exception):
    """step_models.json is unreadable or violates its schema."""


def step_models_path() -> Path:
    return BASE / "step_models.json"


def _parse_pair(raw: object, where: str, path: Path) -> Tuple[str, str]:
    if not isinstance(raw, dict):
        raise StepConfigError(f"{path}: '{where}' must be an object with 'model' and 'effort'")
    pair = []
    for key in ("model", "effort"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise StepConfigError(f"{path}: '{where}.{key}' must be a non-empty string")
        pair.append(value.strip())
    return pair[0], pair[1]


def load_step_models() -> Tuple[Tuple[str, str], Dict[str, Tuple[str, str]]]:
    """Return (default, per-step table). Raises StepConfigError on a bad file."""
    path = step_models_path()
    if not path.is_file():
        key = str(path)
        if key not in _warned_missing:
            _warned_missing.add(key)
            print(
                f"[WARN] {path} not found; using built-in model={FALLBACK_MODEL_EFFORT[0]}, "
                f"effort={FALLBACK_MODEL_EFFORT[1]} for every step. Re-run install.py to create it.",
                file=sys.stderr,
            )
        return FALLBACK_MODEL_EFFORT, {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StepConfigError(f"{path}: cannot read as JSON: {exc}")
    if not isinstance(data, dict):
        raise StepConfigError(f"{path}: top level must be a JSON object")
    if "default" not in data:
        raise StepConfigError(f"{path}: missing 'default'")
    default = _parse_pair(data["default"], "default", path)
    steps_raw = data.get("steps", {})
    if not isinstance(steps_raw, dict):
        raise StepConfigError(f"{path}: 'steps' must be an object")
    steps = {}
    for name, raw in steps_raw.items():
        if name not in KNOWN_PREPARE_STEPS:
            raise StepConfigError(
                f"{path}: unknown step '{name}' in 'steps' "
                f"(valid: {', '.join(sorted(KNOWN_PREPARE_STEPS))})"
            )
        steps[name] = _parse_pair(raw, f"steps.{name}", path)
    return default, steps


def get_step_model(step: str) -> Tuple[str, str]:
    """(model, effort) for a *-prepare step; the configured default when unlisted."""
    default, steps = load_step_models()
    return steps.get(step, default)


def preflight_step_models(engine: str) -> None:
    """Fail on a bad step_models.json before a prepare step mutates run state."""
    if ENGINE_REGISTRY.get(engine, {}).get("supports_model_effort"):
        load_step_models()
