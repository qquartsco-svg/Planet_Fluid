"""
Eurus → Oceanus 바람 forcing.

- `FluidCell` 등 **u_ms / v_ms**(동·북, m/s) 보유 객체는 표층 풍(10 m 근사)으로 그대로 매핑한다.
- `WeatherAgent`·`CirculationCell`은 **스칼라 순환 하층풍**만 있으므로, 위도에 맞는 셀의
  `lower_wind_ms`를 **동서 성분**으로 쓰는 **프록시**를 제공한다(정밀 항해용이 아님).

`eurus_engine` 패키지는 필수 의존성이 아니다(덕 타이핑).
"""
from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple


def wind_10m_ms_from_fluid_like(fluid: Any) -> Tuple[float, float]:
    """
    Eurus `FluidCell`과 동일 규약: u = 동쪽, v = 북쪽 (m/s).
    """
    u = float(getattr(fluid, "u_ms", 0.0))
    v = float(getattr(fluid, "v_ms", 0.0))
    return u, v


def select_circulation_cell_for_lat(
    cells: List[Any],
    lat_rad: float,
) -> Optional[Any]:
    """위도가 [lat_low, lat_high]에 들어가는 첫 `CirculationCell` (북반구 띠 가정)."""
    phi = lat_rad
    for c in cells:
        lo = float(getattr(c, "lat_low_rad", -math.pi))
        hi = float(getattr(c, "lat_high_rad", math.pi))
        if lo <= phi <= hi:
            return c
    return cells[0] if cells else None


def wind_10m_proxy_from_circulation_cell(
    cell: Any,
    *,
    zonal_east_scale: float = 1.0,
    meridional_north_scale: float = 0.15,
) -> Tuple[float, float]:
    """
    하층 스칼라 풍을 (u_east, v_north)로 분해하는 단순 프록시.

    - 동서: ``zonal_east_scale * lower_wind_ms`` (Eurus Hadley 하층 양수 → 동풍 쪽 스케일)
    - 남북: ``meridional_north_scale * upper_wind_ms`` (제트·경도 평균 프록시)
    """
    lw = float(getattr(cell, "lower_wind_ms", 0.0))
    uw = float(getattr(cell, "upper_wind_ms", 0.0))
    u = zonal_east_scale * lw
    v = meridional_north_scale * uw
    return u, v


def wind_10m_ms_from_weather_agent_like(
    agent: Any,
    *,
    zonal_east_scale: float = 1.0,
    meridional_north_scale: float = 0.15,
) -> Tuple[float, float]:
    """
    `WeatherAgent`의 위도에 맞는 순환 셀을 고른 뒤
    :func:`wind_10m_proxy_from_circulation_cell` 적용.
    """
    cells = list(getattr(agent, "cells", []) or [])
    lat = float(getattr(agent, "lat_rad", 0.0))
    c = select_circulation_cell_for_lat(cells, lat)
    if c is None:
        return 0.0, 0.0
    return wind_10m_proxy_from_circulation_cell(
        c,
        zonal_east_scale=zonal_east_scale,
        meridional_north_scale=meridional_north_scale,
    )


def apply_wind_to_ocean_grid(
    grid: Any,
    wind_u_ms: float,
    wind_v_ms: float,
) -> None:
    """`OceanGridModel.set_wind_field` 덕 타이핑."""
    setter = getattr(grid, "set_wind_field", None)
    if setter is None:
        raise TypeError("grid must provide set_wind_field(wind_u_ms, wind_v_ms)")
    setter(float(wind_u_ms), float(wind_v_ms))


def apply_eurus_fluid_wind_to_ocean_grid(grid: Any, fluid: Any) -> None:
    """`FluidCell` → 균일 바람 forcing."""
    u, v = wind_10m_ms_from_fluid_like(fluid)
    apply_wind_to_ocean_grid(grid, u, v)


def apply_eurus_weather_agent_wind_to_ocean_grid(
    grid: Any,
    agent: Any,
    **kwargs: Any,
) -> None:
    """`WeatherAgent` 순환 프록시 → 균일 바람 forcing."""
    u, v = wind_10m_ms_from_weather_agent_like(agent, **kwargs)
    apply_wind_to_ocean_grid(grid, u, v)
