import math

from oceanus_engine import OceanGridModel, EARTH_OCEAN
from oceanus_engine.physics.coriolis import coriolis_parameter
from oceanus_engine.physics.tides import harmonic_tide_eta_m, harmonic_tide_eta_derivative_m_per_s
from oceanus_engine.physics.thermohaline import density_linear_eos
from oceanus_engine.coastal.route_utility import route_utility_score, sample_current_bilinear
from oceanus_engine.bridge.marine_autonomy_bridge import (
    world_en_to_vessel_frame,
    marine_perception_dict_from_ocean,
    route_current_correction_dict,
    marine_route_bridge_packet_from_ocean,
)
from oceanus_engine.observer.ocean_observer import build_forecast_frame
from oceanus_engine.physics.plate_hooks import PlateEvent


def test_coriolis_mid_lat():
    phi = math.radians(45.0)
    f = coriolis_parameter(phi, EARTH_OCEAN)
    assert 0.00005 < abs(f) < 0.0002


def test_density_eos_colder_heavier():
    r_warm = density_linear_eos(300.0, 35.0)
    r_cold = density_linear_eos(280.0, 35.0)
    assert r_cold > r_warm


def test_tide_harmonic_bounded():
    eta = harmonic_tide_eta_m(0.0, 0.1, 0.5, 0.5, 0.25, 0.15, 0.1)
    assert abs(eta) < 5.0
    det = harmonic_tide_eta_derivative_m_per_s(100.0, 0.1, 0.5, 0.5, 0.25, 0.15, 0.1)
    assert abs(det) < 1e-2


def test_grid_step_wind():
    g = OceanGridModel(12, 12, 5_000.0, 5_000.0, default_bathymetry_m=200.0)
    g.set_wind_field(8.0, 2.0)
    g.cell(6, 6)
    for _ in range(5):
        g.step(30.0)
    cfs = g.current_field_state()
    assert cfs.nx == 12 and cfs.mean_speed_ms >= 0.0


def test_sample_and_bridge():
    m = OceanGridModel(8, 8, 1_000.0, 1_000.0)
    u, v, _ = sample_current_bilinear(m._cells, 3.5, 3.5)
    d = marine_perception_dict_from_ocean(u, v, 0.0)
    assert "current_u_ms" in d
    su, sw = world_en_to_vessel_frame(1.0, 0.0, 0.0)
    assert abs(su) < 1e-9 and abs(sw - 1.0) < 1e-9


def test_forecast_frame():
    m = OceanGridModel(10, 10, 2_000.0, 2_000.0)
    m.step(60.0)
    cf = m.current_field_state()
    frame = build_forecast_frame(cf, m.all_cells(), 3_600.0)
    assert frame.verdict is not None
    assert 0.0 <= frame.omega_route_utility <= 1.0


def test_route_utility():
    s = route_utility_score(0.5, 0.0, 1.0, 0.0)
    assert 0.0 <= s <= 1.0


def test_route_correction_packet():
    corr = route_current_correction_dict(0.2, -0.1, 1.0, 0.0)
    assert abs(corr["water_relative_cmd_east_ms"] - 0.8) < 1e-9
    assert abs(corr["water_relative_cmd_north_ms"] - 0.1) < 1e-9

    pkt = marine_route_bridge_packet_from_ocean(
        0.2, -0.1, psi_rad=0.0, desired_ground_east_ms=1.0, desired_ground_north_ms=0.0
    )
    assert pkt["contract_version"] == "ocean-marine-bridge.v1"
    assert "marine_perception" in pkt and "route_correction" in pkt


def test_tectonic_resonance_scan_emits_event():
    m = OceanGridModel(8, 8, 1_000.0, 1_000.0)
    captured = []
    m.plate_hooks.register(lambda ev: captured.append(ev))
    # 10 Hz 단일 톤, 샘플링 100 Hz
    fs = 100.0
    f0 = 10.0
    n = 256
    sig = [math.sin(2.0 * math.pi * f0 * t / fs) for t in range(n)]
    out = m.scan_tectonic_resonance(
        sig,
        sample_rate_hz=fs,
        natural_freq_hz=f0,
        boundary_id="pacific_ring",
    )
    assert out["resonance_state"] in ("TUNED", "NEAR_RESONANCE")
    assert out["event_emitted"] is True
    assert len(captured) == 1
    assert isinstance(captured[0], PlateEvent)
    assert captured[0].kind == "earthquake"
