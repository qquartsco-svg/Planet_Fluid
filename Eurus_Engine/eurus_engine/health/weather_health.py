"""
Eurus_Engine — 날씨 건강도 Observer (Ω 5레이어)

구성:
  Ω_stability   — 대기 안정도 (CAPE/CIN)
  Ω_circulation — 순환 건강도 (셀·제트기류)
  Ω_energy      — 복사 에너지 균형
  Ω_moisture    — 수증기·강수 균형
  Ω_dynamics    — 유체 동역학 (와도·발산·CFL)

  Ω_global = 가중합 → 판정
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from eurus_engine.contracts.schemas import (
    CirculationCell, GlobalAtmosphereState, StabilityIndex,
    WeatherHealthReport, WeatherPhase,
)

# 가중치
_W = dict(stability=0.25, circulation=0.25, energy=0.20, moisture=0.15, dynamics=0.15)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# 개별 Ω 계산
# ---------------------------------------------------------------------------

def omega_stability(
    stability: StabilityIndex,
    phase: WeatherPhase,
) -> float:
    """
    Ω_stability (0~1).
    CAPE < 500 J/kg : 안정 (1.0)
    CAPE > 3000 J/kg: 불안정 (0.0)
    """
    cape = stability.CAPE_j_kg
    cin  = stability.CIN_j_kg

    if cape < 500.0:
        score = 1.0
    elif cape < 1500.0:
        score = 1.0 - (cape - 500.0) / 1000.0 * 0.4
    elif cape < 3000.0:
        score = 0.6 - (cape - 1500.0) / 1500.0 * 0.4
    else:
        score = 0.0

    cin_penalty = min(0.2, abs(cin) / 500.0 * 0.2)
    return _clamp(score - cin_penalty)


def omega_circulation(
    cells: List[CirculationCell],
    mean_wind_ms: float = 10.0,
    jet_speed_ms: float = 30.0,
) -> float:
    """
    Ω_circulation (0~1).
    순환 셀 평균 건강도 + 제트기류 정상 범위 (20~60 m/s).
    """
    if not cells:
        return 0.5

    cell_health = sum(c.omega_cell for c in cells) / len(cells)

    if jet_speed_ms < 20.0:
        jet_score = jet_speed_ms / 20.0
    elif jet_speed_ms <= 60.0:
        jet_score = 1.0
    else:
        jet_score = max(0.0, 1.0 - (jet_speed_ms - 60.0) / 40.0)

    return _clamp(cell_health * 0.6 + jet_score * 0.4)


def omega_energy(energy_imbalance_wm2: float) -> float:
    """
    Ω_energy (0~1).
    |imbalance| < 1 W/m²: 건강 (1.0)
    |imbalance| > 10 W/m²: 위험 (0.0)
    """
    imb = abs(energy_imbalance_wm2)
    if imb < 1.0:
        return 1.0
    if imb < 5.0:
        return 1.0 - (imb - 1.0) / 4.0 * 0.5
    if imb < 10.0:
        return 0.5 - (imb - 5.0) / 5.0 * 0.5
    return 0.0


def omega_moisture(
    mean_humidity: float,
    precip_balance: float = 0.0,
) -> float:
    """
    Ω_moisture (0~1).
    상대습도 40~70%: 최적
    강수-증발 균형 ±2 mm/day: 정상
    """
    if 0.40 <= mean_humidity <= 0.70:
        hum_score = 1.0
    elif mean_humidity < 0.40:
        hum_score = mean_humidity / 0.40
    else:
        hum_score = max(0.0, 1.0 - (mean_humidity - 0.70) / 0.30)

    balance_score = max(0.0, 1.0 - abs(precip_balance) / 5.0)
    return _clamp(hum_score * 0.6 + balance_score * 0.4)


def omega_dynamics(
    max_vorticity_s1: float = 1e-5,
    max_divergence_s1: float = 1e-6,
    cfl_fraction: float = 0.5,
) -> float:
    """
    Ω_dynamics (0~1).
    와도·발산 기후값 범위 내, CFL 안전 범위.
    """
    vort_score = _clamp(1.0 - max_vorticity_s1 / 5e-4)
    div_score  = _clamp(1.0 - max_divergence_s1 / 5e-5)
    cfl_score  = _clamp(1.0 - max(0.0, cfl_fraction - 0.8) / 0.2)
    return vort_score * 0.4 + div_score * 0.3 + cfl_score * 0.3


# ---------------------------------------------------------------------------
# 통합 Observer
# ---------------------------------------------------------------------------

def assess_weather_health(
    state: GlobalAtmosphereState,
    stability: Optional[StabilityIndex] = None,
    cells: Optional[List[CirculationCell]] = None,
    mean_humidity: float = 0.60,
    jet_speed_ms: float = 30.0,
    max_vorticity_s1: float = 1e-5,
    max_divergence_s1: float = 1e-6,
    cfl_fraction: float = 0.5,
    evidence: Optional[Dict[str, Any]] = None,
) -> WeatherHealthReport:
    """날씨 건강도 종합 판정 (Ω 5레이어)."""
    if stability is None:
        stability = StabilityIndex()
    if cells is None:
        cells = []

    ω_s = omega_stability(stability, state.phase)
    ω_c = omega_circulation(cells, jet_speed_ms=jet_speed_ms)
    ω_e = omega_energy(state.energy_imbalance_wm2)
    ω_m = omega_moisture(mean_humidity)
    ω_d = omega_dynamics(max_vorticity_s1, max_divergence_s1, cfl_fraction)

    ω_total = (
        _W["stability"]   * ω_s +
        _W["circulation"] * ω_c +
        _W["energy"]      * ω_e +
        _W["moisture"]    * ω_m +
        _W["dynamics"]    * ω_d
    )

    # 강제 임계치
    if state.phase == WeatherPhase.SEVERE:
        ω_total = min(ω_total, 0.35)
    elif state.phase == WeatherPhase.ACTIVE:
        ω_total = min(ω_total, 0.65)

    # 판정
    if ω_total >= 0.80:
        verdict = "STABLE"
    elif ω_total >= 0.60:
        verdict = "ACTIVE"
    elif ω_total >= 0.40:
        verdict = "FRAGILE"
    else:
        verdict = "CRITICAL"

    # 블로커
    blockers: list[str] = []
    if ω_s < 0.40:
        blockers.append("HIGH_INSTABILITY")
    if ω_c < 0.40:
        blockers.append("CIRCULATION_BREAKDOWN")
    if ω_e < 0.40:
        blockers.append("ENERGY_IMBALANCE")
    if ω_m < 0.40:
        blockers.append("MOISTURE_ANOMALY")
    if ω_d < 0.40:
        blockers.append("DYNAMICS_UNSTABLE")

    return WeatherHealthReport(
        omega_stability=round(ω_s, 4),
        omega_circulation=round(ω_c, 4),
        omega_energy=round(ω_e, 4),
        omega_moisture=round(ω_m, 4),
        omega_dynamics=round(ω_d, 4),
        omega_total=round(ω_total, 4),
        phase=state.phase,
        verdict=verdict,
        blockers=tuple(blockers),
        evidence=evidence or {},
    )
