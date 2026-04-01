"""
Eurus_Engine — TerraCore 브릿지

TerraCore 엔진의 대기 상태를 Eurus_Engine 계약으로 변환.
duck-typing: TerraCore 가 설치되어 있지 않아도 작동.
"""

from __future__ import annotations

from typing import Any, Optional

from eurus_engine.contracts.schemas import (
    FluidCell, GlobalAtmosphereState, WeatherPhase,
)


def fluid_cell_from_terracore(terracore_cell: Any) -> FluidCell:
    """
    TerraCore 셀 (dict 또는 객체) → FluidCell.
    """
    if isinstance(terracore_cell, dict):
        d = terracore_cell
    else:
        # instance __dict__ (may be empty for class-attr objects) → fallback to getattr
        d = vars(terracore_cell) if hasattr(terracore_cell, "__dict__") else {}
        if not d:
            # class-level attribute fallback
            _keys = ("lon_rad","longitude_rad","lat_rad","latitude_rad",
                     "u_ms","wind_u_ms","v_ms","wind_v_ms",
                     "h_m","geopotential_m","p_pa","pressure_pa",
                     "T_k","temperature_k","q","specific_humidity")
            d = {k: getattr(terracore_cell, k)
                 for k in _keys if hasattr(terracore_cell, k)}

    return FluidCell(
        λ_rad=float(d.get("lon_rad", d.get("longitude_rad", 0.0))),
        φ_rad=float(d.get("lat_rad", d.get("latitude_rad", 0.0))),
        u_ms=float(d.get("u_ms", d.get("wind_u_ms", 0.0))),
        v_ms=float(d.get("v_ms", d.get("wind_v_ms", 0.0))),
        h_m=float(d.get("h_m", d.get("geopotential_m", 8_500.0))),
        p_pa=float(d.get("p_pa", d.get("pressure_pa", 101_325.0))),
        T_k=float(d.get("T_k", d.get("temperature_k", 288.15))),
        q=float(d.get("q", d.get("specific_humidity", 0.01))),
    )


def global_state_from_terracore(terracore_state: Any) -> GlobalAtmosphereState:
    """
    TerraCore 행성 대기 상태 → GlobalAtmosphereState.
    """
    if isinstance(terracore_state, dict):
        d = terracore_state
    elif hasattr(terracore_state, "__dict__"):
        d = vars(terracore_state)
    else:
        d = {}

    phase_str = str(d.get("phase", "calm")).upper()
    try:
        phase = WeatherPhase[phase_str]
    except KeyError:
        phase = WeatherPhase.CALM

    return GlobalAtmosphereState(
        t_s=float(d.get("t_s", d.get("simulation_time_s", 0.0))),
        mean_surface_temp_k=float(d.get("mean_temp_k", d.get("surface_temp_k", 288.15))),
        mean_sea_level_pressure_pa=float(d.get("mslp_pa", d.get("mean_pressure_pa", 101_325.0))),
        total_water_vapor_kg=float(d.get("water_vapor_kg", 1.27e16)),
        energy_imbalance_wm2=float(d.get("energy_imbalance_wm2", 0.0)),
        phase=phase,
    )


def optional_terracore_handoff(terracore_state: Any) -> Optional[GlobalAtmosphereState]:
    """TerraCore 상태 유효 시 변환, 실패 시 None."""
    if terracore_state is None:
        return None
    try:
        return global_state_from_terracore(terracore_state)
    except Exception:
        return None
