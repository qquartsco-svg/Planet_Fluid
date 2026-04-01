"""
Eurus_Engine — 대기 전선 역학

기능:
  - 한랭/온난/폐색/정체 전선 이동
  - 전선 강수 강도 추정
  - 폐색 전선 합성
  - 전선면 기온 분포
"""

from __future__ import annotations

import dataclasses
import math

from eurus_engine.contracts.schemas import (
    Front, FrontType, PlanetConfig, EARTH,
)


def cold_front_speed_ms(
    upper_wind_ms: float,
    surface_friction: float = 0.7,
) -> float:
    """
    한랭 전선 이동 속도 (m/s).
    상층풍의 ~70 % (마찰 감소).
    """
    return upper_wind_ms * surface_friction


def warm_front_speed_ms(upper_wind_ms: float) -> float:
    """
    온난 전선 이동 속도 (m/s). 한랭 전선보다 느림.
    """
    return upper_wind_ms * 0.4


def frontal_precipitation(front: Front) -> float:
    """
    전선 강수 강도 (0~1).
    한랭: 대류성 (강함) / 온난: 층상 (약함) / 폐색: 중간.
    """
    base = front.precipitation
    if front.front_type == FrontType.COLD:
        return min(1.0, base * 1.3)
    if front.front_type == FrontType.WARM:
        return min(1.0, base * 0.8)
    if front.front_type == FrontType.OCCLUDED:
        return min(1.0, base * 1.0)
    return base   # STATIONARY


def advance_front(
    front: Front,
    dt_s: float,
    upper_wind_ms: float = 15.0,
    planet: PlanetConfig = EARTH,
) -> Front:
    """
    전선 위도 방향 이동.
    한랭 전선: 남쪽으로 / 온난 전선: 북쪽으로.
    """
    if front.front_type == FrontType.COLD:
        spd  = cold_front_speed_ms(upper_wind_ms)
        dlat = -spd * dt_s / planet.radius_m
    elif front.front_type == FrontType.WARM:
        spd  = warm_front_speed_ms(upper_wind_ms)
        dlat = spd * dt_s / planet.radius_m
    else:
        dlat = 0.0

    new_lat = max(-math.pi / 2, min(math.pi / 2, front.lat_rad + dlat))
    return dataclasses.replace(front, lat_rad=new_lat)


def occlude_front(cold: Front, warm: Front) -> Front:
    """
    한랭·온난 전선이 합쳐져 폐색 전선 생성.
    강도 = 두 전선 가중 평균.
    """
    avg_lat    = 0.5 * (cold.lat_rad + warm.lat_rad)
    avg_grad   = 0.5 * (cold.temp_gradient_k_m + warm.temp_gradient_k_m)
    avg_spd    = 0.3 * cold.speed_ms + 0.7 * warm.speed_ms
    avg_precip = 0.6 * cold.precipitation + 0.4 * warm.precipitation

    return Front(
        front_type=FrontType.OCCLUDED,
        lat_rad=avg_lat,
        lon_start_rad=min(cold.lon_start_rad, warm.lon_start_rad),
        lon_end_rad=max(cold.lon_end_rad, warm.lon_end_rad),
        temp_gradient_k_m=avg_grad,
        speed_ms=avg_spd,
        precipitation=avg_precip,
    )


def frontal_temperature_at(
    front: Front,
    lat_rad: float,
    T_cold_k: float,
    T_warm_k: float,
) -> float:
    """
    전선 인근 기온 추정 (K).
    전선 남쪽: 따뜻한 공기  /  전선 북쪽: 찬 공기.
    """
    dist_m = abs(lat_rad - front.lat_rad) * 6_371_000.0
    if lat_rad < front.lat_rad:
        return T_warm_k - front.temp_gradient_k_m * dist_m
    return T_cold_k + front.temp_gradient_k_m * dist_m
