#!/usr/bin/env python3
"""Demo: shared planet snapshot -> Eurus -> Cherubim-ready context."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eurus_engine import (  # noqa: E402
    EARTH,
    WeatherAgent,
    cherubim_context_from_eurus,
    eurus_state_from_planet_snapshot,
)


def main() -> None:
    snapshot = {
        "sigma_plate": 0.10,
        "P_w": 0.52,
        "S_rot": 0.22,
        "W_surface": 1.0e9,
        "W_total": 1.4e9,
        "dW_surface_dt_norm": 0.02,
        "greenhouse_proxy": 0.62,
        "hydrology_stability_proxy": 0.70,
        "biosphere_window_score": 0.76,
        "climate_variance_proxy": 0.18,
        "seasonality_proxy": 0.20,
        "albedo_eff": 0.29,
    }

    state = eurus_state_from_planet_snapshot(snapshot, planet=EARTH)
    agent = WeatherAgent(planet=EARTH, lat_rad=math.radians(15.0), day_of_year=180)
    agent.initialize(T_surface_k=state.mean_surface_temp_k, humidity=0.65)
    report = agent.health_report()
    ctx = cherubim_context_from_eurus(state, report, planet=EARTH)

    print("snapshot_keys:", sorted(snapshot.keys()))
    print("eurus:", round(state.mean_surface_temp_k, 3), state.phase.value, round(state.energy_imbalance_wm2, 3))
    print("cherubim:", ctx["eden_climate_score"], ctx["temperature_window_proxy"], ctx["eurus_verdict"])


if __name__ == "__main__":
    main()
