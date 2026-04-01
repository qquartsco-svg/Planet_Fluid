> **English.** Korean (정본): [README.md](README.md)

# Planet_Fluid

**Coupled planetary fluid stack** — **Eurus_Engine** (atmosphere) and **Oceanus_Engine** (ocean) in one repository, wired at the surface by wind forcing into the ocean shallow-water core. This is an **L1 integrated stack** for the 00_BRAIN family: lightweight, observation-oriented, and bridge-friendly — **not** a high-fidelity GCM/OGCM pair.

Public GitHub repository: **`Planet_Fluid`** (`qquartsco-svg/Planet_Fluid`).

---

## Layout

```
Planet_Fluid/
├── Eurus_Engine/          ← planetary atmosphere kernel
├── Oceanus_Engine/        ← planetary ocean kernel
├── planet_fluid/          ← umbrella package (meta/version export; facade reserved)
├── examples/run_planet_fluid_demo.py  ← FluidCell → ocean grid (one tick)
├── scripts/               ← integrity + release_check + upstream sync
├── BLOCKCHAIN_INFO*.md
├── SIGNATURE.sha256
└── README.md / README_EN.md
```

---

## Coupling

| Direction | Mechanism |
|-----------|-----------|
| Eurus → Oceanus | `oceanus_engine.bridge.eurus_wind_adapter` maps `FluidCell` / `WeatherAgent`-like objects to `OceanGridModel.set_wind_field` |
| Ocean-only | call `set_wind_field(u_ms, v_ms)` directly |

`eurus_engine` is **not** a hard dependency of `oceanus_engine` (duck typing). This monorepo places both trees as siblings; the demo prepends their roots to `sys.path`.

Current coupling scope is **one-way MVP (Eurus → Oceanus wind forcing)**.  
Two-way heat/moisture/salinity feedback coupling is future work.

---

## Use cases (screening)

- Observe first-order transfer from atmospheric wind to ocean surface stress
- Coupled atmosphere-ocean concept demos for design/education
- Generate ocean forcing inputs for route/ops decision pipelines
- Pre-scan environment states before Element_Capture_Foundation workflows

---

## Quick start

Requires **Python 3.10+**, stdlib-only engines.

```bash
git clone https://github.com/qquartsco-svg/Planet_Fluid.git
cd Planet_Fluid
python examples/run_planet_fluid_demo.py
```

Per-engine tests:

```bash
cd Eurus_Engine && python -m pytest tests/ -q
cd ../Oceanus_Engine && python -m pytest tests/ -q
```

Full gate (both test suites + manifest verify + cache cleanup):

```bash
python scripts/release_check.py
```

Sync updates from upstream sibling engines in `_staging`:

```bash
bash scripts/sync_from_staging.sh --dry-run  # preview changes
bash scripts/sync_from_staging.sh            # apply sync + refresh root signature
```

---

## Integrity (“blockchain signature”)

Details: [BLOCKCHAIN_INFO_EN.md](BLOCKCHAIN_INFO_EN.md) · Korean: [BLOCKCHAIN_INFO.md](BLOCKCHAIN_INFO.md)

After edits to signed files:

```bash
python scripts/regenerate_signature.py
python scripts/verify_signature.py
```

---

## Per-engine docs

- Atmosphere: [Eurus_Engine/README_EN.md](Eurus_Engine/README_EN.md) · Korean: [Eurus_Engine/README.md](Eurus_Engine/README.md)
- Ocean: [Oceanus_Engine/README_EN.md](Oceanus_Engine/README_EN.md) · Korean: [Oceanus_Engine/README.md](Oceanus_Engine/README.md)

---

*Planet_Fluid v1.0.0 — screening and observation-oriented fluid cores; not a claim of ground-truth planetary state.*
