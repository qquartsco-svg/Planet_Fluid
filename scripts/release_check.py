"""Run Eurus + Oceanus tests, then verify the integrity manifest."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_step(label: str, cmd: list[str], cwd: Path) -> int:
    print(f"\n[{label}] {' '.join(cmd)}  (cwd={cwd.name})")
    completed = subprocess.run(cmd, cwd=cwd)
    if completed.returncode != 0:
        print(f"\n[FAIL] {label}")
        return completed.returncode
    return 0


def main() -> int:
    steps = [
        ("pytest_eurus", [sys.executable, "-m", "pytest", "tests", "-q", "--tb=short"], ROOT / "Eurus_Engine"),
        ("pytest_oceanus", [sys.executable, "-m", "pytest", "tests", "-q", "--tb=short"], ROOT / "Oceanus_Engine"),
        ("verify_signature", [sys.executable, str(ROOT / "scripts" / "verify_signature.py")], ROOT),
        ("cleanup_generated", [sys.executable, str(ROOT / "scripts" / "cleanup_generated.py")], ROOT),
    ]
    for label, command, cwd in steps:
        code = run_step(label, command, cwd)
        if code != 0:
            return code
    print("\n[OK] release_check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
