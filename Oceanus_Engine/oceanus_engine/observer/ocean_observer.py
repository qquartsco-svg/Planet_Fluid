"""L6 — Ω 스칼라 및 종합 verdict."""
from __future__ import annotations

import math
from typing import Iterable, List, Tuple

from oceanus_engine.contracts.schemas import (
    OceanCellState,
    OceanForecastFrame,
    OceanHealthVerdict,
    CurrentFieldState,
    SeafloorClass,
)
from oceanus_engine.physics.thermohaline import aggregate_thermohaline
from oceanus_engine.physics.tides import tide_state_for_cell
from oceanus_engine.physics.seafloor import seafloor_state_from_bathymetry_grid
from oceanus_engine.contracts.schemas import EARTH_OCEAN


def omega_metrics_from_grid(
    cells: Iterable[OceanCellState],
    nx: int,
    ny: int,
    dx_m: float,
    dy_m: float,
    t_s: float,
) -> Tuple[float, float, float, float, float]:
    """
    Ω_current_stability, Ω_thermohaline, Ω_tidal_predictability,
    Ω_seafloor_risk, Ω_route_utility
    모두 [0,1] 근처 (높을수록 양호).
    """
    grid: List[OceanCellState] = list(cells)
    if not grid:
        return 1.0, 1.0, 1.0, 1.0, 1.0

    speeds = [c.speed_ms for c in grid]
    mean_s = sum(speeds) / len(speeds)
    var = sum((s - mean_s) ** 2 for s in speeds) / max(len(speeds), 1)
    std = math.sqrt(var)
    omega_cur = max(0.0, min(1.0, 1.0 / (1.0 + std)))

    th = aggregate_thermohaline(grid)
    omega_th = max(0.0, min(1.0, 1.0 - 5.0 * th.overturning_tendency))

    c0 = grid[len(grid) // 2]
    td = tide_state_for_cell(t_s, c0.λ_rad, c0.φ_rad, EARTH_OCEAN)
    omega_tide = max(0.0, min(1.0, 1.0 - abs(td.eta_equilibrium_m) / 5.0))

    risks = []
    if nx >= 3 and ny >= 3:
        idx = 0
        for iy in range(1, ny - 1):
            for ix in range(1, nx - 1):
                c = grid[iy * nx + ix]
                e = grid[iy * nx + (ix + 1)]
                w = grid[iy * nx + (ix - 1)]
                n = grid[(iy + 1) * nx + ix]
                s = grid[(iy - 1) * nx + ix]
                sf = seafloor_state_from_bathymetry_grid(
                    c.bathymetry_m, e.bathymetry_m, w.bathymetry_m,
                    n.bathymetry_m, s.bathymetry_m, dx_m, dy_m,
                )
                trench = 1.0 if sf.seafloor_class == SeafloorClass.TRENCH else 0.0
                risks.append(trench * 0.3 + min(abs(sf.slope_x) + abs(sf.slope_y), 1.0) * 0.2)
        omega_sf = max(0.0, min(1.0, 1.0 - sum(risks) / max(len(risks), 1)))
    else:
        omega_sf = 1.0

    omega_route = max(0.0, min(1.0, 1.0 - mean_s / 3.0))
    return omega_cur, omega_th, omega_tide, omega_sf, omega_route


def verdict_from_omegas(
    oc: float,
    oth: float,
    ot: float,
    osf: float,
    oru: float,
) -> OceanHealthVerdict:
    m = min(oc, oth, ot, osf, oru)
    if m >= 0.75:
        return OceanHealthVerdict.HEALTHY
    if m >= 0.55:
        return OceanHealthVerdict.STABLE
    if m >= 0.35:
        return OceanHealthVerdict.FRAGILE
    return OceanHealthVerdict.CRITICAL


def build_forecast_frame(
    current: CurrentFieldState,
    cells: Iterable[OceanCellState],
    horizon_s: float,
) -> OceanForecastFrame:
    grid = list(cells)
    th = aggregate_thermohaline(grid)
    c0 = grid[len(grid) // 2] if grid else OceanCellState()
    td = tide_state_for_cell(current.t_s, c0.λ_rad, c0.φ_rad, EARTH_OCEAN)
    oc, oth, ot, osf, oru = omega_metrics_from_grid(
        grid,
        current.nx,
        current.ny,
        current.dx_m,
        current.dy_m,
        current.t_s,
    )
    vd = verdict_from_omegas(oc, oth, ot, osf, oru)
    return OceanForecastFrame(
        t0_s=current.t_s,
        horizon_s=horizon_s,
        current=current,
        thermohaline=th,
        tide=td,
        omega_current_stability=oc,
        omega_thermohaline=oth,
        omega_tidal_predictability=ot,
        omega_seafloor_risk=osf,
        omega_route_utility=oru,
        verdict=vd,
    )
