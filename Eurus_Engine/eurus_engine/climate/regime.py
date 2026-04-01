"""
Eurus_Engine — climate regime classifier
"""

from __future__ import annotations

from eurus_engine.contracts.schemas import (
    ClimateRegimeReport,
    ClimateRegimeType,
    EARTH,
    GlobalAtmosphereState,
    PlanetConfig,
    WeatherHealthReport,
    WeatherPhase,
)


def classify_climate_regime(
    state: GlobalAtmosphereState,
    report: WeatherHealthReport,
    *,
    mean_humidity: float = 0.60,
    planet: PlanetConfig = EARTH,
) -> ClimateRegimeReport:
    pressure_ratio = state.mean_sea_level_pressure_pa / max(planet.surface_pressure_pa, 1.0)
    temp_k = state.mean_surface_temp_k
    energy = state.energy_imbalance_wm2
    notes: list[str] = []

    phase = state.phase

    if pressure_ratio < 0.25:
        regime = ClimateRegimeType.THIN_ATMOSPHERE
        notes.append("pressure_ratio_below_nominal")
    elif pressure_ratio > 3.0:
        regime = ClimateRegimeType.DENSE_ATMOSPHERE
        notes.append("pressure_ratio_above_nominal")
    elif phase == WeatherPhase.SEVERE:
        regime = ClimateRegimeType.STORM_DOMINANT
        notes.append("weather_phase_severe")
    elif temp_k > 330.0 or energy > 8.0:
        regime = ClimateRegimeType.HOT_GREENHOUSE
        notes.append("temperature_or_energy_hot")
    elif temp_k < 245.0 or mean_humidity < 0.18:
        regime = ClimateRegimeType.COLD_DRY
        notes.append("temperature_or_humidity_cold_dry")
    elif mean_humidity > 0.72 and phase in (WeatherPhase.DEVELOPING, WeatherPhase.ACTIVE):
        regime = ClimateRegimeType.HUMID_ACTIVE
        notes.append("humid_and_convectively_active")
    elif phase == WeatherPhase.ACTIVE and report.omega_total < 0.35 and abs(energy) > 6.0:
        regime = ClimateRegimeType.STORM_DOMINANT
        notes.append("active_and_highly_energetic")
    elif 273.0 <= temp_k <= 310.0 and 0.25 <= mean_humidity <= 0.80 and abs(energy) <= 4.0:
        regime = ClimateRegimeType.TEMPERATE
        notes.append("temperate_window")
    else:
        regime = ClimateRegimeType.UNSTABLE_TRANSITION
        notes.append("outside_named_basin")

    score = climate_regime_score(
        state,
        report,
        mean_humidity=mean_humidity,
        planet=planet,
        regime=regime,
    )
    return ClimateRegimeReport(regime=regime, climate_regime_score=score, notes=tuple(notes))


def climate_regime_score(
    state: GlobalAtmosphereState,
    report: WeatherHealthReport,
    *,
    mean_humidity: float = 0.60,
    planet: PlanetConfig = EARTH,
    regime: ClimateRegimeType | None = None,
) -> float:
    temp_score = _clamp(1.0 - abs(state.mean_surface_temp_k - 295.0) / 55.0, 0.0, 1.0)
    humidity_score = _clamp(1.0 - abs(mean_humidity - 0.55) / 0.55, 0.0, 1.0)
    energy_score = _clamp(1.0 - abs(state.energy_imbalance_wm2) / 10.0, 0.0, 1.0)
    pressure_ratio = state.mean_sea_level_pressure_pa / max(planet.surface_pressure_pa, 1.0)
    pressure_score = _clamp(1.0 - abs(pressure_ratio - 1.0) / 1.5, 0.0, 1.0)

    base = (
        0.30 * temp_score
        + 0.15 * humidity_score
        + 0.20 * energy_score
        + 0.15 * pressure_score
        + 0.20 * report.omega_total
    )

    if regime == ClimateRegimeType.TEMPERATE:
        base += 0.05
    elif regime in (ClimateRegimeType.HOT_GREENHOUSE, ClimateRegimeType.STORM_DOMINANT):
        base -= 0.10
    elif regime in (ClimateRegimeType.THIN_ATMOSPHERE, ClimateRegimeType.DENSE_ATMOSPHERE):
        base -= 0.08

    return round(_clamp(base, 0.0, 1.0), 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
