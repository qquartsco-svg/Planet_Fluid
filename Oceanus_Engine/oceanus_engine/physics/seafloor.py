"""L4 — 해저 경사·분류(해령·해구·대륙붕 프록시)."""
from __future__ import annotations

from oceanus_engine.contracts.schemas import SeafloorState, SeafloorClass


def classify_seafloor(depth_m: float, slope_mag: float) -> SeafloorClass:
    if depth_m < 200.0:
        return SeafloorClass.CONTINENTAL_SHELF
    if depth_m < 2000.0 and slope_mag > 0.02:
        return SeafloorClass.SLOPE
    if depth_m > 6_000.0 and slope_mag > 0.05:
        return SeafloorClass.TRENCH
    if slope_mag < 0.005 and 2_000.0 < depth_m < 5_500.0:
        return SeafloorClass.ABYSSAL
    if slope_mag > 0.03 and depth_m > 1_000.0:
        return SeafloorClass.RIDGE
    if depth_m < 3_500.0 and slope_mag > 0.04:
        return SeafloorClass.SEAMOUNT
    return SeafloorClass.ABYSSAL


def seafloor_state_from_bathymetry_grid(
    H_center: float,
    H_east: float,
    H_west: float,
    H_north: float,
    H_south: float,
    dx_m: float,
    dy_m: float,
) -> SeafloorState:
    sx = (H_east - H_west) / (2.0 * dx_m + 1e-9)
    sy = (H_north - H_south) / (2.0 * dy_m + 1e-9)
    slope_mag = (sx**2 + sy**2) ** 0.5
    return SeafloorState(
        depth_m=H_center,
        slope_x=sx,
        slope_y=sy,
        seafloor_class=classify_seafloor(H_center, slope_mag),
    )
