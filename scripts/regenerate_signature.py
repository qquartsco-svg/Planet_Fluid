#!/usr/bin/env python3
"""Regenerate SIGNATURE.sha256 for the Planet_Fluid repository root."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIR_NAMES = frozenset({
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "dist",
    "build",
})
SKIP_SUFFIXES = (".pyc",)
SKIP_TOP_FILES = frozenset({"SIGNATURE.sha256"})


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        if rel.name in SKIP_TOP_FILES and len(rel.parts) == 1:
            continue
        files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    lines: list[str] = []
    for path in iter_files():
        rel = path.relative_to(ROOT)
        lines.append(f"{sha256_of(path)}  {rel.as_posix()}\n")
    manifest = ROOT / "SIGNATURE.sha256"
    manifest.write_text("".join(lines), encoding="utf-8")
    print(f"[OK]  {len(lines)} files signed -> SIGNATURE.sha256")


if __name__ == "__main__":
    main()
