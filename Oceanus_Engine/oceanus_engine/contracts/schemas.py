"""
L0 — 해양·행성 해역 공통 계약 (Oceanus_Engine).

단위 SI, frozen dataclass. Eurus의 PlanetConfig와 개념 정렬하되 해양 전용 필드 확장.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional, Any


# ---------------------------------------------------------------------------
# 행성(해양 물리에 필요한 최소 집합)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OceanPlanetConfig:
    """해양 SWE·조석·코리올리에 쓰는 행성 상수."""
    name: str = "Earth"
    radius_m: float = 6_371_000.0
    gravity_ms2: float = 9.80665
    rotation_rate_rads: float = 7.292_115e-5
    # 해수 기본 밀도 스케일 (EOS는 thermohaline에서 갱신)
    rho_seawater_ref_kg_m3: float = 1025.0
    # 대기(바람 응력 스케일용)
    rho_air_ref_kg_m3: float = 1.225


EARTH_OCEAN = OceanPlanetConfig()


# ---------------------------------------------------------------------------
# L6 / Observer
# ---------------------------------------------------------------------------
class OceanHealthVerdict(str, Enum):
    HEALTHY = "HEALTHY"
    STABLE = "STABLE"
    FRAGILE = "FRAGILE"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# L1 — 격자 셀 (표층 얕은물 + 열염 슬롯)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OceanCellState:
    """
    단일 해양 격자 셀.

    λ_rad, φ_rad : 경·위도 (rad)
    u_ms, v_ms   : 깊이평균 유속, 동·북 (m/s)
    eta_m        : 평균해수면 대비 면고 이상 (m)
    bathymetry_m : 정지 수심 H (양수, m) — 해저까지
    T_k          : 수온 (K)
    S_psu        : 염분 (실용염도, PSU)
    p_bottom_pa  : 해저 압력 프록시 (Pa), 선택
    """
    λ_rad: float = 0.0
    φ_rad: float = 0.0
    u_ms: float = 0.0
    v_ms: float = 0.0
    eta_m: float = 0.0
    bathymetry_m: float = 4_000.0
    T_k: float = 288.15
    S_psu: float = 35.0
    p_bottom_pa: float = 0.0
    rho_kg_m3: float = 1025.0

    @property
    def water_column_m(self) -> float:
        """총 수층 두께 D = H + η (하한 적용)."""
        return max(self.bathymetry_m + self.eta_m, 1.0)

    @property
    def speed_ms(self) -> float:
        return math.sqrt(self.u_ms**2 + self.v_ms**2)


# ---------------------------------------------------------------------------
# L1 — 전역 유장 스냅샷
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CurrentFieldState:
    """2D 유장 메타 + 평균/최대 유속 요약 (브리지·L4 노드용)."""
    t_s: float = 0.0
    nx: int = 0
    ny: int = 0
    dx_m: float = 1.0
    dy_m: float = 1.0
    mean_speed_ms: float = 0.0
    max_speed_ms: float = 0.0
    mean_eta_m: float = 0.0
    # 평균 바람 응력 (N/m²) — Eurus 연계 메타
    wind_stress_east_nm2: float = 0.0
    wind_stress_north_nm2: float = 0.0


# ---------------------------------------------------------------------------
# L2 — 열염
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ThermohalineState:
    """격자 또는 박스 평균 열염 상태 + 단순 전환 경향."""
    T_k_mean: float = 288.15
    S_psu_mean: float = 35.0
    rho_kg_m3_mean: float = 1025.0
    # 양의 값: 표층 침강 경향 프록시 (무차원 스칼라)
    overturning_tendency: float = 0.0


# ---------------------------------------------------------------------------
# L3 — 조석 (달·태양 천체역학 메타 + 조화)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TideState:
    """
    조석 상태: 평형 조위 일부 + 주요 반일·일주 조화 진폭/위상.

    astronomical_phase_rad : 달·태양 황경 차 등으로부터 만든 결합 위상 프록시
    """
    t_s: float = 0.0
    eta_equilibrium_m: float = 0.0
    u_tidal_ms: float = 0.0
    v_tidal_ms: float = 0.0
    M2_amp_m: float = 0.5
    S2_amp_m: float = 0.25
    K1_amp_m: float = 0.15
    O1_amp_m: float = 0.10
    astronomical_phase_rad: float = 0.0


# ---------------------------------------------------------------------------
# L4 — 해저·판 경계
# ---------------------------------------------------------------------------
class SeafloorClass(str, Enum):
    ABYSSAL = "abyssal"
    CONTINENTAL_SHELF = "continental_shelf"
    SLOPE = "slope"
    RIDGE = "ridge"
    TRENCH = "trench"
    SEAMOUNT = "seamount"


@dataclass(frozen=True)
class SeafloorState:
    """해저 분류 + 경사(대륙붕·해구 연계)."""
    depth_m: float = 4_000.0
    slope_x: float = 0.0  # ∂H/∂x (무차원 경사)
    slope_y: float = 0.0
    seafloor_class: SeafloorClass = SeafloorClass.ABYSSAL
    hydrothermal_flux_wm2: float = 0.0


@dataclass(frozen=True)
class PlateBoundaryState:
    """판 경계 스칼라 + 이벤트 훅 식별자."""
    boundary_id: str = ""
    convergence_rate_m_yr: float = 0.0
    shear_rate_m_yr: float = 0.0
    seismic_coupling: float = 0.0  # 0~1
    last_event_t_s: Optional[float] = None


# ---------------------------------------------------------------------------
# L5 — 연안·항로
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CoastalState:
    """항만 접근·얕은 물 위험 프록시."""
    distance_to_shore_m: float = 1e6
    shallow_water_risk: float = 0.0  # 0~1
    harbor_access_score: float = 1.0  # 0~1


# ---------------------------------------------------------------------------
# 관측·예측 프레임
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OceanObservation:
    """단일 시점 관측(센서·위성·부이) 정규화."""
    t_s: float = 0.0
    λ_rad: float = 0.0
    φ_rad: float = 0.0
    eta_obs_m: Optional[float] = None
    u_obs_ms: Optional[float] = None
    v_obs_ms: Optional[float] = None
    T_obs_k: Optional[float] = None
    S_obs_psu: Optional[float] = None
    tide_gauge_m: Optional[float] = None
    quality: float = 1.0  # 0~1


@dataclass(frozen=True)
class OceanForecastFrame:
    """ATHENA/워크벤치용 요약 프레임."""
    t0_s: float = 0.0
    horizon_s: float = 3_600.0
    current: CurrentFieldState = field(default_factory=CurrentFieldState)
    thermohaline: ThermohalineState = field(default_factory=ThermohalineState)
    tide: TideState = field(default_factory=TideState)
    omega_current_stability: float = 1.0
    omega_thermohaline: float = 1.0
    omega_tidal_predictability: float = 1.0
    omega_seafloor_risk: float = 1.0
    omega_route_utility: float = 1.0
    verdict: OceanHealthVerdict = OceanHealthVerdict.STABLE
    meta: Tuple[Tuple[str, Any], ...] = ()
