"""
Eurus_Engine — 행성 대기·날씨 동역학 데이터 계약

설계 원칙:
  - 행성 독립적 (지구·화성·금성·외계 행성 모두 지원)
  - 모든 단위 SI
  - stdlib 전용
  - frozen dataclass (불변 상태)

좌표계:
  λ: 경도 (rad), φ: 위도 (rad), z: 고도 (m)
  u: 동서 방향 속도 (m/s, 동쪽 양)
  v: 남북 방향 속도 (m/s, 북쪽 양)
  w: 수직 속도 (m/s, 상향 양)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


# ---------------------------------------------------------------------------
# 행성 물리 상수 프리셋
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PlanetConfig:
    """
    행성 물리 파라미터.

    기본값: 지구 (Earth).
    화성·금성·타이탄 등 다른 행성은 이 클래스를 교체해 사용.
    """
    name:              str   = "Earth"
    radius_m:          float = 6_371_000.0    # 행성 반지름 (m)
    gravity_ms2:       float = 9.80665         # 표면 중력 (m/s²)
    rotation_rate_rads: float = 7.292_115e-5  # 자전 각속도 (rad/s)
    surface_pressure_pa: float = 101_325.0    # 표준 지표 기압 (Pa)
    scale_height_m:    float = 8_500.0        # 대기 규모 높이 H (m)
    r_specific_j_kgk:  float = 287.058        # 비기체상수 Rd (J/kg·K)
    cp_j_kgk:          float = 1_004.0        # 정압 비열 (J/kg·K)
    solar_constant_wm2: float = 1_361.0       # 태양 상수 (W/m²)
    albedo:            float = 0.306          # 행성 알베도 (무차원)
    obliquity_rad:     float = math.radians(23.44)  # 자전축 기울기 (rad)

    # 파생
    @property
    def circumference_m(self) -> float:
        return 2.0 * math.pi * self.radius_m

    @property
    def day_s(self) -> float:
        """항성일 (s)."""
        return 2.0 * math.pi / self.rotation_rate_rads if self.rotation_rate_rads > 0 else float("inf")

    @property
    def dry_adiabatic_lapse_rate_k_m(self) -> float:
        """건조 단열 감율 Γd = g/cp (K/m)."""
        return self.gravity_ms2 / self.cp_j_kgk


# 행성 프리셋
EARTH  = PlanetConfig()
MARS   = PlanetConfig(
    name="Mars",
    radius_m=3_389_500.0,
    gravity_ms2=3.721,
    rotation_rate_rads=7.088e-5,
    surface_pressure_pa=636.0,
    scale_height_m=11_100.0,
    r_specific_j_kgk=188.9,   # CO₂ 지배 대기
    cp_j_kgk=735.0,
    solar_constant_wm2=589.0,
    albedo=0.250,
    obliquity_rad=math.radians(25.19),
)
VENUS  = PlanetConfig(
    name="Venus",
    radius_m=6_051_800.0,
    gravity_ms2=8.87,
    rotation_rate_rads=2.992e-7,   # 역방향 자전 (극히 느림)
    surface_pressure_pa=9_200_000.0,
    scale_height_m=15_900.0,
    r_specific_j_kgk=188.9,
    cp_j_kgk=820.0,
    solar_constant_wm2=2_601.0,
    albedo=0.690,
    obliquity_rad=math.radians(177.36),
)


# ---------------------------------------------------------------------------
# 대기 수직 레이어
# ---------------------------------------------------------------------------
class AtmosphereLayer(Enum):
    TROPOSPHERE    = "troposphere"      # 0 ~ 12 km (지구 기준)
    TROPOPAUSE     = "tropopause"       # ~12 km
    STRATOSPHERE   = "stratosphere"     # 12 ~ 50 km
    MESOSPHERE     = "mesosphere"       # 50 ~ 80 km
    THERMOSPHERE   = "thermosphere"     # 80 km 이상


# ---------------------------------------------------------------------------
# 날씨 단계 FSM
# ---------------------------------------------------------------------------
class WeatherPhase(Enum):
    CALM          = "calm"             # 안정 — 약한 순환
    DEVELOPING    = "developing"       # 대류계 발달 중
    ACTIVE        = "active"           # 활성 순환·전선 활동
    SEVERE        = "severe"           # 강한 기상 (태풍·폭풍)
    DISSIPATING   = "dissipating"      # 약화 단계
    EQUILIBRIUM   = "equilibrium"      # 복사 평형 도달


class ClimateRegimeType(Enum):
    TEMPERATE = "temperate"
    HOT_GREENHOUSE = "hot_greenhouse"
    COLD_DRY = "cold_dry"
    HUMID_ACTIVE = "humid_active"
    STORM_DOMINANT = "storm_dominant"
    THIN_ATMOSPHERE = "thin_atmosphere"
    DENSE_ATMOSPHERE = "dense_atmosphere"
    UNSTABLE_TRANSITION = "unstable_transition"


# ---------------------------------------------------------------------------
# 유체 상태 (한 격자점)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FluidCell:
    """
    단일 대기 격자 셀 — Shallow Water Equations 기반 상태.

    λ_rad : 경도 (rad)
    φ_rad : 위도 (rad)
    u_ms  : 동서 속도 (m/s)
    v_ms  : 남북 속도 (m/s)
    h_m   : 유체층 두께 / 지위 고도 (m)
    p_pa  : 기압 (Pa)
    T_k   : 기온 (K)
    q     : 비습도 (kg/kg) — 수증기
    """
    λ_rad: float = 0.0
    φ_rad: float = 0.0
    u_ms:  float = 0.0
    v_ms:  float = 0.0
    h_m:   float = 8_500.0    # 기본 규모 높이
    p_pa:  float = 101_325.0
    T_k:   float = 288.15
    q:     float = 0.01       # 비습도

    @property
    def speed_ms(self) -> float:
        return math.sqrt(self.u_ms**2 + self.v_ms**2)

    @property
    def wind_direction_deg(self) -> float:
        """기상 풍향 (북 기준 시계방향, 도)."""
        angle = math.degrees(math.atan2(-self.u_ms, -self.v_ms))
        return angle % 360.0

    @property
    def virtual_temperature_k(self) -> float:
        """가온도 Tv = T(1 + 0.608q)."""
        return self.T_k * (1.0 + 0.608 * self.q)

    @property
    def density_kg_m3(self) -> float:
        """공기 밀도 ρ = p/(Rd·Tv) (kg/m³)."""
        Rd = 287.058
        tv = max(self.virtual_temperature_k, 1.0)
        return self.p_pa / (Rd * tv)

    @property
    def mach(self) -> float:
        """마하수 (음속 = sqrt(γ·Rd·T), γ=1.4)."""
        cs = math.sqrt(1.4 * 287.058 * max(self.T_k, 1.0))
        return self.speed_ms / cs if cs > 0 else 0.0


# ---------------------------------------------------------------------------
# 대기 수직 프로파일
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VerticalProfile:
    """
    고도별 대기 상태 (1D 수직 컬럼).

    altitudes_m : 고도 배열 (m)
    temperatures_k : 각 고도의 기온 (K)
    pressures_pa : 각 고도의 기압 (Pa)
    densities_kg_m3 : 각 고도의 밀도 (kg/m³)
    """
    altitudes_m:      Tuple[float, ...] = ()
    temperatures_k:   Tuple[float, ...] = ()
    pressures_pa:     Tuple[float, ...] = ()
    densities_kg_m3:  Tuple[float, ...] = ()

    @property
    def n_levels(self) -> int:
        return len(self.altitudes_m)

    @property
    def tropopause_estimate_m(self) -> float:
        """기온 역전이 처음 나타나는 고도를 대류권계면으로 근사."""
        for i in range(1, len(self.temperatures_k)):
            if self.temperatures_k[i] >= self.temperatures_k[i - 1]:
                return float(self.altitudes_m[i])
        return 12_000.0  # 기본값


# ---------------------------------------------------------------------------
# 기압계 (고기압/저기압)
# ---------------------------------------------------------------------------
class PressureSystemType(Enum):
    HIGH   = "high"     # 고기압 (안티사이클론)
    LOW    = "low"      # 저기압 (사이클론)
    RIDGE  = "ridge"    # 기압 능
    TROUGH = "trough"   # 기압 골


@dataclass(frozen=True)
class PressureSystem:
    """기압계 — 고기압·저기압 중심."""
    system_type:      PressureSystemType
    center_lat_rad:   float      # 중심 위도
    center_lon_rad:   float      # 중심 경도
    central_pressure_pa: float   # 중심 기압 (Pa)
    radius_m:         float      # 영향 반경 (m)
    max_wind_ms:      float      # 최대 풍속 (m/s)
    intensity:        float      # 강도 0~1

    @property
    def is_cyclone(self) -> bool:
        return self.system_type == PressureSystemType.LOW

    @property
    def category(self) -> str:
        """사피어-심프슨 등급 (열대 저기압 기준)."""
        if not self.is_cyclone:
            return "HIGH"
        v = self.max_wind_ms
        if v < 17.0:   return "TD"    # 열대저압부
        if v < 33.0:   return "TS"    # 열대폭풍
        if v < 43.0:   return "C1"
        if v < 50.0:   return "C2"
        if v < 58.0:   return "C3"
        if v < 70.0:   return "C4"
        return "C5"


# ---------------------------------------------------------------------------
# 전선 (Front)
# ---------------------------------------------------------------------------
class FrontType(Enum):
    COLD  = "cold"      # 한랭 전선
    WARM  = "warm"      # 온난 전선
    OCCLUDED = "occluded"  # 폐색 전선
    STATIONARY = "stationary"  # 정체 전선


@dataclass(frozen=True)
class Front:
    """대기 전선."""
    front_type:    FrontType
    lat_rad:       float      # 전선 위치 (위도)
    lon_start_rad: float      # 경도 시작
    lon_end_rad:   float      # 경도 끝
    temp_gradient_k_m: float  # 온도 경도 (K/m)
    speed_ms:      float      # 전선 이동 속도 (m/s)
    precipitation: float      # 강수 강도 0~1


# ---------------------------------------------------------------------------
# 대기 안정도 지수
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StabilityIndex:
    """
    대기 안정도 지수 집합.

    CAPE : 대류 유효 위치 에너지 (J/kg)
    CIN  : 대류 억제 에너지 (J/kg)
    LI   : 리프티드 인덱스 (K) — 음수면 불안정
    K    : K-인덱스
    SI   : 쇼월터 안정도 지수
    """
    CAPE_j_kg:  float = 0.0
    CIN_j_kg:   float = 0.0
    LI_k:       float = 0.0
    K_index:    float = 0.0
    SI:         float = 0.0

    @property
    def convective_risk(self) -> str:
        """대류 위험도 판정."""
        if self.CAPE_j_kg > 3_000.0:  return "EXTREME"
        if self.CAPE_j_kg > 1_500.0:  return "HIGH"
        if self.CAPE_j_kg > 500.0:    return "MODERATE"
        if self.CAPE_j_kg > 100.0:    return "LOW"
        return "MINIMAL"


# ---------------------------------------------------------------------------
# 전지구 대기 상태 (스냅샷)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GlobalAtmosphereState:
    """
    시뮬레이션 한 스텝의 전지구 대기 상태.

    t_s            : 시뮬 시간 (s)
    mean_surface_temp_k : 전지구 평균 지표 온도 (K)
    mean_sea_level_pressure_pa : 평균 해수면 기압 (Pa)
    total_water_vapor_kg : 전지구 수증기 총량 (kg)
    energy_imbalance_wm2 : 복사 에너지 불균형 (W/m²) — 양수=온난화
    phase          : 현재 날씨 단계
    pressure_systems : 기압계 목록
    fronts         : 전선 목록
    """
    t_s:               float = 0.0
    mean_surface_temp_k: float = 288.15    # 지구 평균 기온 15°C
    mean_sea_level_pressure_pa: float = 101_325.0
    total_water_vapor_kg: float = 1.27e16  # 지구 전체 수증기량
    energy_imbalance_wm2: float = 0.0
    phase:             WeatherPhase = WeatherPhase.CALM
    pressure_systems:  Tuple[PressureSystem, ...] = ()
    fronts:            Tuple[Front, ...] = ()

    @property
    def global_warming_signal(self) -> str:
        if self.energy_imbalance_wm2 > 2.0:   return "STRONG_WARMING"
        if self.energy_imbalance_wm2 > 0.5:   return "WARMING"
        if self.energy_imbalance_wm2 < -0.5:  return "COOLING"
        return "EQUILIBRIUM"


# ---------------------------------------------------------------------------
# 날씨 건강도 (Ω 스코어)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WeatherHealthReport:
    """
    대기 건강도 종합 판정 (Ω 가중 스코어).

    5개 컴포넌트:
      omega_stability   — 대기 안정도 (CAPE 기준)
      omega_circulation — 순환 건강도 (로스비 수, 제트기류)
      omega_energy      — 복사 에너지 균형
      omega_moisture    — 수증기·강수 균형
      omega_dynamics    — 유체 동역학 상태 (와도, 발산)
      omega_total       — 가중 합산
    """
    omega_stability:   float = 0.0
    omega_circulation: float = 0.0
    omega_energy:      float = 0.0
    omega_moisture:    float = 0.0
    omega_dynamics:    float = 0.0
    omega_total:       float = 0.0

    phase:   WeatherPhase = WeatherPhase.CALM
    verdict: str = "UNKNOWN"    # "STABLE" | "ACTIVE" | "SEVERE" | "CRITICAL"
    blockers: Tuple[str, ...] = ()
    evidence: dict = field(default_factory=dict)

    @property
    def weather_ok(self) -> bool:
        return self.verdict in ("STABLE", "ACTIVE")


@dataclass(frozen=True)
class ClimateRegimeReport:
    regime: ClimateRegimeType = ClimateRegimeType.UNSTABLE_TRANSITION
    climate_regime_score: float = 0.0
    notes: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 순환 셀
# ---------------------------------------------------------------------------
class CirculationCellType(Enum):
    HADLEY  = "hadley"    # 열대 (0~30°)
    FERREL  = "ferrel"    # 중위도 (30~60°)
    POLAR   = "polar"     # 극지 (60~90°)


@dataclass(frozen=True)
class CirculationCell:
    """대기 대순환 셀."""
    cell_type:     CirculationCellType
    lat_low_rad:   float     # 셀 하단 위도
    lat_high_rad:  float     # 셀 상단 위도
    upper_wind_ms: float     # 상층 흐름 속도 (m/s)
    lower_wind_ms: float     # 하층 흐름 속도 (m/s)
    upwelling_lat_rad: float # 상승류 위도
    omega_cell:    float = 0.8  # 셀 건강도
