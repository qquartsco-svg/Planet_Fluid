"""
Eurus_Engine — WeatherAgent FSM

날씨 동역학 시뮬레이션 오케스트레이터.

FSM:  CALM → DEVELOPING → ACTIVE → SEVERE → DISSIPATING → EQUILIBRIUM

기능:
  - 복사 에너지 균형 → 기온 강제
  - 대순환 셀 갱신 (Hadley·Ferrel·Polar)
  - WeatherHealthReport (Ω 5레이어)
  - 이벤트 충격 (폭풍·화산·엘니뇨 등)
  - Athena 권고
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from eurus_engine.climate.regime import classify_climate_regime
from eurus_engine.contracts.schemas import (
    CirculationCell, GlobalAtmosphereState, PlanetConfig,
    StabilityIndex, WeatherHealthReport, WeatherPhase, EARTH,
)
from eurus_engine.physics.thermodynamics import (
    equilibrium_temperature_k, radiative_energy_balance, stability_index,
)
from eurus_engine.physics.vertical_profile import standard_atmosphere_profile
from eurus_engine.circulation.hadley_cell import build_circulation_cells
from eurus_engine.health.weather_health import assess_weather_health


# ---------------------------------------------------------------------------
# 이벤트 타입
# ---------------------------------------------------------------------------
class WeatherEvent:
    TROPICAL_CYCLONE   = "tropical_cyclone"
    VOLCANIC_ERUPTION  = "volcanic_eruption"
    EL_NINO            = "el_nino"
    LA_NINA            = "la_nina"
    POLAR_VORTEX_SPLIT = "polar_vortex_split"
    DROUGHT            = "drought"
    HEAT_DOME          = "heat_dome"
    ATMOSPHERIC_RIVER  = "atmospheric_river"


# ---------------------------------------------------------------------------
# WeatherAgent
# ---------------------------------------------------------------------------
class WeatherAgent:
    """
    행성 날씨 동역학 에이전트.

    사용 예::

        from eurus_engine import WeatherAgent, WeatherEvent, EARTH
        agent = WeatherAgent(planet=EARTH, lat_rad=0.52, day_of_year=182)
        agent.initialize(T_surface_k=300.0)
        for _ in range(24):
            agent.tick(dt_s=3600.0)
        print(agent.summary())
    """

    def __init__(
        self,
        planet: PlanetConfig = EARTH,
        lat_rad: float = 0.523_599,   # ~30°N
        day_of_year: int = 182,
    ) -> None:
        self.planet      = planet
        self.lat_rad     = lat_rad
        self.day_of_year = day_of_year

        self.t_s: float                      = 0.0
        self.T_surface_k: float              = 288.15
        self.energy_imbalance_wm2: float     = 0.0
        self.mean_humidity: float            = 0.60
        self.phase: WeatherPhase             = WeatherPhase.CALM
        self.cells: List[CirculationCell]    = []
        self.stability: StabilityIndex       = StabilityIndex()
        self.history: List[Dict[str, Any]]   = []
        self._initialized: bool              = False

        # 동역학 진단
        self.max_vorticity:  float = 1e-5
        self.max_divergence: float = 1e-6
        self.cfl_fraction:   float = 0.5

    # ------------------------------------------------------------------
    # 초기화
    # ------------------------------------------------------------------

    def initialize(
        self,
        T_surface_k: float = 288.15,
        humidity: float = 0.60,
        season_factor: float = 0.0,
    ) -> None:
        """에이전트 초기화 — 수직 프로파일·순환 셀·안정도 설정."""
        self.T_surface_k  = T_surface_k
        self.mean_humidity = humidity
        self._initialized  = True

        self._profile = standard_atmosphere_profile(
            planet=self.planet,
            T_surface_k=T_surface_k,
        )

        self.cells = build_circulation_cells(
            equatorial_T_k=T_surface_k + 15.0,
            pole_T_k=T_surface_k - 50.0,
            planet=self.planet,
            season_factor=season_factor,
        )

        self.stability = stability_index(
            self._profile,
            T_surface_k,
            self.planet.surface_pressure_pa,
            T_surface_k - 5.0,
        )

        self.energy_imbalance_wm2 = radiative_energy_balance(
            self.lat_rad, self.T_surface_k, self.day_of_year, self.planet,
        )
        self._update_phase()

    # ------------------------------------------------------------------
    # 틱
    # ------------------------------------------------------------------

    def tick(self, dt_s: float = 3_600.0) -> None:
        """한 시간 스텝 전진."""
        if not self._initialized:
            self.initialize()

        self.t_s += dt_s

        # 1. 복사 강제
        imbalance = radiative_energy_balance(
            self.lat_rad, self.T_surface_k, self.day_of_year, self.planet,
        )
        self.energy_imbalance_wm2 = imbalance

        # 2. 기온 변화: ΔT = R·dt / (ρ·cp·H)
        rho_cp_H = 1.225 * self.planet.cp_j_kgk * self.planet.scale_height_m
        dT = imbalance * dt_s / max(rho_cp_H, 1.0)
        self.T_surface_k = max(100.0, self.T_surface_k + dT)

        # 3. 습도 변화
        dq = -0.001 * dT
        self.mean_humidity = max(0.05, min(0.99, self.mean_humidity + dq))

        # 4. 순환 셀 갱신
        self.cells = build_circulation_cells(
            equatorial_T_k=self.T_surface_k + 15.0,
            pole_T_k=self.T_surface_k - 50.0,
            planet=self.planet,
        )

        # 5. 동역학 진단
        if self.cells:
            from eurus_engine.physics.fluid_dynamics import coriolis_parameter
            U    = abs(self.cells[0].upper_wind_ms)
            L    = self.planet.radius_m * 0.3
            c_g  = math.sqrt(self.planet.gravity_ms2 * self.planet.scale_height_m)
            self.max_vorticity  = U / max(L, 1.0)
            self.max_divergence = self.max_vorticity * 0.1
            self.cfl_fraction   = (U + c_g) * dt_s / max(L, 1.0)

        # 6. FSM 갱신
        self._update_phase()

        # 7. 히스토리
        self.history.append({
            "t_s": self.t_s,
            "T_surface_k": round(self.T_surface_k, 2),
            "energy_imbalance_wm2": round(self.energy_imbalance_wm2, 3),
            "humidity": round(self.mean_humidity, 3),
            "phase": self.phase.value,
        })

    def _update_phase(self) -> None:
        """에너지 불균형·CAPE 기반 FSM 전이."""
        imb  = abs(self.energy_imbalance_wm2)
        cape = self.stability.CAPE_j_kg

        if imb > 15.0 or cape > 3000.0:
            self.phase = WeatherPhase.SEVERE
        elif imb > 8.0 or cape > 1500.0:
            self.phase = WeatherPhase.ACTIVE
        elif imb > 3.0 or cape > 500.0:
            self.phase = WeatherPhase.DEVELOPING
        elif imb < 0.5 and cape < 100.0:
            T_eq = equilibrium_temperature_k(
                self.lat_rad, self.day_of_year, self.planet
            )
            if abs(self.T_surface_k - T_eq) < 2.0:
                self.phase = WeatherPhase.EQUILIBRIUM
            else:
                self.phase = WeatherPhase.CALM
        else:
            self.phase = WeatherPhase.CALM

    # ------------------------------------------------------------------
    # 이벤트 충격
    # ------------------------------------------------------------------

    def apply_event(self, event: str, magnitude: float = 1.0) -> None:
        """날씨 이벤트 충격 적용. magnitude: 0~1."""
        if event == WeatherEvent.TROPICAL_CYCLONE:
            self.energy_imbalance_wm2 += 20.0 * magnitude
            self.max_vorticity        *= 1.0 + 5.0 * magnitude
            self.phase                 = WeatherPhase.SEVERE

        elif event == WeatherEvent.VOLCANIC_ERUPTION:
            self.T_surface_k          -= 5.0 * magnitude
            self.energy_imbalance_wm2 -= 10.0 * magnitude
            self.mean_humidity        += 0.05 * magnitude

        elif event == WeatherEvent.EL_NINO:
            self.T_surface_k          += 2.0 * magnitude
            self.mean_humidity        += 0.05 * magnitude
            self.energy_imbalance_wm2 += 5.0 * magnitude

        elif event == WeatherEvent.LA_NINA:
            self.T_surface_k   -= 1.5 * magnitude
            self.mean_humidity -= 0.03 * magnitude

        elif event == WeatherEvent.HEAT_DOME:
            self.T_surface_k          += 8.0 * magnitude
            self.mean_humidity        -= 0.10 * magnitude
            self.energy_imbalance_wm2 += 12.0 * magnitude

        elif event == WeatherEvent.DROUGHT:
            self.mean_humidity -= 0.20 * magnitude
            self.T_surface_k   += 3.0 * magnitude

        elif event == WeatherEvent.ATMOSPHERIC_RIVER:
            self.mean_humidity += 0.25 * magnitude
            self.T_surface_k   += 1.0 * magnitude

        elif event == WeatherEvent.POLAR_VORTEX_SPLIT:
            self.T_surface_k          -= 10.0 * magnitude
            self.energy_imbalance_wm2 -= 8.0 * magnitude

        # 범위 클리핑
        self.T_surface_k  = max(100.0, self.T_surface_k)
        self.mean_humidity = max(0.05, min(0.99, self.mean_humidity))
        self._update_phase()

    # ------------------------------------------------------------------
    # 건강도 리포트
    # ------------------------------------------------------------------

    def health_report(self) -> WeatherHealthReport:
        """현재 상태 WeatherHealthReport 생성."""
        state = GlobalAtmosphereState(
            t_s=self.t_s,
            mean_surface_temp_k=self.T_surface_k,
            energy_imbalance_wm2=self.energy_imbalance_wm2,
            phase=self.phase,
        )
        jet_speed = abs(self.cells[0].upper_wind_ms) if self.cells else 30.0
        return assess_weather_health(
            state=state,
            stability=self.stability,
            cells=self.cells,
            mean_humidity=self.mean_humidity,
            jet_speed_ms=jet_speed,
            max_vorticity_s1=self.max_vorticity,
            max_divergence_s1=self.max_divergence,
            cfl_fraction=self.cfl_fraction,
        )

    def athena_recommendations(self) -> List[str]:
        """Athena 권고 — 날씨 복원 우선 조치."""
        report = self.health_report()
        recs: List[str] = []

        if "HIGH_INSTABILITY" in report.blockers:
            recs.append("TRIGGER: convective_parameterization_adjustment")
        if "ENERGY_IMBALANCE" in report.blockers:
            if self.energy_imbalance_wm2 > 0:
                recs.append("TRIGGER: albedo_enhancement (cloud_seeding)")
            else:
                recs.append("TRIGGER: greenhouse_gas_reduction")
        if "CIRCULATION_BREAKDOWN" in report.blockers:
            recs.append("TRIGGER: jet_stream_restoration_check")
        if "MOISTURE_ANOMALY" in report.blockers:
            if self.mean_humidity < 0.4:
                recs.append("TRIGGER: precipitation_enhancement")
            else:
                recs.append("TRIGGER: evaporation_balance_check")
        if "DYNAMICS_UNSTABLE" in report.blockers:
            recs.append("TRIGGER: timestep_reduction (CFL_violation)")

        if not recs:
            recs.append("STATUS: nominal — no intervention required")
        return recs

    def summary(self) -> Dict[str, Any]:
        """에이전트 상태 요약."""
        report = self.health_report()
        regime = classify_climate_regime(
            GlobalAtmosphereState(
                t_s=self.t_s,
                mean_surface_temp_k=self.T_surface_k,
                mean_sea_level_pressure_pa=self.planet.surface_pressure_pa,
                total_water_vapor_kg=1.27e16 * self.mean_humidity,
                energy_imbalance_wm2=self.energy_imbalance_wm2,
                phase=self.phase,
            ),
            report,
            mean_humidity=self.mean_humidity,
            planet=self.planet,
        )
        return {
            "t_s": self.t_s,
            "planet": self.planet.name,
            "T_surface_k": round(self.T_surface_k, 2),
            "energy_imbalance_wm2": round(self.energy_imbalance_wm2, 3),
            "mean_humidity": round(self.mean_humidity, 3),
            "phase": self.phase.value,
            "climate_regime": regime.regime.value,
            "climate_regime_score": regime.climate_regime_score,
            "omega_total": report.omega_total,
            "verdict": report.verdict,
            "blockers": list(report.blockers),
            "recommendations": self.athena_recommendations(),
            "n_steps": len(self.history),
        }
