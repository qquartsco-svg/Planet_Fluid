#!/usr/bin/env python3
"""Verify files against SIGNATURE.sha256."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SIGNATURE.sha256"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        print("SIGNATURE.sha256: missing", file=sys.stderr)
        return 1
    ok = True
    passed = 0
    failed = 0
    missing = 0
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            continue
        digest, relpath = parts
        target = ROOT / relpath
        if not target.exists():
            print(f"MISSING {relpath}", file=sys.stderr)
            ok = False
            missing += 1
            continue
        if sha256_of(target) != digest:
            print(f"MISMATCH {relpath}", file=sys.stderr)
            ok = False
            failed += 1
            continue
        passed += 1
    if ok:
        print(f"[OK]  VERIFIED  passed={passed}  failed={failed}  missing={missing}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
