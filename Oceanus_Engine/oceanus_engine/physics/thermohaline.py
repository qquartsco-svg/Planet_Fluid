"""
L2 — 열염·밀도 (단순 선형 EOS) 및 박스 평균 ThermohalineState.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from oceanus_engine.contracts.schemas import OceanCellState, ThermohalineState


def density_linear_eos(
    T_k: float,
    S_psu: float,
    T_ref_k: float = 288.15,
    S_ref_psu: float = 35.0,
    alpha_k: float = 2.0e-4,
    beta_s: float = 7.6e-4,
    rho0: float = 1025.0,
) -> float:
    """선형 EOS: ρ = ρ0(1 − α(T−Tref) + β(S−Sref))."""
    return rho0 * (1.0 - alpha_k * (T_k - T_ref_k) + beta_s * (S_psu - S_ref_psu))


def overturning_tendency_proxy(
    rho_surface: float,
    rho_deep: float,
) -> float:
    """
    표층이 심층보다 무거우면 침강 경향. 무차원 스칼라 (대략 정규화).
    """
    dr = rho_surface - rho_deep
    return max(0.0, dr / 1025.0)


def aggregate_thermohaline(cells: Iterable[OceanCellState]) -> ThermohalineState:
    lst = list(cells)
    if not lst:
        return ThermohalineState()
    n = len(lst)
    t_mean = sum(c.T_k for c in lst) / n
    s_mean = sum(c.S_psu for c in lst) / n
    r_mean = sum(c.rho_kg_m3 for c in lst) / n
    # 표층/심층 프록시: 얕은 H vs 깊은 H
    shallow = [c for c in lst if c.bathymetry_m < 200.0]
    deep = [c for c in lst if c.bathymetry_m >= 200.0]
    rs = sum(c.rho_kg_m3 for c in shallow) / len(shallow) if shallow else r_mean
    rd = sum(c.rho_kg_m3 for c in deep) / len(deep) if deep else r_mean
    ov = overturning_tendency_proxy(rs, rd)
    return ThermohalineState(
        T_k_mean=t_mean,
        S_psu_mean=s_mean,
        rho_kg_m3_mean=r_mean,
        overturning_tendency=ov,
    )


def apply_thermohaline_to_cell(cell: OceanCellState) -> OceanCellState:
    """셀 밀도 갱신 (T,S 고정 시 한 스텝 밀도 동기화)."""
    rho = density_linear_eos(cell.T_k, cell.S_psu)
    return replace(cell, rho_kg_m3=rho)
