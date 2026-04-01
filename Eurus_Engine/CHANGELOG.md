# Changelog

## 0.1.4 — 2026-03-29

- Added `climate/regime.py` to classify atmospheric climate basins above weather-health level.
- Added `ClimateRegimeType` / `ClimateRegimeReport` contracts.
- Exposed `eurus_regime` and `climate_regime_score` through Cherubim bridge and `WeatherAgent.summary()`.
- Added regression coverage for temperate and hot-greenhouse regime classification.
- Release state now verifies cleanly with 113 passing tests.

## 0.1.3 — 2026-03-29

- Added explicit Eurus→Cherubim field-mapping documentation.
- Added end-to-end `JOE/MOE snapshot -> Eurus -> Cherubim` chain demo and regression coverage.
- Synced package metadata and README to `0.1.3`.
- Release state now verifies cleanly with 110 passing tests.

## 0.1.2 — 2026-03-29

- Added `joe_moe_bridge.py` to absorb shared JOE/MOE planet snapshots into Eurus atmospheric state.
- Added `cherubim_bridge.py` to export Eurus-derived climate / habitability proxies without hard package coupling.
- Added bridge tests and planetary bridge documentation.

## 0.1.1 — 2026-03-29

- Added release-integrity tooling: `regenerate_signature.py`, `verify_signature.py`, `release_check.py`, `cleanup_generated.py`.
- Added `BLOCKCHAIN_INFO.md` and `PHAM_BLOCKCHAIN_LOG.md`.
- Synced package metadata, README, and runtime version to `0.1.1`.

## 0.1.0 — 2026-03-29

- Initial `Eurus_Engine`: shallow-water fluid dynamics, thermodynamics, circulation, pressure systems, fronts, weather health observer, and agent FSM.
- 107 tests passing.
