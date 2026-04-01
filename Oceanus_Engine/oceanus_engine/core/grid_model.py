"""
2D 해양 격자 — MVP-1 SWE + L3 조석 강제 + L2 밀도 동기화 훅.
"""
from __future__ import annotations

import dataclasses
import math
from typing import List, Tuple

from oceanus_engine.contracts.schemas import (
    OceanCellState,
    CurrentFieldState,
    OceanPlanetConfig,
    EARTH_OCEAN,
)
from oceanus_engine.physics.shallow_water import (
    step_ocean_cell_euler,
    wind_stress_from_wind_10m,
)
from oceanus_engine.physics.thermohaline import apply_thermohaline_to_cell
from oceanus_engine.physics.tides import (
    harmonic_tide_eta_derivative_m_per_s,
    tide_state_for_cell,
)
from oceanus_engine.physics.plate_hooks import PlateHookRegistry
from oceanus_engine.physics.tectonic_resonance import scan_tectonic_resonance_and_emit


class OceanGridModel:
    """
    nx×ny 격자. 내부 셀만 SWE 스텝; 가장자리는 이웃을 그대로 사용(경계 조건 단순화).
    """

    def __init__(
        self,
        nx: int,
        ny: int,
        dx_m: float,
        dy_m: float,
        planet: OceanPlanetConfig = EARTH_OCEAN,
        default_bathymetry_m: float = 4_000.0,
        center_lat_rad: float = 0.523599,  # ~30°N
        center_lon_rad: float = 0.0,
    ) -> None:
        self.nx = nx
        self.ny = ny
        self.dx_m = dx_m
        self.dy_m = dy_m
        self.planet = planet
        self.t_s = 0.0
        self._wind_u = 0.0
        self._wind_v = 0.0
        self.tide_coupling: float = 1.0
        self.tidal_vel_coupling: float = 0.3
        self.plate_hooks = PlateHookRegistry()
        cos_ref = max(abs(math.cos(center_lat_rad)), 0.2)
        dlat = dy_m / planet.radius_m
        dlon = dx_m / (planet.radius_m * cos_ref)

        self._cells: List[List[OceanCellState]] = []
        for iy in range(ny):
            row: List[OceanCellState] = []
            for ix in range(nx):
                phi = center_lat_rad + (iy - ny // 2) * dlat
                lam = center_lon_rad + (ix - nx // 2) * dlon
                row.append(
                    OceanCellState(
                        λ_rad=lam,
                        φ_rad=phi,
                        bathymetry_m=default_bathymetry_m,
                    )
                )
            self._cells.append(row)

    def cell(self, ix: int, iy: int) -> OceanCellState:
        return self._cells[iy][ix]

    def set_bathymetry(self, iy: int, ix: int, H_m: float) -> None:
        c = self._cells[iy][ix]
        self._cells[iy][ix] = dataclasses.replace(c, bathymetry_m=H_m)

    def set_wind_field(self, wind_u_ms: float, wind_v_ms: float) -> None:
        self._wind_u = wind_u_ms
        self._wind_v = wind_v_ms

    def _neighbor(
        self, ix: int, iy: int, di: int, dj: int
    ) -> OceanCellState:
        j = min(max(iy + dj, 0), self.ny - 1)
        i = min(max(ix + di, 0), self.nx - 1)
        return self._cells[j][i]

    def step(
        self,
        dt_s: float,
        apply_thermohaline: bool = True,
        apply_tidal_source: bool = True,
        M2_amp_m: float = 0.5,
        S2_amp_m: float = 0.25,
        K1_amp_m: float = 0.15,
        O1_amp_m: float = 0.10,
    ) -> None:
        new_grid: List[List[OceanCellState]] = copy_cells(self._cells)
        for iy in range(1, self.ny - 1):
            for ix in range(1, self.nx - 1):
                c = self._cells[iy][ix]
                e = self._neighbor(ix, iy, 1, 0)
                w = self._neighbor(ix, iy, -1, 0)
                n = self._neighbor(ix, iy, 0, 1)
                s = self._neighbor(ix, iy, 0, -1)
                q_eta = 0.0
                if apply_tidal_source:
                    q_eta = self.tide_coupling * harmonic_tide_eta_derivative_m_per_s(
                        self.t_s,
                        c.λ_rad,
                        c.φ_rad,
                        M2_amp_m,
                        S2_amp_m,
                        K1_amp_m,
                        O1_amp_m,
                    )
                nc = step_ocean_cell_euler(
                    c,
                    e,
                    w,
                    n,
                    s,
                    dt_s,
                    self.dx_m,
                    self.dy_m,
                    planet=self.planet,
                    wind_u_ms=self._wind_u,
                    wind_v_ms=self._wind_v,
                    tide_eta_source_per_s=q_eta,
                )
                if apply_thermohaline:
                    nc = apply_thermohaline_to_cell(nc)
                ts = tide_state_for_cell(
                    self.t_s,
                    c.λ_rad,
                    c.φ_rad,
                    self.planet,
                    M2_amp_m,
                    S2_amp_m,
                    K1_amp_m,
                    O1_amp_m,
                )
                nc = dataclasses.replace(
                    nc,
                    u_ms=nc.u_ms + self.tidal_vel_coupling * ts.u_tidal_ms,
                    v_ms=nc.v_ms + self.tidal_vel_coupling * ts.v_tidal_ms,
                )
                new_grid[iy][ix] = nc
        self._cells = new_grid
        self.t_s += dt_s

    def current_field_state(self) -> CurrentFieldState:
        total = 0.0
        mx = 0.0
        meta = 0.0
        n = 0
        for row in self._cells:
            for c in row:
                sp = c.speed_ms
                total += sp
                mx = max(mx, sp)
                meta += c.eta_m
                n += 1
        mean_sp = total / n if n else 0.0
        mean_eta = meta / n if n else 0.0
        tx, ty = wind_stress_from_wind_10m(
            self._wind_u, self._wind_v, rho_air=self.planet.rho_air_ref_kg_m3
        )
        return CurrentFieldState(
            t_s=self.t_s,
            nx=self.nx,
            ny=self.ny,
            dx_m=self.dx_m,
            dy_m=self.dy_m,
            mean_speed_ms=mean_sp,
            max_speed_ms=mx,
            mean_eta_m=mean_eta,
            wind_stress_east_nm2=tx,
            wind_stress_north_nm2=ty,
        )

    def all_cells(self) -> Tuple[OceanCellState, ...]:
        out: List[OceanCellState] = []
        for row in self._cells:
            out.extend(row)
        return tuple(out)

    def scan_tectonic_resonance(
        self,
        signal,
        *,
        sample_rate_hz: float,
        natural_freq_hz: float,
        boundary_id: str = "global_boundary",
        magnitude_scale: float = 7.0,
    ):
        return scan_tectonic_resonance_and_emit(
            signal,
            sample_rate_hz=sample_rate_hz,
            natural_freq_hz=natural_freq_hz,
            boundary_id=boundary_id,
            t_s=self.t_s,
            registry=self.plate_hooks,
            magnitude_scale=magnitude_scale,
        )


def copy_cells(grid: List[List[OceanCellState]]) -> List[List[OceanCellState]]:
    return [[c for c in row] for row in grid]
