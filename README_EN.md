> **English.** Korean (정본): [README.md](README.md)

# Planet_Fluid

**Coupled planetary fluid stack** — **Eurus_Engine** (atmosphere) and **Oceanus_Engine** (ocean) in one repository, wired at the surface by wind forcing into the ocean shallow-water core. This is an **L1 integrated stack** for the 00_BRAIN family: lightweight, observation-oriented, and bridge-friendly — **not** a high-fidelity GCM/OGCM pair.

Public GitHub repository: **`Planet_Fluid`** (`qquartsco-svg/Planet_Fluid`).

---

## Engines at a glance

### Eurus_Engine (atmosphere)

- **Scope:** Planetary **shallow-fluid-style atmosphere** dynamics (SWE-class core), Coriolis, vorticity/divergence, **thermodynamics & radiation & CAPE/CIN**, large-scale circulation, pressure systems and fronts, plus **climate regime** and **Ω-style health** — a **weather/climate screening kernel**, not an operations-grade NWP stack.
- **Planet-agnostic:** `PlanetConfig` presets (Earth/Mars/Venus/…) share one structural skeleton; fidelity stays **screening-level**.
- **Bridges:** Duck-typed hooks toward sibling stacks (TerraCore / Lucifer / JOE·MOE / Cherubim); see `Eurus_Engine/docs/` and README.

### Oceanus_Engine (ocean)

- **Scope:** **Surface ocean** on a 2D SWE grid (η, H, u, v, Coriolis, **wind stress**), plus **thermohaline**, **tidal harmonics**, **seafloor / plate hooks**, coastal/route utilities, and **Ω-style ocean health** — organized as **L0–L6** contracts and physics layers.
- **Not vessel autonomy:** it is closer to the **ocean state field** consumed by routing/autonomy stacks than to the vessel brain.
- **Bridges:** `eurus_wind_adapter` (atmosphere → wind), marine autonomy mapping, optional design-workspace nodes; see Oceanus README.

---

## Fluid mechanics: shared skeleton vs differences

| Axis | Shared | Eurus emphasis | Oceanus emphasis |
|------|--------|----------------|------------------|
| **L1 spine** | Rotating frame, **2D SWE-like updates** | Layer thickness, pressure, moisture, radiation, circulation loops | Water column thickness, **wind stress**, lower boundary |
| **Heat** | Simplified / proxy thermodynamics | Dry/moist lapse, OLR, insolation | Linear EOS, **thermohaline** aggregation |
| **Forcing / boundaries** | Coriolis | Fronts, cyclones, jets | **Tides**, bathymetry, plate event hooks |

Planet_Fluid coupling today targets the **wind-stress row**: Eurus supplies **surface (u, v)** that Oceanus ingests through the **same API** as arbitrary wind.

---

## Extensibility and operability

- **Dependencies:** Both engines are **stdlib-only**, `requires-python >= 3.10` (see each `pyproject.toml`).
- **Duck typing:** Oceanus runs without installing Eurus; forcing can be **raw (u, v)** or **FluidCell / WeatherAgent-like** objects.
- **Monorepo ergonomics:** Sibling folders + `sys.path` bootstrap in `examples/run_planet_fluid_demo.py` — easy to vendor, subtree, or mirror into other repos.
- **`planet_fluid/`:** Today exposes **meta such as `__version__`** and reserves a future **unified facade**; a single `python -m planet_fluid...` entrypoint can be added without collapsing the two engine trees.
- **Sync workflow:** Authoritative edits in `_staging` → `scripts/sync_from_staging.sh` → refresh **root** `SIGNATURE.sha256`.

---

## Limits (stay inside the scope)

- **Not GCM/OGCM class:** resolution, physics completeness, DA, and validation are **not** meant to replace operational forecasting.
- **Coupling is MVP:** **one-way wind forcing** only; two-way heat/moisture/salinity feedback is **out of scope** for now.
- **Spatial uniformity in the demo:** the adapter path emphasizes **uniform wind** on the grid; **per-cell spatial wind maps** need an explicit extension (loop, reanalysis ingest, or a dedicated mapper).
- **Safety / certification:** outputs are **screening and design inputs**, not a substitute for certified navigation or regulatory compliance.

---

## Roadmap (candidates)

1. **Spatially varying forcing:** Interpolation / tiling between Eurus cells and Oceanus grids (coupling layer under `planet_fluid` or a dedicated module).
2. **Optional two-way fluxes:** Minimal SST → boundary layer, evap/precip/salt feedback — only if the stack stays explicitly **lightweight**.
3. **Unified “Planet Tick” runner:** One script chaining demo → tests → signature (similar to other 00_BRAIN engine playbooks).
4. **Packaging:** Optional root `pyproject` / documented `pip install -e` layouts for monorepo consumers.
5. **GitHub metadata:** Repo **About** description, topics, and **Releases** are recommended in GitHub settings (outside this tree).

---

## Layout

```
Planet_Fluid/
├── Eurus_Engine/          ← planetary atmosphere kernel
├── Oceanus_Engine/        ← planetary ocean kernel
├── planet_fluid/          ← umbrella package (meta/version export; facade reserved)
├── examples/
│   └── run_planet_fluid_demo.py   ← FluidCell → ocean grid (one tick)
├── scripts/
│   ├── regenerate_signature.py
│   ├── verify_signature.py
│   ├── release_check.py
│   ├── cleanup_generated.py
│   └── sync_from_staging.sh
├── BLOCKCHAIN_INFO.md
├── BLOCKCHAIN_INFO_EN.md
├── SIGNATURE.sha256
├── README.md / README_EN.md
└── VERSION
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

Sync **does not overwrite** `Eurus_Engine/README*.md` or `Oceanus_Engine/README*.md` (Planet_Fluid–specific docs). Pull upstream README edits manually when you want them.

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
