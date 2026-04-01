#!/usr/bin/env python3
"""Demo: JOE/MOE snapshot -> Eurus -> Cherubim-ready context."""
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
        "sigma_plate": 0.12,
        "P_w": 0.55,
        "S_rot": 0.22,
        "W_surface": 1.1e9,
        "W_total": 1.4e9,
        "dW_surface_dt_norm": 0.03,
        "greenhouse_proxy": 0.60,
        "hydrology_stability_proxy": 0.72,
        "biosphere_window_score": 0.78,
        "climate_variance_proxy": 0.18,
        "seasonality_proxy": 0.20,
        "albedo_eff": 0.30,
    }

    state = eurus_state_from_planet_snapshot(snapshot, planet=EARTH, t_s=0.0)
    agent = WeatherAgent(planet=EARTH, lat_rad=math.radians(20.0), day_of_year=180)
    agent.initialize(T_surface_k=state.mean_surface_temp_k, humidity=0.65)
    ctx = cherubim_context_from_eurus(state, agent.health_report(), planet=EARTH)

    print("eurus_state:", round(state.mean_surface_temp_k, 3), state.phase.value, round(state.energy_imbalance_wm2, 3))
    print("cherubim_ctx:", ctx)


if __name__ == "__main__":
    main()
