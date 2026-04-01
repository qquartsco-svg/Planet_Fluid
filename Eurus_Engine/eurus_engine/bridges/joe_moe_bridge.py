"""
Eurus_Engine — JOE/MOE snapshot bridge

Shared planet snapshot (JOE → MOE → Cherubim) to Eurus atmospheric state.
"""

from __future__ import annotations

from typing import Any, Mapping

from eurus_engine.contracts.schemas import EARTH, GlobalAtmosphereState, PlanetConfig, WeatherPhase
from eurus_engine.physics.thermodynamics import equilibrium_temperature_k


def eurus_state_from_planet_snapshot(
    snapshot: Mapping[str, Any],
    *,
    planet: PlanetConfig = EARTH,
    t_s: float = 0.0,
) -> GlobalAtmosphereState:
    greenhouse = _clamp01(_float(snapshot.get("greenhouse_proxy", 0.5), 0.5))
    albedo_eff = _clamp(_float(snapshot.get("albedo_eff", planet.albedo), planet.albedo), 0.0, 0.95)
    hydrology = _clamp01(_float(snapshot.get("hydrology_stability_proxy", 0.5), 0.5))
    biosphere = _clamp01(_float(snapshot.get("biosphere_window_score", 0.5), 0.5))
    climate_variance = _clamp01(_float(snapshot.get("climate_variance_proxy", 0.25), 0.25))
    seasonality = _clamp01(_float(snapshot.get("seasonality_proxy", 0.25), 0.25))
    water_surface = max(0.0, _float(snapshot.get("W_surface", 1.0), 1.0))
    water_total = max(water_surface, _float(snapshot.get("W_total", water_surface or 1.0), water_surface or 1.0))
    pressure_proxy = max(0.0, _float(snapshot.get("P_w", 0.5), 0.5))

    base_temp = equilibrium_temperature_k(0.0, 180, planet)
    temp_k = base_temp + 42.0 * (greenhouse - 0.5) - 10.0 * seasonality + 4.0 * (0.5 - albedo_eff)
    temp_k = _clamp(temp_k, 120.0, 900.0)

    energy_imbalance = 8.0 * (greenhouse - 0.5) + 4.0 * (climate_variance - 0.5) - 2.0 * (albedo_eff - planet.albedo)
    water_ratio = water_surface / max(water_total, 1.0)
    water_vapor_kg = 1.27e16 * _clamp(0.15 + 1.25 * hydrology * water_ratio * (0.6 + 0.4 * biosphere), 0.02, 3.0)
    pressure_pa = planet.surface_pressure_pa * _clamp(0.45 + 0.75 * greenhouse + 0.20 * pressure_proxy, 0.05, 25.0)

    severity = max(abs(energy_imbalance), climate_variance * 10.0, (1.0 - hydrology) * 6.0)
    if severity > 6.5:
        phase = WeatherPhase.SEVERE
    elif severity > 4.0:
        phase = WeatherPhase.ACTIVE
    elif severity > 2.0:
        phase = WeatherPhase.DEVELOPING
    else:
        phase = WeatherPhase.CALM

    return GlobalAtmosphereState(
        t_s=t_s,
        mean_surface_temp_k=temp_k,
        mean_sea_level_pressure_pa=pressure_pa,
        total_water_vapor_kg=water_vapor_kg,
        energy_imbalance_wm2=energy_imbalance,
        phase=phase,
    )


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp01(value: float) -> float:
    return _clamp(value, 0.0, 1.0)
