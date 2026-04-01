"""
Eurus_Engine — 대기 수직 프로파일 (행성 독립)

기능:
  - 표준 대기 근사 (등온·등온 기온 감율 레이어)
  - 임의 PlanetConfig로 수직 구조 생성
  - 압력·밀도·기온 프로파일 (정수압 방정식)
  - 리프팅 고도 (LCL) 계산
"""

from __future__ import annotations
import math
from typing import List, Tuple
from eurus_engine.contracts.schemas import PlanetConfig, EARTH, VerticalProfile

_Rd = 287.058

def hydrostatic_pressure(p0_pa: float, T_k: float, dz_m: float,
                          g: float = 9.80665, Rd: float = _Rd) -> float:
    """정수압 방정식: p(z+dz) = p(z) · exp(−g·dz / (Rd·T))"""
    return p0_pa * math.exp(-g * dz_m / (Rd * max(T_k, 1.0)))

def density_from_ideal_gas(p_pa: float, T_k: float,
                            Rd: float = _Rd) -> float:
    """이상기체 밀도 ρ = p/(Rd·T) (kg/m³)."""
    return p_pa / (Rd * max(T_k, 1.0))

def standard_atmosphere_profile(
    planet: PlanetConfig = EARTH,
    z_top_m: float = 50_000.0,
    dz_m: float = 500.0,
    T_surface_k: float = 288.15,
) -> VerticalProfile:
    """
    행성 표준 대기 수직 프로파일 생성.
    대류권: 건조 단열 감율로 냉각
    성층권 이상: 등온 근사
    """
    g = planet.gravity_ms2
    Rd = planet.r_specific_j_kgk
    gamma = planet.dry_adiabatic_lapse_rate_k_m  # K/m
    tropopause_m = planet.scale_height_m * 1.5   # 대략 대류권 두께 근사

    altitudes: List[float] = []
    temps: List[float] = []
    pressures: List[float] = []
    densities: List[float] = []

    z = 0.0
    T = T_surface_k
    p = planet.surface_pressure_pa

    while z <= z_top_m:
        altitudes.append(z)
        temps.append(T)
        pressures.append(p)
        densities.append(density_from_ideal_gas(p, T, Rd))

        # 다음 레이어
        if z < tropopause_m:
            T_next = max(T - gamma * dz_m, 160.0)  # 대류권
        else:
            T_next = T  # 성층권 등온 근사

        p_next = hydrostatic_pressure(p, 0.5*(T + T_next), dz_m, g, Rd)
        T = T_next
        p = p_next
        z += dz_m

    return VerticalProfile(
        altitudes_m=tuple(altitudes),
        temperatures_k=tuple(temps),
        pressures_pa=tuple(pressures),
        densities_kg_m3=tuple(densities),
    )

def lcl_altitude_m(T_k: float, T_dew_k: float) -> float:
    """
    리프팅 응결 고도 LCL (m).
    Bolton (1980) 근사: LCL ≈ 125 · (T − Td)
    """
    return max(0.0, 125.0 * (T_k - T_dew_k))

def interpolate_profile_at_altitude(profile: VerticalProfile, z_m: float
                                     ) -> Tuple[float, float, float]:
    """
    프로파일에서 특정 고도의 (T, p, rho) 선형 보간.
    Returns (T_k, p_pa, rho_kg_m3)
    """
    alts = profile.altitudes_m
    if not alts:
        return 288.15, 101325.0, 1.225
    if z_m <= alts[0]:
        return profile.temperatures_k[0], profile.pressures_pa[0], profile.densities_kg_m3[0]
    if z_m >= alts[-1]:
        return profile.temperatures_k[-1], profile.pressures_pa[-1], profile.densities_kg_m3[-1]

    for i in range(1, len(alts)):
        if alts[i] >= z_m:
            frac = (z_m - alts[i-1]) / max(alts[i] - alts[i-1], 1.0)
            T = profile.temperatures_k[i-1] + frac*(profile.temperatures_k[i]-profile.temperatures_k[i-1])
            p = profile.pressures_pa[i-1] + frac*(profile.pressures_pa[i]-profile.pressures_pa[i-1])
            rho = profile.densities_kg_m3[i-1] + frac*(profile.densities_kg_m3[i]-profile.densities_kg_m3[i-1])
            return T, p, rho
    return profile.temperatures_k[-1], profile.pressures_pa[-1], profile.densities_kg_m3[-1]

def scale_height(T_k: float, planet: PlanetConfig = EARTH) -> float:
    """대기 규모 높이 H = Rd·T/g (m)."""
    return planet.r_specific_j_kgk * T_k / max(planet.gravity_ms2, 1e-9)

def brunt_vaisala_frequency(T_k: float, dTdz: float,
                             planet: PlanetConfig = EARTH) -> float:
    """
    브런트-바이살라 진동수 N² = (g/T)·(dT/dz + Γd).
    N² > 0: 안정 (진동)
    N² < 0: 불안정 (대류)
    """
    gamma_d = planet.dry_adiabatic_lapse_rate_k_m
    N2 = (planet.gravity_ms2 / max(T_k, 1.0)) * (dTdz + gamma_d)
    return N2
