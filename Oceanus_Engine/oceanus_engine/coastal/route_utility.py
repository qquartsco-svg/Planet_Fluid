"""L5 — 연안·항로 유틸 (격자 보간, 경로 유리도, 얕은 물 위험)."""
from __future__ import annotations

import math
from typing import List, Tuple

from oceanus_engine.contracts.schemas import OceanCellState, CoastalState


def sample_current_bilinear(
    cells: List[List[OceanCellState]],
    ix_fp: float,
    iy_fp: float,
) -> Tuple[float, float, float]:
    """
    (ix_fp, iy_fp) 실수 격자 좌표에서 u,v,η 이중선형 보간.
    """
    ny = len(cells)
    nx = len(cells[0]) if ny else 0
    if nx == 0 or ny == 0:
        return 0.0, 0.0, 0.0
    ix0 = int(math.floor(ix_fp))
    iy0 = int(math.floor(iy_fp))
    ix0 = min(max(ix0, 0), nx - 2)
    iy0 = min(max(iy0, 0), ny - 2)
    fx = ix_fp - ix0
    fy = iy_fp - iy0

    def interp(get):
        v00 = get(cells[iy0][ix0])
        v10 = get(cells[iy0][ix0 + 1])
        v01 = get(cells[iy0 + 1][ix0])
        v11 = get(cells[iy0 + 1][ix0 + 1])
        v0 = v00 * (1 - fx) + v10 * fx
        v1 = v01 * (1 - fx) + v11 * fx
        return v0 * (1 - fy) + v1 * fy

    u = interp(lambda c: c.u_ms)
    v = interp(lambda c: c.v_ms)
    eta = interp(lambda c: c.eta_m)
    return u, v, eta


def route_utility_score(
    u_route_ms: float,
    v_route_ms: float,
    v_desired_east: float,
    v_desired_north: float,
    max_comfort_speed_ms: float = 2.0,
) -> float:
    """
    희망 속도 벡터와 해류 정렬도 + 과도한 횡류 페널티 → [0,1].
    """
    den = max(max_comfort_speed_ms, 1e-6)
    cu = u_route_ms / den
    cv = v_route_ms / den
    du = v_desired_east / den
    dv = v_desired_north / den
    dot = cu * du + cv * dv
    cross = abs(cu * dv - cv * du)
    align = max(0.0, min(1.0, (dot + 1.0) / 2.0))
    penalty = min(1.0, cross)
    return max(0.0, min(1.0, 0.7 * align + 0.3 * (1.0 - penalty)))


def coastal_state_from_depth(
    bathymetry_m: float,
    eta_m: float,
    distance_to_shore_m: float,
) -> CoastalState:
    D = max(bathymetry_m + eta_m, 0.5)
    shallow = max(0.0, 1.0 - min(D / 50.0, 1.0))
    harbor = max(0.0, min(1.0, D / 30.0)) * max(0.0, min(1.0, 1.0 - shallow))
    if distance_to_shore_m < 5_000.0:
        shallow = min(1.0, shallow + 0.2 * (1.0 - distance_to_shore_m / 5_000.0))
    return CoastalState(
        distance_to_shore_m=distance_to_shore_m,
        shallow_water_risk=shallow,
        harbor_access_score=harbor,
    )
