"""
Eurus_Engine — Cherubim bridge

Expose atmosphere-derived habitability context without importing Cherubim.
"""

from __future__ import annotations

from typing import Any, Dict

from eurus_engine.climate.regime import classify_climate_regime
from eurus_engine.contracts.schemas import EARTH, GlobalAtmosphereState, PlanetConfig, WeatherHealthReport


def cherubim_context_from_eurus(
    state: GlobalAtmosphereState,
    report: WeatherHealthReport,
    *,
    planet: PlanetConfig = EARTH,
) -> Dict[str, Any]:
    climate_regime = classify_climate_regime(state, report, mean_humidity=report.omega_moisture, planet=planet)
    temp_window = _temperature_window_proxy(state.mean_surface_temp_k)
    water_availability = _clamp(
        (state.total_water_vapor_kg / 1.27e16) * 0.45 + report.omega_moisture * 0.55,
        0.0,
        1.0,
    )
    radiation_proxy = _clamp(1.0 - abs(state.energy_imbalance_wm2) / 12.0, 0.0, 1.0)
    pressure_proxy = _clamp(state.mean_sea_level_pressure_pa / max(planet.surface_pressure_pa, 1.0), 0.0, 5.0)
    climate_stability = _clamp(report.omega_total, 0.0, 1.0)

    return {
        "temperature_window_proxy": temp_window,
        "water_availability_proxy": water_availability,
        "radiation_proxy": radiation_proxy,
        "climate_stability_proxy": climate_stability,
        "pressure_atm": pressure_proxy,
        "eden_climate_score": round(
            0.35 * temp_window
            + 0.25 * water_availability
            + 0.20 * radiation_proxy
            + 0.20 * climate_stability,
            4,
        ),
        "eurus_phase": state.phase.value,
        "eurus_verdict": report.verdict,
        "eurus_regime": climate_regime.regime.value,
        "climate_regime_score": climate_regime.climate_regime_score,
    }


def _temperature_window_proxy(temp_k: float) -> float:
    return _clamp(1.0 - abs(temp_k - 295.0) / 35.0, 0.0, 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
