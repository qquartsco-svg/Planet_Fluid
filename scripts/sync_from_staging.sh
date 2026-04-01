#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_BASE="$(cd "${ROOT}/.." && pwd)"
EURUS_SRC="${UPSTREAM_BASE}/Eurus_Engine/"
OCEANUS_SRC="${UPSTREAM_BASE}/Oceanus_Engine/"
EURUS_DST="${ROOT}/Eurus_Engine/"
OCEANUS_DST="${ROOT}/Oceanus_Engine/"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run"
fi

if [[ ! -d "${EURUS_SRC}" ]]; then
  echo "[FAIL] missing upstream Eurus_Engine: ${EURUS_SRC}" >&2
  exit 1
fi
if [[ ! -d "${OCEANUS_SRC}" ]]; then
  echo "[FAIL] missing upstream Oceanus_Engine: ${OCEANUS_SRC}" >&2
  exit 1
fi

COMMON_EXCLUDES=(
  "--exclude=.git"
  "--exclude=SIGNATURE.sha256"
  "--exclude=BLOCKCHAIN_INFO.md"
  "--exclude=BLOCKCHAIN_INFO_EN.md"
  "--exclude=PHAM_BLOCKCHAIN_LOG.md"
  "--exclude=scripts/regenerate_signature.py"
  "--exclude=scripts/verify_signature.py"
  "--exclude=scripts/release_check.py"
  "--exclude=__pycache__"
  "--exclude=.pytest_cache"
  "--exclude=.mypy_cache"
  "--exclude=.ruff_cache"
  "--exclude=*.pyc"
  "--exclude=.DS_Store"
)

echo "[sync] Eurus_Engine  ${EURUS_SRC} -> ${EURUS_DST}"
rsync -a --delete ${DRY_RUN} "${COMMON_EXCLUDES[@]}" "${EURUS_SRC}" "${EURUS_DST}"

echo "[sync] Oceanus_Engine ${OCEANUS_SRC} -> ${OCEANUS_DST}"
rsync -a --delete ${DRY_RUN} "${COMMON_EXCLUDES[@]}" "${OCEANUS_SRC}" "${OCEANUS_DST}"

if [[ -n "${DRY_RUN}" ]]; then
  echo "[OK] dry-run only (no files changed)"
  exit 0
fi

echo "[sync] Refreshing root signature"
python "${ROOT}/scripts/regenerate_signature.py"
python "${ROOT}/scripts/verify_signature.py"
echo "[OK] sync completed"
