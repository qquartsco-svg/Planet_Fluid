"""
Eurus_Engine — 기압계 역학 (고기압·저기압)

기능:
  - Rankine 와류 모형 풍속
  - 가우시안 기압 프로파일
  - 사이클론 이동 (β-drift + 조향류)
  - 기압계 강도 변화율
  - 해수면 기압 위도 근사
"""

from __future__ import annotations

import dataclasses
import math
from typing import Optional

from eurus_engine.contracts.schemas import (
    PlanetConfig, EARTH, PressureSystem, PressureSystemType,
)


def rankine_vortex_wind(
    r_m: float,
    r_core_m: float,
    max_wind_ms: float,
) -> float:
    """
    Rankine 와류 모형 풍속 (m/s).
    r < r_core : 강체 회전  v = max_wind × (r / r_core)
    r ≥ r_core : 위치 와류  v = max_wind × (r_core / r)
    """
    if r_m <= 0:
        return 0.0
    if r_m < r_core_m:
        return max_wind_ms * r_m / max(r_core_m, 1.0)
    return max_wind_ms * r_core_m / max(r_m, 1.0)


def pressure_at_radius(
    central_pressure_pa: float,
    env_pressure_pa: float,
    r_m: float,
    radius_m: float,
) -> float:
    """
    가우시안 기압 프로파일.
    p(r) = p_env − (p_env − p_c) · exp(−r² / R²)
    """
    dp = env_pressure_pa - central_pressure_pa
    return env_pressure_pa - dp * math.exp(-(r_m**2) / max(radius_m**2, 1e-10))


def cyclone_drift_speed_ms(beta: float, radius_m: float) -> float:
    """
    β-drift 속도 (m/s). 사이클론 북서 이동.
    v_β ≈ β · R²  (단순 근사)
    """
    return beta * radius_m**2


def intensity_change_rate(
    system: PressureSystem,
    sst_k: float = 303.15,
    shear_ms: float = 5.0,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    기압계 강도 변화율 dI/dt (per hour, −1~+1).
    양수: 발달  /  음수: 약화.
    """
    if system.system_type == PressureSystemType.HIGH:
        return -0.01

    T_threshold_k = 299.15   # 26°C 임계 수온 (지구)
    sst_factor    = max(0.0, sst_k - T_threshold_k) / 5.0
    shear_penalty = min(1.0, shear_ms / 15.0)
    coriolis_ok   = abs(system.center_lat_rad) > math.radians(5.0)
    if not coriolis_ok:
        return 0.0
    return min(0.1, sst_factor * (1.0 - shear_penalty))


def advance_pressure_system(
    system: PressureSystem,
    dt_s: float,
    steering_u_ms: float = 5.0,
    steering_v_ms: float = 3.0,
    planet: PlanetConfig = EARTH,
) -> PressureSystem:
    """
    기압계 중심 위치 이동 (dt_s 후).
    조향류 + β-drift.
    """
    from eurus_engine.physics.fluid_dynamics import beta_parameter

    beta   = beta_parameter(system.center_lat_rad, planet)
    v_beta = cyclone_drift_speed_ms(beta, system.radius_m)

    cos_lat = math.cos(max(abs(system.center_lat_rad), 1e-6))
    dlon    = (steering_u_ms * dt_s) / (planet.radius_m * cos_lat)
    dlat    = (steering_v_ms + v_beta) * dt_s / planet.radius_m

    new_lat = max(-math.pi / 2, min(math.pi / 2,
                                     system.center_lat_rad + dlat))
    new_lon = (system.center_lon_rad + dlon) % (2 * math.pi)

    return dataclasses.replace(
        system,
        center_lat_rad=new_lat,
        center_lon_rad=new_lon,
    )


def estimate_mslp(
    T_surface_k: float,
    lat_rad: float,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    해수면 기압 근사 (Pa).
    아열대 고압대 (~30°) / 아한대 저압대 (~60°) 반영.
    """
    base     = planet.surface_pressure_pa
    lat_deg  = math.degrees(abs(lat_rad))
    sub_high = 1500.0 * math.exp(-((lat_deg - 30.0) ** 2) / 100.0)
    sub_low  = -1200.0 * math.exp(-((lat_deg - 60.0) ** 2) / 100.0)
    return base + sub_high + sub_low
