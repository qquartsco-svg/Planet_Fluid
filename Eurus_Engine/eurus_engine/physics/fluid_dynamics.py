"""
Eurus_Engine — 대기 유체역학 (Shallow Water Equations)

구현 방정식:
  얕은 수층 방정식 (Shallow Water Equations, SWE):
    ∂u/∂t + u∂u/∂x + v∂u/∂y − f·v = −g·∂h/∂x + ν∇²u
    ∂v/∂t + u∂v/∂x + v∂v/∂y + f·u = −g·∂h/∂y + ν∇²v
    ∂h/∂t + ∂(hu)/∂x + ∂(hv)/∂y = Q (소스/싱크)

  여기서:
    u, v  : 수평 속도 (m/s)
    h     : 유체층 두께 / 지위 고도 (m)
    f     : 코리올리 매개변수 (s⁻¹) = 2Ω·sin(φ)
    g     : 중력 가속도 (m/s²)
    ν     : 동역학 점성 계수 (m²/s) — 수치 확산
    Q     : 가열·냉각 소스 항

  수치 기법:
    - Euler 전진 (단순 1차) → 안정성 조건 CFL < 1
    - Runge-Kutta 4차 (정밀 모드)

  단위: SI 전용
"""

from __future__ import annotations

import math
from typing import List, Tuple

import dataclasses

from eurus_engine.contracts.schemas import FluidCell, PlanetConfig, EARTH


# ---------------------------------------------------------------------------
# 코리올리 함수
# ---------------------------------------------------------------------------

def coriolis_parameter(lat_rad: float, planet: PlanetConfig = EARTH) -> float:
    """
    코리올리 매개변수 f = 2Ω·sin(φ).

    Parameters
    ----------
    lat_rad : 위도 (rad), −π/2 (남극) ~ +π/2 (북극)
    planet  : 행성 설정

    Returns
    -------
    f (s⁻¹)
    """
    return 2.0 * planet.rotation_rate_rads * math.sin(lat_rad)


def beta_parameter(lat_rad: float, planet: PlanetConfig = EARTH) -> float:
    """
    β 매개변수 = df/dy = 2Ω·cos(φ)/R (m⁻¹·s⁻¹).
    로스비 파 전파 속도에 사용.
    """
    return (2.0 * planet.rotation_rate_rads * math.cos(lat_rad)
            / planet.radius_m)


def rossby_number(U_ms: float, L_m: float, lat_rad: float,
                  planet: PlanetConfig = EARTH) -> float:
    """
    로스비 수 Ro = U / (f·L).

    Ro << 1 : 지균류 지배 (대규모 대기 순환)
    Ro >> 1 : 비지균 (소규모 대류)
    """
    f = coriolis_parameter(lat_rad, planet)
    if abs(f) < 1e-12 or L_m <= 0:
        return float("inf")
    return abs(U_ms) / (abs(f) * L_m)


def geostrophic_wind(
    dp_dx_pa_m: float,
    dp_dy_pa_m: float,
    density_kg_m3: float,
    lat_rad: float,
    planet: PlanetConfig = EARTH,
) -> Tuple[float, float]:
    """
    지균풍 계산.
    u_g = −(1/ρf)·∂p/∂y
    v_g = +(1/ρf)·∂p/∂x

    Returns (u_g, v_g) in m/s.
    """
    f = coriolis_parameter(lat_rad, planet)
    if abs(f) < 1e-12 or density_kg_m3 <= 0:
        return 0.0, 0.0
    u_g = -(1.0 / (density_kg_m3 * f)) * dp_dy_pa_m
    v_g =  (1.0 / (density_kg_m3 * f)) * dp_dx_pa_m
    return u_g, v_g


# ---------------------------------------------------------------------------
# 와도 (Vorticity)
# ---------------------------------------------------------------------------

def relative_vorticity(
    du_dy: float,   # ∂u/∂y (s⁻¹)
    dv_dx: float,   # ∂v/∂x (s⁻¹)
) -> float:
    """
    상대 와도 ζ = ∂v/∂x − ∂u/∂y (s⁻¹).
    양수: 반시계 (북반구 저기압)
    """
    return dv_dx - du_dy


def absolute_vorticity(
    zeta: float,
    lat_rad: float,
    planet: PlanetConfig = EARTH,
) -> float:
    """절대 와도 η = ζ + f."""
    return zeta + coriolis_parameter(lat_rad, planet)


def potential_vorticity(
    eta: float,    # 절대 와도
    h_m: float,    # 유체층 두께
) -> float:
    """
    위치 와도 PV = η / h (m⁻¹·s⁻¹).
    보존량 (단열·마찰 없음).
    """
    return eta / h_m if h_m > 0 else 0.0


# ---------------------------------------------------------------------------
# 발산 (Divergence)
# ---------------------------------------------------------------------------

def divergence(
    du_dx: float,   # ∂u/∂x (s⁻¹)
    dv_dy: float,   # ∂v/∂y (s⁻¹)
) -> float:
    """수평 발산 D = ∂u/∂x + ∂v/∂y (s⁻¹)."""
    return du_dx + dv_dy


# ---------------------------------------------------------------------------
# SWE 경향 (Tendency) — 한 격자점에서 du/dt, dv/dt, dh/dt 계산
# ---------------------------------------------------------------------------

def swe_tendency(
    u: float, v: float, h: float,
    dudx: float, dudy: float,
    dvdx: float, dvdy: float,
    dhdx: float, dhdy: float,
    f: float,
    g: float,
    nu: float = 1_000.0,    # 수치 점성 (m²/s)
    lap_u: float = 0.0,     # ∇²u 라플라시안
    lap_v: float = 0.0,     # ∇²v
    Q_h: float = 0.0,       # 두께 소스 항 (가열/냉각)
) -> Tuple[float, float, float]:
    """
    얕은 수층 방정식 경향 계산.

    Returns (du/dt, dv/dt, dh/dt)
    """
    # 이류 항 (advection)
    adv_u = -(u * dudx + v * dudy)
    adv_v = -(u * dvdx + v * dvdy)
    adv_h = -(u * dhdx + v * dhdy + h * (dudx + dvdy))

    # 기압 경도력 + 코리올리
    pgf_u = -g * dhdx + f * v
    pgf_v = -g * dhdy - f * u

    # 수치 점성 (확산)
    diff_u = nu * lap_u
    diff_v = nu * lap_v

    du_dt = adv_u + pgf_u + diff_u
    dv_dt = adv_v + pgf_v + diff_v
    dh_dt = adv_h + Q_h

    return du_dt, dv_dt, dh_dt


# ---------------------------------------------------------------------------
# 격자 미분 (중앙 차분)
# ---------------------------------------------------------------------------

def central_diff(
    f_plus: float,
    f_minus: float,
    delta: float,
) -> float:
    """중앙 차분: (f[i+1] − f[i−1]) / (2·Δ)."""
    return (f_plus - f_minus) / (2.0 * delta + 1e-15)


def laplacian_2d(
    f_center: float,
    f_east: float, f_west: float,
    f_north: float, f_south: float,
    dx: float, dy: float,
) -> float:
    """
    2D 라플라시안 ∇²f ≈ (f_E−2f_C+f_W)/dx² + (f_N−2f_C+f_S)/dy²
    """
    d2fdx2 = (f_east - 2.0 * f_center + f_west) / (dx**2 + 1e-30)
    d2fdy2 = (f_north - 2.0 * f_center + f_south) / (dy**2 + 1e-30)
    return d2fdx2 + d2fdy2


# ---------------------------------------------------------------------------
# 단일 격자점 SWE 스텝 (Euler)
# ---------------------------------------------------------------------------

def step_cell_euler(
    cell: FluidCell,
    east:  FluidCell,
    west:  FluidCell,
    north: FluidCell,
    south: FluidCell,
    dt_s:  float,
    dx_m:  float,
    dy_m:  float,
    planet: PlanetConfig = EARTH,
    nu: float = 1_000.0,
    heating_wm2: float = 0.0,    # 복사 가열 (W/m²)
) -> FluidCell:
    """
    얕은 수층 방정식 Euler 전진 스텝 — 단일 격자 셀 갱신.

    CFL 안정 조건 검사 포함.
    dt_s 가 너무 크면 자동으로 CFL에 맞게 축소.
    """
    g = planet.gravity_ms2
    f = coriolis_parameter(cell.φ_rad, planet)

    # 속도 중앙 차분
    dudx = central_diff(east.u_ms,  west.u_ms,  dx_m)
    dudy = central_diff(north.u_ms, south.u_ms, dy_m)
    dvdx = central_diff(east.v_ms,  west.v_ms,  dx_m)
    dvdy = central_diff(north.v_ms, south.v_ms, dy_m)
    dhdx = central_diff(east.h_m,   west.h_m,   dx_m)
    dhdy = central_diff(north.h_m,  south.h_m,  dy_m)

    # 라플라시안
    lap_u = laplacian_2d(cell.u_ms, east.u_ms, west.u_ms,
                         north.u_ms, south.u_ms, dx_m, dy_m)
    lap_v = laplacian_2d(cell.v_ms, east.v_ms, west.v_ms,
                         north.v_ms, south.v_ms, dx_m, dy_m)

    # 가열 → h 소스 (단순 근사: Q = heating / (ρ·g·H))
    rho = cell.density_kg_m3
    Q_h = heating_wm2 / (rho * g * cell.h_m + 1e-10)

    du_dt, dv_dt, dh_dt = swe_tendency(
        cell.u_ms, cell.v_ms, cell.h_m,
        dudx, dudy, dvdx, dvdy, dhdx, dhdy,
        f, g, nu,
        lap_u=lap_u, lap_v=lap_v,
        Q_h=Q_h,
    )

    # CFL 검사: c_g = sqrt(g·h) (중력파 위상 속도)
    c_g = math.sqrt(g * max(cell.h_m, 1.0))
    cfl_limit = 0.8 * min(dx_m, dy_m) / (c_g + cell.speed_ms + 1e-9)
    dt_eff = min(dt_s, cfl_limit)

    new_u = cell.u_ms + du_dt * dt_eff
    new_v = cell.v_ms + dv_dt * dt_eff
    new_h = max(cell.h_m + dh_dt * dt_eff, 0.1)  # h > 0 보장

    # 온도 단열 냉각 (위치 에너지↔운동에너지 교환 근사)
    new_T = cell.T_k - planet.dry_adiabatic_lapse_rate_k_m * (new_h - cell.h_m) * 0.01

    return dataclasses.replace(
        cell,
        u_ms=new_u,
        v_ms=new_v,
        h_m=new_h,
        T_k=max(new_T, 10.0),
    )


# ---------------------------------------------------------------------------
# 중력파 위상 속도 (분산 관계)
# ---------------------------------------------------------------------------

def gravity_wave_speed(h_m: float, planet: PlanetConfig = EARTH) -> float:
    """c = sqrt(g·H) — 천수파 위상 속도 (m/s)."""
    return math.sqrt(planet.gravity_ms2 * max(h_m, 0.0))


def rossby_wave_speed(
    k: float,          # 동서 파수 (rad/m)
    beta: float,       # β 매개변수 (m⁻¹·s⁻¹)
    u_mean: float = 0.0,  # 평균 동서류 (m/s)
) -> float:
    """
    로스비 파 위상 속도 c_x = u_mean − β/k² (m/s).
    서쪽으로 전파하는 행성파.
    """
    if abs(k) < 1e-15:
        return -float("inf")
    return u_mean - beta / (k**2)


# ---------------------------------------------------------------------------
# 에너지 계산
# ---------------------------------------------------------------------------

def kinetic_energy_density(
    u_ms: float,
    v_ms: float,
    density_kg_m3: float,
) -> float:
    """운동 에너지 밀도 KE = ½ρ(u²+v²) (J/m³)."""
    return 0.5 * density_kg_m3 * (u_ms**2 + v_ms**2)


def available_potential_energy(
    h_m: float,
    h_mean_m: float,
    planet: PlanetConfig = EARTH,
) -> float:
    """
    유효 위치 에너지 APE = ½g(h−H)² (J/m²).
    h_mean_m: 기준 층 두께 H
    """
    return 0.5 * planet.gravity_ms2 * (h_m - h_mean_m)**2
