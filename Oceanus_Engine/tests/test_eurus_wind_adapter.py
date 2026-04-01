import math
from types import SimpleNamespace

from oceanus_engine import OceanGridModel
from oceanus_engine.bridge.eurus_wind_adapter import (
    wind_10m_ms_from_fluid_like,
    select_circulation_cell_for_lat,
    wind_10m_ms_from_weather_agent_like,
    apply_eurus_fluid_wind_to_ocean_grid,
    apply_eurus_weather_agent_wind_to_ocean_grid,
)


def test_fluid_like_mapping():
    o = SimpleNamespace(u_ms=3.0, v_ms=-4.0)
    assert wind_10m_ms_from_fluid_like(o) == (3.0, -4.0)


def test_select_circulation_cell():
    cells = [
        SimpleNamespace(lat_low_rad=0.0, lat_high_rad=0.5, lower_wind_ms=1.0, upper_wind_ms=10.0),
        SimpleNamespace(lat_low_rad=0.5, lat_high_rad=1.0, lower_wind_ms=2.0, upper_wind_ms=20.0),
    ]
    c = select_circulation_cell_for_lat(cells, 0.6)
    assert c is cells[1]


def test_weather_agent_proxy_sets_grid_wind():
    g = OceanGridModel(4, 4, 1_000.0, 1_000.0)
    hadley = SimpleNamespace(
        lat_low_rad=0.0,
        lat_high_rad=math.radians(35.0),
        lower_wind_ms=5.0,
        upper_wind_ms=-20.0,
    )
    agent = SimpleNamespace(cells=[hadley], lat_rad=math.radians(10.0))
    apply_eurus_weather_agent_wind_to_ocean_grid(g, agent)
    u, v = wind_10m_ms_from_weather_agent_like(agent)
    assert abs(u - 5.0) < 1e-9
    g.step(10.0)
    assert g.current_field_state().wind_stress_east_nm2 != 0.0


def test_fluid_applies_to_grid():
    g = OceanGridModel(4, 4, 1_000.0, 1_000.0)
    fluid = SimpleNamespace(u_ms=10.0, v_ms=0.0)
    apply_eurus_fluid_wind_to_ocean_grid(g, fluid)
    cfs = g.current_field_state()
    assert cfs.wind_stress_east_nm2 != 0.0
