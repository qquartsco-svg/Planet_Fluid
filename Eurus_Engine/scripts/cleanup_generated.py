#!/usr/bin/env python3
"""Remove generated cache artifacts from the repository tree."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    removed = 0
    for pattern in (".pytest_cache", "__pycache__", ".DS_Store"):
        for path in ROOT.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                removed += 1
            elif path.exists():
                path.unlink()
                removed += 1
    print(f"cleaned generated cache artifacts ({removed})")


if __name__ == "__main__":
    main()
