> **English.** Korean (정본): [README.md](README.md)

> **Planet_Fluid monorepo:** Coupled atmosphere–ocean overview: [../README_EN.md](../README_EN.md) · [../README.md](../README.md).

# Eurus_Engine

![version](https://img.shields.io/badge/version-0.1.4-blue)
![python](https://img.shields.io/badge/python-≥3.10-green)
![stdlib](https://img.shields.io/badge/deps-stdlib_only-brightgreen)
![tests](https://img.shields.io/badge/tests-113_passed-success)

**Planetary atmosphere weather-dynamics engine** — shallow-water fluid dynamics, thermodynamics, large-scale circulation, and radiative energy balance in one stdlib-only package. **Planet-agnostic** presets (Earth, Mars, Venus, etc.).

---

## Highlights

| Area | What you get |
|------|----------------|
| **Fluids** | SWE, Coriolis, geostrophic wind, vorticity/divergence, CFL-style stability hooks |
| **Thermo** | Magnus vapor pressure, dry/moist lapse, CAPE/CIN, θ / θe |
| **Radiation** | Stefan–Boltzmann OLR, solar insolation, simple balance / equilibrium temperature |
| **Circulation** | Hadley / Ferrel / Polar cells, jets, ITCZ, Walker (El Niño-style) |
| **Pressure & fronts** | Rankine vortex winds, Gaussian pressure, β-drift; cold/warm/occluded/stationary fronts |
| **Health** | Multi-layer Ω-style weather observer |
| **Climate regime** | temperate / greenhouse / thin-atmosphere style classification |
| **FSM** | CALM → DEVELOPING → ACTIVE → SEVERE → DISSIPATING → EQUILIBRIUM |
| **Bridges** | TerraCore / Lucifer / JOE·MOE snapshots / Cherubim habitability proxy (duck-typed) |

---

## Module map (short)

```
eurus_engine/
├── contracts/schemas.py   — PlanetConfig, FluidCell, WeatherAgent, fronts, pressure systems …
├── physics/               — fluid_dynamics, thermodynamics, vertical_profile
├── circulation/         — Hadley, pressure_system, fronts
├── climate/regime.py
├── health/weather_health.py
├── agent/weather_agent.py
└── bridges/               — terracore, lucifer, joe_moe, cherubim
```

Full tree and Korean narrative: [README.md](README.md).

---

## Tests

```bash
cd Eurus_Engine && python -m pytest tests/ -q
```

## Integrity (Planet_Fluid monorepo)

Manifest and docs live at the **repository root**:

- [../SIGNATURE.sha256](../SIGNATURE.sha256)
- [../BLOCKCHAIN_INFO_EN.md](../BLOCKCHAIN_INFO_EN.md) · Korean: [../BLOCKCHAIN_INFO.md](../BLOCKCHAIN_INFO.md)

```bash
cd ..   # repo root
python scripts/verify_signature.py
python scripts/release_check.py
```

---

*Eurus — trace where the planetary atmosphere flows.*
