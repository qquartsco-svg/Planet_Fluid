"""
Eurus_Engine — 대기 대순환 셀 (Hadley / Ferrel / Polar)

기능:
  - 위도 기반 순환 셀 구분 (Hadley·Ferrel·Polar)
  - Hadley 셀 세기: 열대 가열 강도 함수
  - 제트기류 위치·강도 추정
  - Walker 순환 (엘니뇨 지수)
"""

from __future__ import annotations

import math
from typing import List

from eurus_engine.contracts.schemas import (
    CirculationCell, CirculationCellType, PlanetConfig, EARTH,
)


def hadley_cell_strength(
    equatorial_T_k: float,
    pole_T_k: float,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    Hadley 셀 강도 지수 (0~1).
    적도-극 온도 차가 클수록 순환 강함.
    지구 기준 ΔT ≈ 30 K → 강도 1.0
    """
    delta_T = max(0.0, equatorial_T_k - pole_T_k)
    return min(1.0, delta_T / 30.0)


def jet_stream_latitude_rad(
    planet: PlanetConfig = EARTH,
    season_factor: float = 0.0,  # -1: 겨울, +1: 여름
) -> float:
    """
    아열대 제트기류 위도 추정 (rad).
    지구 기준 ~30°, 계절에 따라 ±5° 변동.
    """
    base_lat_deg = 30.0
    seasonal_shift = 5.0 * season_factor
    earth_radius = 6_371_000.0
    scale = math.sqrt(earth_radius / max(planet.radius_m, 1e6))
    return math.radians((base_lat_deg + seasonal_shift) * scale)


def jet_stream_speed_ms(
    hadley_strength: float,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    제트기류 최대 풍속 근사 (m/s).
    지구 기준 강도 1.0 → ~50 m/s
    """
    earth_rot = 7.292e-5
    rot_factor = planet.rotation_rate_rads / max(earth_rot, 1e-10)
    return 50.0 * hadley_strength * rot_factor


def build_circulation_cells(
    equatorial_T_k: float = 305.0,
    pole_T_k: float = 250.0,
    planet: PlanetConfig = EARTH,
    season_factor: float = 0.0,
) -> List[CirculationCell]:
    """
    행성 대기 대순환 셀 3개 (Hadley · Ferrel · Polar) 생성.
    북반구 기준.
    """
    strength  = hadley_cell_strength(equatorial_T_k, pole_T_k, planet)
    jet_lat   = jet_stream_latitude_rad(planet, season_factor)
    jet_speed = jet_stream_speed_ms(strength, planet)

    hadley = CirculationCell(
        cell_type=CirculationCellType.HADLEY,
        lat_low_rad=0.0,
        lat_high_rad=jet_lat,
        upper_wind_ms=-jet_speed * 0.6,   # 상층 편동풍
        lower_wind_ms=jet_speed * 0.3,    # 하층 무역풍
        upwelling_lat_rad=0.0,             # ITCZ
        omega_cell=min(1.0, strength * 1.2),
    )

    polar_lat = math.radians(60.0)
    ferrel = CirculationCell(
        cell_type=CirculationCellType.FERREL,
        lat_low_rad=jet_lat,
        lat_high_rad=polar_lat,
        upper_wind_ms=jet_speed * 0.4,
        lower_wind_ms=-jet_speed * 0.2,
        upwelling_lat_rad=polar_lat,
        omega_cell=min(1.0, strength * 0.9),
    )

    polar = CirculationCell(
        cell_type=CirculationCellType.POLAR,
        lat_low_rad=polar_lat,
        lat_high_rad=math.pi / 2.0,
        upper_wind_ms=jet_speed * 0.2,
        lower_wind_ms=-jet_speed * 0.15,
        upwelling_lat_rad=math.pi / 2.0,
        omega_cell=min(1.0, strength * 0.7),
    )

    return [hadley, ferrel, polar]


def itcz_latitude_rad(season_factor: float = 0.0) -> float:
    """
    열대 수렴대 (ITCZ) 위도 (rad).
    season_factor: -1=1월, +1=7월 → ±5° 계절 이동.
    """
    return math.radians(5.0 * season_factor)


def walker_circulation_strength(
    east_pacific_T_k: float,
    west_pacific_T_k: float,
) -> float:
    """
    Walker 순환 강도 (−1 ~ +1). 엘니뇨 지수.
    정상: west > east → 양수
    엘니뇨: east ≥ west → 약화·역전
    """
    delta = west_pacific_T_k - east_pacific_T_k
    return max(-1.0, min(1.0, delta / 3.0))
