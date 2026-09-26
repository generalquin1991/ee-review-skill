#!/usr/bin/env python3
"""Run the Codex skill validator with an explicit dependency preflight."""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def has_pyyaml():
    """Return whether the active Python interpreter can import PyYAML."""
    return importlib.util.find_spec("yaml") is not None


def find_validator(explicit_path=None):
    """Find quick_validate.py in the active Codex installation."""
    if explicit_path:
        path = Path(explicit_path).expanduser()
        return path if path.is_file() else None

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    candidates = [
        codex_home / "skills/.system/skill-creator/scripts/quick_validate.py",
        Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py",
    ]
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def main(argv=None):
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Validate this Codex skill after checking validator dependencies."
    )
    parser.add_argument(
        "skill_dir",
        nargs="?",
        default=str(skill_root),
        help="Skill directory to validate (default: this skill)",
    )
    parser.add_argument(
        "--validator",
        help="Explicit path to quick_validate.py (useful in custom Codex installs)",
    )
    args = parser.parse_args(argv)

    if not has_pyyaml():
        print("[ERROR] PyYAML is required by quick_validate.py but is not installed.", file=sys.stderr)
        print("Install it with: python3 -m pip install PyYAML", file=sys.stderr)
        print("Or from this skill: python3 -m pip install -r requirements-validation.txt", file=sys.stderr)
        print("Then rerun: python3 scripts/validate_skill.py", file=sys.stderr)
        return 2

    validator = find_validator(args.validator)
    if validator is None:
        print("[ERROR] Codex quick_validate.py was not found.", file=sys.stderr)
        print("Pass its location with --validator /path/to/quick_validate.py.", file=sys.stderr)
        return 2

    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"[ERROR] Skill directory not found: {skill_dir}", file=sys.stderr)
        return 2

    return subprocess.run(
        [sys.executable, str(validator), str(skill_dir)],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
