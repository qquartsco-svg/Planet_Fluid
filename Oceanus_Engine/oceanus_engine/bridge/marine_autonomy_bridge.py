"""
Oceanus → Marine_Autonomy bridge.

- 세계(동-북) 해류를 선체 surge/sway로 투영.
- route utility 엔진에서 바로 소비 가능한 "current correction" 패킷 제공.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple


def world_en_to_vessel_frame(
    u_east_ms: float,
    v_north_ms: float,
    psi_rad: float,
) -> Tuple[float, float]:
    """
    선수 방위 psi (북 0, 시계 +) 기준 surge/sway 성분.
    surge ≈ 동쪽 유속을 선수축에 투영, sway ≈ 횡방향.
    """
    c = math.cos(psi_rad)
    s = math.sin(psi_rad)
    surge = u_east_ms * s + v_north_ms * c
    sway = u_east_ms * c - v_north_ms * s
    return surge, sway


def marine_perception_dict_from_ocean(
    u_east_ms: float,
    v_north_ms: float,
    psi_rad: float,
    wind_speed_ms: float = 0.0,
    wind_dir_rad: float = 0.0,
    visibility_m: float = 1e6,
    depth_m: float = 100.0,
    contacts: tuple = (),
) -> Dict[str, Any]:
    cu, cv = world_en_to_vessel_frame(u_east_ms, v_north_ms, psi_rad)
    return {
        "contacts": contacts,
        "wind_speed_ms": wind_speed_ms,
        "wind_dir_rad": wind_dir_rad,
        "current_u_ms": cu,
        "current_v_ms": cv,
        "visibility_m": visibility_m,
        "depth_m": depth_m,
    }


def _norm2(x: float, y: float) -> float:
    return math.sqrt(x * x + y * y)


def route_current_correction_dict(
    u_east_ms: float,
    v_north_ms: float,
    desired_ground_east_ms: float,
    desired_ground_north_ms: float,
) -> Dict[str, float]:
    """
    지상 기준 목표 속도(vg_desired)와 해류(vc)로부터 수상체 상대 목표(vw_cmd)를 계산.

    vg = vw + vc  =>  vw_cmd = vg_desired - vc
    """
    vw_e = desired_ground_east_ms - u_east_ms
    vw_n = desired_ground_north_ms - v_north_ms
    vg_mag = _norm2(desired_ground_east_ms, desired_ground_north_ms)
    vc_mag = _norm2(u_east_ms, v_north_ms)
    vw_mag = _norm2(vw_e, vw_n)
    return {
        "desired_ground_east_ms": float(desired_ground_east_ms),
        "desired_ground_north_ms": float(desired_ground_north_ms),
        "desired_ground_speed_ms": float(vg_mag),
        "water_relative_cmd_east_ms": float(vw_e),
        "water_relative_cmd_north_ms": float(vw_n),
        "water_relative_cmd_speed_ms": float(vw_mag),
        "current_world_east_ms": float(u_east_ms),
        "current_world_north_ms": float(v_north_ms),
        "current_speed_ms": float(vc_mag),
    }


def marine_route_bridge_packet_from_ocean(
    u_east_ms: float,
    v_north_ms: float,
    psi_rad: float,
    desired_ground_east_ms: float,
    desired_ground_north_ms: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Oceanus → Marine 전달 표준 패킷(v1).
    """
    return {
        "contract_version": "ocean-marine-bridge.v1",
        "marine_perception": marine_perception_dict_from_ocean(
            u_east_ms, v_north_ms, psi_rad, **kwargs
        ),
        "current_sample_world": {
            "u_east_ms": float(u_east_ms),
            "v_north_ms": float(v_north_ms),
            "speed_ms": float(_norm2(u_east_ms, v_north_ms)),
        },
        "route_correction": route_current_correction_dict(
            u_east_ms,
            v_north_ms,
            desired_ground_east_ms,
            desired_ground_north_ms,
        ),
    }


def sample_current_for_vessel(
    cells,
    ix_fp: float,
    iy_fp: float,
    psi_rad: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    from oceanus_engine.coastal.route_utility import sample_current_bilinear

    u, v, _eta = sample_current_bilinear(cells, ix_fp, iy_fp)
    return marine_perception_dict_from_ocean(u, v, psi_rad, **kwargs)
