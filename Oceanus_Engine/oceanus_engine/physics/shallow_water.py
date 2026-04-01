"""
L1 — 해양 얕은물 방정식 (표층 유장).

∂u/∂t + u·∇u − f v = −g ∂η/∂x + τ_x/(ρD) + ν∇²u
∂v/∂t + u·∇v + f u = −g ∂η/∂y + τ_y/(ρD) + ν∇²v
∂η/∂t + ∇·((D)u) = S_η   (D = H + η)

Eurus SWE와 정렬하되 면고는 η, 정수심은 H.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Tuple

from oceanus_engine.contracts.schemas import OceanCellState, OceanPlanetConfig, EARTH_OCEAN
from oceanus_engine.physics.coriolis import coriolis_parameter


def central_diff(f_plus: float, f_minus: float, delta: float) -> float:
    return (f_plus - f_minus) / (2.0 * delta + 1e-15)


def laplacian_2d(
    f_center: float,
    f_east: float,
    f_west: float,
    f_north: float,
    f_south: float,
    dx: float,
    dy: float,
) -> float:
    d2fdx2 = (f_east - 2.0 * f_center + f_west) / (dx**2 + 1e-30)
    d2fdy2 = (f_north - 2.0 * f_center + f_south) / (dy**2 + 1e-30)
    return d2fdx2 + d2fdy2


def wind_stress_from_wind_10m(
    wind_u_ms: float,
    wind_v_ms: float,
    rho_air: float = 1.225,
    cd: float = 1.2e-3,
) -> Tuple[float, float]:
    """
    단순 벌크 공식: τ = ρ_a C_d |W| W  (N/m²).
    """
    wsp = math.sqrt(wind_u_ms**2 + wind_v_ms**2 + 1e-12)
    tau = rho_air * cd * wsp
    return tau * wind_u_ms, tau * wind_v_ms


def ocean_swe_tendency(
    u: float,
    v: float,
    eta: float,
    D: float,
    dudx: float,
    dudy: float,
    dvdx: float,
    dvdy: float,
    detadx: float,
    detady: float,
    dDudx: float,
    dDvdy: float,
    f: float,
    g: float,
    rho: float,
    nu: float,
    lap_u: float,
    lap_v: float,
    tau_x: float,
    tau_y: float,
    q_eta: float = 0.0,
) -> Tuple[float, float, float]:
    """Returns (du/dt, dv/dt, dη/dt)."""
    adv_u = -(u * dudx + v * dudy)
    adv_v = -(u * dvdx + v * dvdy)
    pgf_u = -g * detadx + f * v
    pgf_v = -g * detady - f * u
    inv_rho_d = 1.0 / (rho * max(D, 1.0))
    stress_u = tau_x * inv_rho_d
    stress_v = tau_y * inv_rho_d
    du_dt = adv_u + pgf_u + nu * lap_u + stress_u
    dv_dt = adv_v + pgf_v + nu * lap_v + stress_v
    # 연속식: ∂η/∂t = −∇·(D u) + Q
    deta_dt = -(dDudx + dDvdy) + q_eta
    return du_dt, dv_dt, deta_dt


def _flux_du(D: float, u: float) -> float:
    return D * u


def step_ocean_cell_euler(
    cell: OceanCellState,
    east: OceanCellState,
    west: OceanCellState,
    north: OceanCellState,
    south: OceanCellState,
    dt_s: float,
    dx_m: float,
    dy_m: float,
    planet: OceanPlanetConfig = EARTH_OCEAN,
    nu: float = 500.0,
    wind_u_ms: float = 0.0,
    wind_v_ms: float = 0.0,
    tide_eta_source_per_s: float = 0.0,
) -> OceanCellState:
    """
    단일 셀 Euler 스텝. ∇·(Du)는 중앙 차분 (D·u 각각 면에서 평균).
    """
    g = planet.gravity_ms2
    f = coriolis_parameter(cell.φ_rad, planet)
    rho = max(cell.rho_kg_m3, 1000.0)
    eta = cell.eta_m
    D = max(cell.bathymetry_m + eta, 1.0)

    dudx = central_diff(east.u_ms, west.u_ms, dx_m)
    dudy = central_diff(north.u_ms, south.u_ms, dy_m)
    dvdx = central_diff(east.v_ms, west.v_ms, dx_m)
    dvdy = central_diff(north.v_ms, south.v_ms, dy_m)
    detadx = central_diff(east.eta_m, west.eta_m, dx_m)
    detady = central_diff(north.eta_m, south.eta_m, dy_m)

    lap_u = laplacian_2d(
        cell.u_ms, east.u_ms, west.u_ms, north.u_ms, south.u_ms, dx_m, dy_m
    )
    lap_v = laplacian_2d(
        cell.v_ms, east.v_ms, west.v_ms, north.v_ms, south.v_ms, dx_m, dy_m
    )

    # 면 플럭스 (간단 산술 평균)
    De, Dw = max(east.bathymetry_m + east.eta_m, 1.0), max(west.bathymetry_m + west.eta_m, 1.0)
    Dn, Ds = max(north.bathymetry_m + north.eta_m, 1.0), max(south.bathymetry_m + south.eta_m, 1.0)
    dDudx = central_diff(_flux_du(De, east.u_ms), _flux_du(Dw, west.u_ms), dx_m)
    dDvdy = central_diff(_flux_du(Dn, north.v_ms), _flux_du(Ds, south.v_ms), dy_m)

    tau_x, tau_y = wind_stress_from_wind_10m(
        wind_u_ms, wind_v_ms, rho_air=planet.rho_air_ref_kg_m3
    )

    du_dt, dv_dt, deta_dt = ocean_swe_tendency(
        cell.u_ms,
        cell.v_ms,
        eta,
        D,
        dudx,
        dudy,
        dvdx,
        dvdy,
        detadx,
        detady,
        dDudx,
        dDvdy,
        f,
        g,
        rho,
        nu,
        lap_u,
        lap_v,
        tau_x,
        tau_y,
        q_eta=tide_eta_source_per_s,
    )

    c_g = math.sqrt(g * D)
    spd = cell.speed_ms
    cfl_limit = 0.8 * min(dx_m, dy_m) / (c_g + spd + 1e-9)
    dt_eff = min(dt_s, cfl_limit)

    new_u = cell.u_ms + du_dt * dt_eff
    new_v = cell.v_ms + dv_dt * dt_eff
    new_eta = cell.eta_m + deta_dt * dt_eff

    return dataclasses.replace(
        cell,
        u_ms=new_u,
        v_ms=new_v,
        eta_m=new_eta,
    )
