"""
Eurus_Engine — 행성 대기 날씨 동역학 엔진  v0.1.4

Public API:
  WeatherAgent        — 메인 FSM 오케스트레이터
  WeatherEvent        — 이벤트 타입 상수
  assess_weather_health — Ω 5레이어 건강도
  EARTH, MARS, VENUS  — 행성 프리셋

Quick Start::

    from eurus_engine import WeatherAgent, WeatherEvent, EARTH

    agent = WeatherAgent(planet=EARTH, lat_rad=0.52, day_of_year=182)
    agent.initialize(T_surface_k=300.0)
    for _ in range(24):
        agent.tick(dt_s=3600.0)   # 24-hour simulation
    print(agent.summary())
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__: str = version("eurus_engine")
except PackageNotFoundError:
    try:
        from pathlib import Path
        __version__ = (Path(__file__).parent.parent / "VERSION").read_text().strip()
    except Exception:
        __version__ = "0.1.4"

# --- 행성 상수 & 계약 ---
from eurus_engine.contracts.schemas import (
    PlanetConfig, EARTH, MARS, VENUS,
    FluidCell, VerticalProfile, GlobalAtmosphereState,
    WeatherPhase, WeatherHealthReport, StabilityIndex,
    ClimateRegimeType, ClimateRegimeReport,
    PressureSystem, PressureSystemType, Front, FrontType,
    CirculationCell, CirculationCellType,
)

# --- 유체역학 ---
from eurus_engine.physics.fluid_dynamics import (
    coriolis_parameter, beta_parameter, rossby_number,
    geostrophic_wind,
    relative_vorticity, absolute_vorticity, potential_vorticity,
    divergence,
    step_cell_euler,
    gravity_wave_speed, rossby_wave_speed,
    kinetic_energy_density, available_potential_energy,
)

# --- 열역학 ---
from eurus_engine.physics.thermodynamics import (
    saturation_vapor_pressure_pa, mixing_ratio_sat,
    relative_humidity, dew_point_k,
    dry_adiabatic_lapse_rate, moist_adiabatic_lapse_rate,
    potential_temperature, equivalent_potential_temperature,
    cape_cin_simple, stability_index,
    insolation_wm2, outgoing_longwave_radiation_wm2,
    radiative_energy_balance, equilibrium_temperature_k,
)

# --- 수직 프로파일 ---
from eurus_engine.physics.vertical_profile import (
    standard_atmosphere_profile, lcl_altitude_m,
    interpolate_profile_at_altitude, brunt_vaisala_frequency,
    hydrostatic_pressure, density_from_ideal_gas, scale_height,
)

# --- 대순환 ---
from eurus_engine.circulation.hadley_cell import (
    build_circulation_cells, hadley_cell_strength,
    jet_stream_latitude_rad, jet_stream_speed_ms,
    walker_circulation_strength, itcz_latitude_rad,
)
from eurus_engine.circulation.pressure_system import (
    rankine_vortex_wind, pressure_at_radius,
    advance_pressure_system, estimate_mslp,
    intensity_change_rate,
)
from eurus_engine.circulation.fronts import (
    advance_front, occlude_front, frontal_precipitation,
    cold_front_speed_ms, warm_front_speed_ms,
)

# --- climate regime ---
from eurus_engine.climate.regime import classify_climate_regime, climate_regime_score

# --- 건강도 ---
from eurus_engine.health.weather_health import (
    assess_weather_health,
    omega_stability, omega_circulation,
    omega_energy, omega_moisture, omega_dynamics,
)

# --- 에이전트 ---
from eurus_engine.agent.weather_agent import WeatherAgent, WeatherEvent

# --- 브릿지 ---
from eurus_engine.bridges.joe_moe_bridge import eurus_state_from_planet_snapshot
from eurus_engine.bridges.cherubim_bridge import cherubim_context_from_eurus
from eurus_engine.bridges.terracore_bridge import (
    fluid_cell_from_terracore, global_state_from_terracore, optional_terracore_handoff,
)
from eurus_engine.bridges.lucifer_bridge import (
    atmosphere_obs_from_lucifer, orbital_coverage_lat_band, ground_resolution_m,
)

__all__ = [
    "__version__",
    # planets
    "PlanetConfig", "EARTH", "MARS", "VENUS",
    # schemas
    "FluidCell", "VerticalProfile", "GlobalAtmosphereState",
    "WeatherPhase", "WeatherHealthReport", "StabilityIndex",
    "ClimateRegimeType", "ClimateRegimeReport",
    "PressureSystem", "PressureSystemType", "Front", "FrontType",
    "CirculationCell", "CirculationCellType",
    # fluid dynamics
    "coriolis_parameter", "beta_parameter", "rossby_number",
    "geostrophic_wind",
    "relative_vorticity", "absolute_vorticity", "potential_vorticity",
    "divergence",
    "step_cell_euler",
    "gravity_wave_speed", "rossby_wave_speed",
    "kinetic_energy_density", "available_potential_energy",
    # thermodynamics
    "saturation_vapor_pressure_pa", "mixing_ratio_sat",
    "relative_humidity", "dew_point_k",
    "dry_adiabatic_lapse_rate", "moist_adiabatic_lapse_rate",
    "potential_temperature", "equivalent_potential_temperature",
    "cape_cin_simple", "stability_index",
    "insolation_wm2", "outgoing_longwave_radiation_wm2",
    "radiative_energy_balance", "equilibrium_temperature_k",
    # vertical profile
    "standard_atmosphere_profile", "lcl_altitude_m",
    "interpolate_profile_at_altitude", "brunt_vaisala_frequency",
    "hydrostatic_pressure", "density_from_ideal_gas", "scale_height",
    # circulation
    "build_circulation_cells", "hadley_cell_strength",
    "jet_stream_latitude_rad", "jet_stream_speed_ms",
    "walker_circulation_strength", "itcz_latitude_rad",
    "rankine_vortex_wind", "pressure_at_radius",
    "advance_pressure_system", "estimate_mslp", "intensity_change_rate",
    "advance_front", "occlude_front", "frontal_precipitation",
    "cold_front_speed_ms", "warm_front_speed_ms",
    # climate regime
    "classify_climate_regime", "climate_regime_score",
    # health
    "assess_weather_health",
    "omega_stability", "omega_circulation",
    "omega_energy", "omega_moisture", "omega_dynamics",
    # agent
    "WeatherAgent", "WeatherEvent",
    # bridges
    "eurus_state_from_planet_snapshot",
    "cherubim_context_from_eurus",
    "fluid_cell_from_terracore", "global_state_from_terracore", "optional_terracore_handoff",
    "atmosphere_obs_from_lucifer", "orbital_coverage_lat_band", "ground_resolution_m",
]
