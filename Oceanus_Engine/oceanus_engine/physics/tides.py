"""
L3 — 조석: 달·태양 반일·일주 조화 + 평형 조위 프록시.

천체각은 단순화(균일 회전·원궤도); 실무 정밀도는 외부 천력역학(ephemeris)로 교체 가능.
별자리/황경은 astronomical_phase_rad 슬롯으로 확장.
"""
from __future__ import annotations

import math
from typing import Tuple

from oceanus_engine.contracts.schemas import TideState, OceanPlanetConfig, EARTH_OCEAN

# 주요 조화 각속도 (rad/s) — M2, S2, K1, O1 근사
_M2 = 2.0 * math.pi / (12.4206012 * 3600.0)
_S2 = 2.0 * math.pi / (12.0 * 3600.0)
_K1 = 2.0 * math.pi / (23.934 * 3600.0)
_O1 = 2.0 * math.pi / (25.819 * 3600.0)


def lunar_solar_beat_phase_rad(t_s: float) -> float:
    """
    달-태양 시차 위상 프록시 (합삭·망 주기 ~29.53일의 저주파 변조).
    """
    T_synodic = 29.530588853 * 86400.0
    return 2.0 * math.pi * (t_s / T_synodic)


def equilibrium_semidiurnal_envelope(lat_rad: float) -> float:
    """cos²φ 형태 반일주 평형 진폭 봉투 (정규화)."""
    return max(0.0, math.cos(lat_rad) ** 2)


def equilibrium_diurnal_envelope(lat_rad: float) -> float:
    """sin(2φ) 형태 일주 분량 봉투 근사."""
    return abs(math.sin(2.0 * lat_rad))


def harmonic_tide_eta_derivative_m_per_s(
    t_s: float,
    lon_rad: float,
    lat_rad: float,
    M2_amp_m: float,
    S2_amp_m: float,
    K1_amp_m: float,
    O1_amp_m: float,
    phase_offset_rad: float = 0.0,
) -> float:
    """dη/dt (합성 조화의 시간 미분). 조석 강제항(연속식 소스)에 사용."""
    astro = lunar_solar_beat_phase_rad(t_s)
    env_sd = equilibrium_semidiurnal_envelope(lat_rad)
    env_d = equilibrium_diurnal_envelope(lat_rad)
    d_m2 = -M2_amp_m * env_sd * _M2 * math.sin(_M2 * t_s + 2.0 * lon_rad + phase_offset_rad)
    d_s2 = -S2_amp_m * env_sd * _S2 * math.sin(_S2 * t_s + 2.0 * lon_rad + astro * 0.1)
    d_k1 = -K1_amp_m * env_d * _K1 * math.sin(_K1 * t_s + lon_rad - astro)
    d_o1 = -O1_amp_m * env_d * _O1 * math.sin(_O1 * t_s + lon_rad + astro * 0.05)
    return d_m2 + d_s2 + d_k1 + d_o1


def harmonic_tide_eta_m(
    t_s: float,
    lon_rad: float,
    lat_rad: float,
    M2_amp_m: float,
    S2_amp_m: float,
    K1_amp_m: float,
    O1_amp_m: float,
    phase_offset_rad: float = 0.0,
) -> float:
    """
    위도·경도·시간에 따른 조위 고도 합성(여러 조화 선형 중첩).
    astronomical_phase: 망·합삭 변조.
    """
    astro = lunar_solar_beat_phase_rad(t_s)
    env_sd = equilibrium_semidiurnal_envelope(lat_rad)
    env_d = equilibrium_diurnal_envelope(lat_rad)

    eta_m2 = M2_amp_m * env_sd * math.cos(_M2 * t_s + 2.0 * lon_rad + phase_offset_rad)
    eta_s2 = S2_amp_m * env_sd * math.cos(_S2 * t_s + 2.0 * lon_rad + astro * 0.1)
    eta_k1 = K1_amp_m * env_d * math.cos(_K1 * t_s + lon_rad - astro)
    eta_o1 = O1_amp_m * env_d * math.cos(_O1 * t_s + lon_rad + astro * 0.05)
    return eta_m2 + eta_s2 + eta_k1 + eta_o1


def tidal_current_geostrophic_proxy(
    detadx: float,
    detady: float,
    f: float,
    g: float,
    eps: float = 1e-6,
) -> Tuple[float, float]:
    """
    f u = -g ∂η/∂y, f v = g ∂η/∂x 근사로 조류 성분 (적도 근처는 eps로 클램프).
    """
    denom = f if abs(f) > eps else eps
    u = -g * detady / denom
    v = g * detadx / denom
    return u, v


def tide_state_for_cell(
    t_s: float,
    lon_rad: float,
    lat_rad: float,
    planet: OceanPlanetConfig = EARTH_OCEAN,
    M2_amp_m: float = 0.5,
    S2_amp_m: float = 0.25,
    K1_amp_m: float = 0.15,
    O1_amp_m: float = 0.10,
) -> TideState:
    astro = lunar_solar_beat_phase_rad(t_s)
    eta_eq = harmonic_tide_eta_m(
        t_s, lon_rad, lat_rad, M2_amp_m, S2_amp_m, K1_amp_m, O1_amp_m
    )
    # 평형 경사 근사: 소구역에서 ∂η/∂x ~ −(η/L) 스케일 — 여기서는 위상 기반 미세 항
    detadx = -(M2_amp_m * equilibrium_semidiurnal_envelope(lat_rad) * _M2
               * math.sin(_M2 * t_s + 2.0 * lon_rad)) / (planet.radius_m * math.cos(lat_rad) + 1e-6)
    detady = 0.0
    from oceanus_engine.physics.coriolis import coriolis_parameter

    f = coriolis_parameter(lat_rad, planet)
    u_t, v_t = tidal_current_geostrophic_proxy(detadx, detady, f, planet.gravity_ms2)
    return TideState(
        t_s=t_s,
        eta_equilibrium_m=eta_eq,
        u_tidal_ms=u_t,
        v_tidal_ms=v_t,
        M2_amp_m=M2_amp_m,
        S2_amp_m=S2_amp_m,
        K1_amp_m=K1_amp_m,
        O1_amp_m=O1_amp_m,
        astronomical_phase_rad=astro,
    )
