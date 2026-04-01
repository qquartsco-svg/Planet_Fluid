"""
Eurus_Engine — 대기 열역학

구현:
  - 건조/습윤 단열 감율
  - 상당 위온도 (θe)
  - 대기 안정도 (CAPE, CIN, LI)
  - 포화 수증기압 (Magnus 공식)
  - 잠열 방출 (응결)
  - 복사 에너지 균형

모든 단위 SI.
"""

from __future__ import annotations

import math
from typing import Tuple

from eurus_engine.contracts.schemas import (
    PlanetConfig, EARTH, StabilityIndex, VerticalProfile,
)

# ---------------------------------------------------------------------------
# 물리 상수
# ---------------------------------------------------------------------------
_Rd   = 287.058     # 건조 공기 비기체상수 (J/kg·K)
_Rv   = 461.5       # 수증기 비기체상수 (J/kg·K)
_Lv   = 2.501e6     # 물 증발 잠열 (J/kg) at 0°C
_cp   = 1_004.0     # 정압 비열 (J/kg·K)
_eps  = _Rd / _Rv   # ≈ 0.622
_P0   = 100_000.0   # 기준 기압 (Pa)
_T0   = 273.15      # 0°C in K


# ---------------------------------------------------------------------------
# A. 포화 수증기압 (Magnus / Tetens 공식)
# ---------------------------------------------------------------------------

def saturation_vapor_pressure_pa(T_k: float) -> float:
    """
    포화 수증기압 es(T) (Pa).
    Magnus 공식 (액체수 기준):
      es = 611.2 · exp(17.67·(T−273.15) / (T−29.65))
    """
    # Magnus 공식은 T_c > −243°C 범위에서만 유효; 극저온 방어
    T_k_safe = max(T_k, 183.15)   # −90°C 이하는 클램프 (지구 최저기록 −89.2°C)
    T_c = T_k_safe - _T0
    denom = T_c + 243.5
    if abs(denom) < 0.1:
        return 611.2
    exponent = 17.67 * T_c / denom
    exponent = max(-100.0, min(100.0, exponent))  # overflow 방지
    return 611.2 * math.exp(exponent)


def mixing_ratio_sat(T_k: float, p_pa: float) -> float:
    """
    포화 혼합비 ws = εes/(p−es) (kg/kg).
    """
    es = saturation_vapor_pressure_pa(T_k)
    return _eps * es / max(p_pa - es, 1.0)


def relative_humidity(T_k: float, T_dew_k: float) -> float:
    """상대 습도 RH = es(Td)/es(T) (0~1)."""
    es_t = saturation_vapor_pressure_pa(T_k)
    es_d = saturation_vapor_pressure_pa(T_dew_k)
    return min(1.0, es_d / max(es_t, 1e-10))


def dew_point_k(T_k: float, RH: float) -> float:
    """이슬점 Td (K). Magnus 역함수."""
    if RH <= 0.0:
        return _T0
    ln_rh = math.log(max(RH, 1e-9))
    T_c = T_k - _T0
    # Magnus 역함수: Td_c = 243.5·(ln(RH)+17.67·Tc/(Tc+243.5)) / ...
    numer = 243.5 * (ln_rh + 17.67 * T_c / (T_c + 243.5))
    denom = 17.67 - (ln_rh + 17.67 * T_c / (T_c + 243.5))
    return numer / max(denom, 1e-9) + _T0


# ---------------------------------------------------------------------------
# B. 단열 감율
# ---------------------------------------------------------------------------

def dry_adiabatic_lapse_rate(planet: PlanetConfig = EARTH) -> float:
    """건조 단열 감율 Γd = g/cp (K/m)."""
    return planet.gravity_ms2 / planet.cp_j_kgk


def moist_adiabatic_lapse_rate(T_k: float, p_pa: float,
                                planet: PlanetConfig = EARTH) -> float:
    """
    습윤 단열 감율 Γm (K/m).
    Γm = g(1 + Lv·ws/(Rd·T)) / (cp + Lv²·ws/(Rv·T²))
    """
    ws = mixing_ratio_sat(T_k, p_pa)
    g = planet.gravity_ms2
    numer = g * (1.0 + _Lv * ws / (_Rd * T_k))
    denom = _cp + _Lv**2 * ws / (_Rv * T_k**2)
    return numer / max(denom, 1e-9)


# ---------------------------------------------------------------------------
# C. 위온도 (Potential Temperature)
# ---------------------------------------------------------------------------

def potential_temperature(T_k: float, p_pa: float) -> float:
    """위온도 θ = T·(P0/p)^(Rd/cp) (K)."""
    return T_k * (_P0 / max(p_pa, 1.0)) ** (_Rd / _cp)


def equivalent_potential_temperature(T_k: float, p_pa: float,
                                     q_kg_kg: float) -> float:
    """
    상당 위온도 θe ≈ θ · exp(Lv·q / (cp·T)) (K).
    보존량 — 습윤 대류 추적에 사용.
    """
    theta = potential_temperature(T_k, p_pa)
    return theta * math.exp(_Lv * q_kg_kg / (_cp * max(T_k, 1.0)))


# ---------------------------------------------------------------------------
# D. 대기 안정도 지수
# ---------------------------------------------------------------------------

def lifted_index(
    T_env_500_k: float,    # 500 hPa 환경 기온 (K)
    T_parcel_500_k: float, # 500 hPa까지 들어 올린 공기덩이 기온 (K)
) -> float:
    """
    리프티드 인덱스 LI = T_env − T_parcel (K).
    LI < 0 : 불안정 (대류 가능)
    LI > 0 : 안정
    """
    return T_env_500_k - T_parcel_500_k


def k_index(
    T_850_k: float,   # 850 hPa 기온
    T_500_k: float,   # 500 hPa 기온
    Td_850_k: float,  # 850 hPa 이슬점
    T_700_k: float,   # 700 hPa 기온
    Td_700_k: float,  # 700 hPa 이슬점
) -> float:
    """
    K-인덱스 = (T850−T500) + Td850 − (T700−Td700).
    > 40: 뇌우 강한 가능성
    > 30: 뇌우 가능성 있음
    """
    return ((T_850_k - T_500_k) + (Td_850_k - _T0)
            - ((T_700_k - _T0) - (Td_700_k - _T0)))


def cape_cin_simple(
    profile: VerticalProfile,
    T_surface_k: float,
    p_surface_pa: float,
    Td_surface_k: float,
) -> Tuple[float, float]:
    """
    단순 CAPE/CIN 적분 (사다리꼴 규칙).

    profile : 환경 수직 프로파일
    T_surface_k : 지표 기온
    p_surface_pa : 지표 기압
    Td_surface_k : 지표 이슬점

    Returns (CAPE_j_kg, CIN_j_kg)
    """
    if profile.n_levels < 2:
        return 0.0, 0.0

    g = EARTH.gravity_ms2
    cape = 0.0
    cin  = 0.0
    lfc_found = False   # 자유 대류 고도 도달 여부

    # 공기덩이 시작 상태
    T_p = T_surface_k
    p_p = p_surface_pa

    for i in range(1, profile.n_levels):
        z0 = profile.altitudes_m[i - 1]
        z1 = profile.altitudes_m[i]
        dz = z1 - z0

        T_env0 = profile.temperatures_k[i - 1]
        T_env1 = profile.temperatures_k[i]

        p0 = profile.pressures_pa[i - 1]
        p1 = profile.pressures_pa[i]
        p_mid = 0.5 * (p0 + p1)

        # 공기덩이 들어 올리기 — 포화 전: 건조 단열, 포화 후: 습윤 단열
        ws_p = mixing_ratio_sat(T_p, p_p)
        RH_p = relative_humidity(T_p, Td_surface_k)
        if RH_p < 1.0 and ws_p > 0.0:
            # 건조 단열
            gamma = dry_adiabatic_lapse_rate()
        else:
            gamma = moist_adiabatic_lapse_rate(T_p, p_p)

        T_p_new = max(T_p - gamma * dz, 180.0)  # 극저온 방어 (CAPE 계산 범위 제한)
        T_p_mid = 0.5 * (T_p + T_p_new)
        T_env_mid = 0.5 * (T_env0 + T_env1)

        dT = T_p_mid - T_env_mid
        buoyancy = g * dT / max(T_env_mid, 1.0)

        if buoyancy >= 0:
            lfc_found = True
            cape += buoyancy * dz
        elif not lfc_found:
            cin += buoyancy * dz   # 음수 (에너지 소모)

        T_p = T_p_new
        p_p = p_mid

    return max(0.0, cape), min(0.0, cin)


def stability_index(
    profile: VerticalProfile,
    T_surface_k: float,
    p_surface_pa: float,
    Td_surface_k: float,
    T_dew_850_k: float = 273.15,
) -> StabilityIndex:
    """
    대기 안정도 지수 종합 계산.
    """
    cape, cin = cape_cin_simple(profile, T_surface_k, p_surface_pa, Td_surface_k)

    # 프로파일에서 500/700/850 hPa 기온 추출
    T_850 = T_surface_k - 5.0   # 근사 (실제 프로파일에서 보간)
    T_700 = T_surface_k - 13.0
    T_500 = T_surface_k - 25.0

    # 프로파일에서 500 hPa 높이 근사 (5.5 km)
    T_parcel_500 = T_surface_k - dry_adiabatic_lapse_rate() * 5_500.0

    li = lifted_index(T_500, T_parcel_500)
    ki = k_index(T_850, T_500, T_dew_850_k, T_700, T_dew_850_k - 3.0)

    return StabilityIndex(
        CAPE_j_kg=round(cape, 1),
        CIN_j_kg=round(cin, 1),
        LI_k=round(li, 2),
        K_index=round(ki, 2),
    )


# ---------------------------------------------------------------------------
# E. 복사 에너지 균형
# ---------------------------------------------------------------------------

def insolation_wm2(
    lat_rad: float,
    day_of_year: int,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    특정 위도·날짜의 일평균 태양 복사량 (W/m²).
    단순 기하 근사 (대기 흡수 무시).
    """
    # 태양 적위 δ (rad)
    declination = planet.obliquity_rad * math.sin(
        2.0 * math.pi * (day_of_year - 80) / 365.0
    )
    cos_zenith = (math.sin(lat_rad) * math.sin(declination)
                  + math.cos(lat_rad) * math.cos(declination))

    # 일평균 — 하루 중 낮 시간 적분 근사
    cos_sunrise = -math.tan(lat_rad) * math.tan(declination)
    if cos_sunrise > 1.0:
        return 0.0    # 극야
    if cos_sunrise < -1.0:
        H = math.pi   # 백야 (24시간 낮)
    else:
        H = math.acos(cos_sunrise)  # 반일조 시간각

    S = planet.solar_constant_wm2
    daily_avg = S / math.pi * (H * math.sin(lat_rad) * math.sin(declination)
                                + math.cos(lat_rad) * math.cos(declination) * math.sin(H))
    return max(0.0, daily_avg)


def outgoing_longwave_radiation_wm2(T_k: float,
                                    emissivity: float = 0.95) -> float:
    """
    지표 방출 장파 복사 OLR = ε·σ·T⁴ (W/m²).
    Stefan-Boltzmann: σ = 5.67e-8 W/(m²·K⁴)
    """
    sigma = 5.670_374e-8
    return emissivity * sigma * T_k**4


def radiative_energy_balance(
    lat_rad: float,
    T_k: float,
    day_of_year: int,
    planet: PlanetConfig = EARTH,
    cloud_fraction: float = 0.5,
) -> float:
    """
    복사 에너지 불균형 R = SW_in − OLR (W/m²).
    양수: 에너지 흡수 (온난화)
    음수: 에너지 방출 (냉각)
    """
    sw_in = insolation_wm2(lat_rad, day_of_year, planet)
    sw_absorbed = sw_in * (1.0 - planet.albedo) * (1.0 - 0.3 * cloud_fraction)
    olr = outgoing_longwave_radiation_wm2(T_k)
    greenhouse_factor = 0.38   # 지구 대기 온실 효과 (지구 기본값)
    olr_eff = olr * (1.0 - greenhouse_factor)
    return sw_absorbed - olr_eff


def equilibrium_temperature_k(
    lat_rad: float,
    day_of_year: int,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    단순 복사 평형 온도 (K).
    S·(1−A) = σ·T_eq⁴
    """
    S = planet.solar_constant_wm2
    A = planet.albedo
    sigma = 5.670_374e-8
    cos_lat = max(0.0, math.cos(lat_rad))
    flux = S * (1.0 - A) * cos_lat / 4.0
    return (flux / sigma) ** 0.25 if flux > 0 else 0.0
