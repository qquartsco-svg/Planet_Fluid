"""코리올리·β (행성 자전). Eurus와 동일 수식, OceanPlanetConfig 사용."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oceanus_engine.contracts.schemas import OceanPlanetConfig

from oceanus_engine.contracts.schemas import EARTH_OCEAN


def coriolis_parameter(lat_rad: float, planet: "OceanPlanetConfig" = EARTH_OCEAN) -> float:
    return 2.0 * planet.rotation_rate_rads * math.sin(lat_rad)


def beta_parameter(lat_rad: float, planet: "OceanPlanetConfig" = EARTH_OCEAN) -> float:
    return (2.0 * planet.rotation_rate_rads * math.cos(lat_rad)) / planet.radius_m
