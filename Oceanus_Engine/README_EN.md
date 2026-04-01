> **English.** Korean (정본): [README.md](README.md)

> **Planet_Fluid monorepo:** Umbrella docs: [../README_EN.md](../README_EN.md) · [../README.md](../README.md). Integrity manifest: [../SIGNATURE.sha256](../SIGNATURE.sha256).

# Oceanus_Engine

**Planetary ocean dynamics shared engine** — the ocean counterpart to Eurus (atmosphere). It models **water as a fluid** plus **thermohaline**, **lunisolar tides**, **seafloor geometry**, and **discrete plate/event hooks**, then exposes **contracts** and **Ω-style** summaries for routing and autonomy stacks.

This is **not** a weather app, a full GCM, or the vessel autonomy core; it is the **ocean state field** that those systems can consume.

## Layers

| Layer | Role |
|-------|------|
| **L0** | Frozen dataclass contracts: cells, currents, thermohaline, tides, seafloor, plates, coastal, observations, forecast frames |
| **L1** | 2D shallow water: η, H, u, v, Coriolis, wind stress, numerical diffusion |
| **L2** | Linear equation of state, thermohaline aggregation, overturning proxy |
| **L3** | M2/S2/K1/O1 harmonics + synodic beat phase; tidal source on continuity + weak tidal velocity overlay |
| **L4** | Bathymetry slope / seafloor class; `PlateHookRegistry` for quakes, uplift, volcanic flux |
| **L5** | Route utility, coastal proxies, bilinear sampling for marine bridge |
| **L6** | Ω scalars and `OceanHealthVerdict` |

## Quick start

```python
from oceanus_engine import OceanGridModel
from oceanus_engine.observer.ocean_observer import build_forecast_frame

m = OceanGridModel(24, 24, 10_000.0, 10_000.0, default_bathymetry_m=500.0)
m.set_wind_field(10.0, 3.0)
m.step(60.0)
frame = build_forecast_frame(m.current_field_state(), m.all_cells(), horizon_s=3600.0)
```

## L4 `engine_ref`

- `ocean.current.forecast` and `ocean.route.utility` are contract hooks for the parent `00_BRAIN` workspace `design_workspace` / `l4_runner`. This GitHub clone may not include those folders.

## Integration

- **Eurus**: inject wind via `set_wind_field` (surface stress is derived inside the ocean core).
- **Eurus (`FluidCell` / `WeatherAgent`)**: `oceanus_engine.bridge.eurus_wind_adapter` — `apply_eurus_fluid_wind_to_ocean_grid`, `apply_eurus_weather_agent_wind_to_ocean_grid` (duck-typed; `eurus_engine` not required at import time).
- **Marine_Autonomy_Stack**: `marine_autonomy_bridge.marine_perception_dict_from_ocean` maps EN currents to surge/sway in the vessel frame.
- **Workbench / ATHENA**: map `OceanForecastFrame` to nodes such as `ocean.current.forecast` and `ocean.route.utility`.

## Tests

```bash
cd Oceanus_Engine && python -m pytest tests/ -q
```

## Dependencies

stdlib only; Python **3.10+**.
