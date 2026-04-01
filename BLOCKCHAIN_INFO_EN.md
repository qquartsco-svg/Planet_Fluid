> **English.** Korean (정본): [BLOCKCHAIN_INFO.md](BLOCKCHAIN_INFO.md)

# BLOCKCHAIN_INFO — Planet_Fluid integrity manifest

## Overview

**Blockchain signature** here means a **SHA-256 file manifest** in `SIGNATURE.sha256`, not a consensus network or smart contracts. It supports quick tamper checks for the signed source and documentation surface at clone or release time.

## Scope

The signer walks the repository from the root (see `scripts/regenerate_signature.py`), excluding VCS metadata, caches, virtualenvs, build artifacts, and the manifest file itself.

Both `Eurus_Engine/` and `Oceanus_Engine/` trees are covered by **one** manifest.

## Verification

```bash
python scripts/regenerate_signature.py
python scripts/verify_signature.py
# or: shasum -a 256 -c SIGNATURE.sha256
python scripts/release_check.py
```

## Trust model

The manifest is a **checksum-backed audit surface**. It does not replace cryptographic code signing or an on-chain ledger.
