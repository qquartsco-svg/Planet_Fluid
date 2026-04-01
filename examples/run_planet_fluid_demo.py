"""
Planet_Fluid — Eurus (atmosphere) → Oceanus (ocean) coupling tick.

Maps a Eurus :class:`FluidCell` surface wind into Oceanus via
``apply_eurus_fluid_wind_to_ocean_grid``, then advances the shallow-water grid.
All numbers are screening-level estimates, not mission truth.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Eurus_Engine"))
sys.path.insert(0, str(ROOT / "Oceanus_Engine"))

from eurus_engine.contracts.schemas import FluidCell
from oceanus_engine import OceanGridModel
from oceanus_engine.bridge.eurus_wind_adapter import apply_eurus_fluid_wind_to_ocean_grid


def main() -> None:
    print("Planet_Fluid — Eurus → Oceanus wind coupling (one tick)\n")

    fluid = FluidCell(
        λ_rad=0.0,
        φ_rad=math.radians(15.0),
        u_ms=12.0,
        v_ms=4.5,
        h_m=8_500.0,
        p_pa=101_325.0,
        T_k=300.0,
        q=0.018,
    )
    print(f"  Eurus FluidCell: u={fluid.u_ms} m/s, v={fluid.v_ms} m/s, |v|={fluid.speed_ms:.2f} m/s")

    grid = OceanGridModel(16, 16, 5_000.0, 5_000.0, default_bathymetry_m=400.0)
    apply_eurus_fluid_wind_to_ocean_grid(grid, fluid)
    grid.step(120.0)

    cfs = grid.current_field_state()
    print(f"  Oceanus: wind_stress_east={cfs.wind_stress_east_nm2:.6f} N/m², "
          f"wind_stress_north={cfs.wind_stress_north_nm2:.6f} N/m²")
    print("\n  Done — extend with WeatherAgent or full Eurus grid in your stack.")


if __name__ == "__main__":
    main()
