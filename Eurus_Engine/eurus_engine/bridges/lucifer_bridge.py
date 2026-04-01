"""
Eurus_Engine — Lucifer_Engine 브릿지

궤도에서 관측한 행성 대기 정보를 Eurus_Engine 계약으로 변환.
Lucifer_Engine 없이도 작동 (duck-typing).
"""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple

from eurus_engine.contracts.schemas import (
    GlobalAtmosphereState, PlanetConfig, EARTH, WeatherPhase,
)


def atmosphere_obs_from_lucifer(
    orbit_state: Any,
    planet: PlanetConfig = EARTH,
) -> Optional[GlobalAtmosphereState]:
    """
    Lucifer_Engine OrbitAgent 상태(dict 또는 객체)에서
    대기 관측값 추출 → GlobalAtmosphereState.

    orbit_state 필드:
      nadir_T_k             — 지표 복사 온도 (K)
      cloud_fraction        — 구름 피복 (0~1)
      energy_imbalance_wm2  — OLR − SW 잔차
      t_s                   — 시뮬레이션 시간 (s)
    """
    if orbit_state is None:
        return None

    if isinstance(orbit_state, dict):
        d = orbit_state
    elif hasattr(orbit_state, "__dict__"):
        d = vars(orbit_state)
    else:
        return None

    try:
        nadir_T  = float(d.get("nadir_T_k", 288.15))
        cloud_f  = float(d.get("cloud_fraction", 0.5))
        imbalance = float(d.get("energy_imbalance_wm2", 0.0))
        t_s      = float(d.get("t_s", 0.0))

        # 구름 피복 → 날씨 단계 추정
        if cloud_f > 0.8:
            phase = WeatherPhase.ACTIVE
        elif cloud_f > 0.5:
            phase = WeatherPhase.DEVELOPING
        else:
            phase = WeatherPhase.CALM

        return GlobalAtmosphereState(
            t_s=t_s,
            mean_surface_temp_k=nadir_T,
            energy_imbalance_wm2=imbalance,
            phase=phase,
        )
    except Exception:
        return None


def orbital_coverage_lat_band(
    inclination_rad: float,
) -> Tuple[float, float]:
    """
    궤도 경사각에서 관측 가능한 위도 범위 (rad).
    Returns (south_lat_rad, north_lat_rad).
    """
    return -inclination_rad, inclination_rad


def ground_resolution_m(
    altitude_m: float,
    sensor_ifov_rad: float = 1e-4,
) -> float:
    """
    지상 해상도 GSD = altitude × IFOV (m).
    """
    return altitude_m * sensor_ifov_rad
