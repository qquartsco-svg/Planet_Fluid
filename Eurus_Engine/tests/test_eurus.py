"""
Eurus_Engine — 테스트 스위트  (50+ 테스트)

§1  PlanetConfig + 프리셋
§2  FluidCell 속성
§3  유체역학 (Coriolis, Rossby, Vorticity, SWE)
§4  열역학 (포화수증기압, 감율, CAPE, 복사)
§5  수직 프로파일
§6  대순환 (Hadley/Ferrel/Polar, Walker)
§7  기압계·전선 역학
§8  Observer Ω (5레이어)
§9  WeatherAgent FSM + 이벤트
§10 브릿지 (TerraCore·Lucifer duck-typing)
"""

import math
import pytest

# --- 계약 ---
from eurus_engine.contracts.schemas import (
    EARTH, MARS, VENUS, PlanetConfig,
    FluidCell, VerticalProfile, GlobalAtmosphereState,
    WeatherPhase, StabilityIndex, WeatherHealthReport,
    Front, FrontType, PressureSystem, PressureSystemType,
    CirculationCellType,
)

# --- 유체역학 ---
from eurus_engine.physics.fluid_dynamics import (
    coriolis_parameter, beta_parameter, rossby_number,
    geostrophic_wind, relative_vorticity, absolute_vorticity,
    potential_vorticity, divergence,
    gravity_wave_speed, rossby_wave_speed,
    kinetic_energy_density, available_potential_energy,
    step_cell_euler,
)

# --- 열역학 ---
from eurus_engine.physics.thermodynamics import (
    saturation_vapor_pressure_pa, mixing_ratio_sat,
    relative_humidity, dew_point_k,
    dry_adiabatic_lapse_rate, moist_adiabatic_lapse_rate,
    potential_temperature, equivalent_potential_temperature,
    cape_cin_simple, stability_index,
    insolation_wm2, outgoing_longwave_radiation_wm2,
    radiative_energy_balance, equilibrium_temperature_k,
)

# --- 수직 프로파일 ---
from eurus_engine.physics.vertical_profile import (
    standard_atmosphere_profile, lcl_altitude_m,
    interpolate_profile_at_altitude, brunt_vaisala_frequency,
    hydrostatic_pressure, density_from_ideal_gas, scale_height,
)

# --- 대순환 ---
from eurus_engine.circulation.hadley_cell import (
    build_circulation_cells, hadley_cell_strength,
    jet_stream_speed_ms, walker_circulation_strength,
)
from eurus_engine.circulation.pressure_system import (
    rankine_vortex_wind, pressure_at_radius,
    advance_pressure_system, estimate_mslp,
)
from eurus_engine.circulation.fronts import (
    advance_front, occlude_front, frontal_precipitation,
    cold_front_speed_ms, warm_front_speed_ms,
)

# --- 건강도 ---
from eurus_engine.health.weather_health import (
    assess_weather_health,
    omega_stability, omega_circulation,
    omega_energy, omega_moisture, omega_dynamics,
)

# --- 에이전트 ---
from eurus_engine.agent.weather_agent import WeatherAgent, WeatherEvent

# --- 브릿지 ---
from eurus_engine.bridges.terracore_bridge import (
    fluid_cell_from_terracore, global_state_from_terracore,
    optional_terracore_handoff,
)
from eurus_engine.bridges.lucifer_bridge import (
    atmosphere_obs_from_lucifer, orbital_coverage_lat_band,
    ground_resolution_m,
)
from eurus_engine.bridges.joe_moe_bridge import eurus_state_from_planet_snapshot
from eurus_engine.bridges.cherubim_bridge import cherubim_context_from_eurus
from eurus_engine.climate.regime import classify_climate_regime


# ===========================================================================
# §1 PlanetConfig + 프리셋
# ===========================================================================
class TestPlanetConfig:
    def test_earth_name(self):
        assert EARTH.name == "Earth"

    def test_earth_gravity(self):
        assert abs(EARTH.gravity_ms2 - 9.80665) < 1e-4

    def test_mars_lower_gravity(self):
        assert MARS.gravity_ms2 < EARTH.gravity_ms2

    def test_venus_slow_rotation(self):
        assert VENUS.rotation_rate_rads < EARTH.rotation_rate_rads

    def test_earth_day_s(self):
        assert 86000 < EARTH.day_s < 87000

    def test_earth_lapse_rate(self):
        gamma = EARTH.dry_adiabatic_lapse_rate_k_m
        assert 0.009 < gamma < 0.011

    def test_custom_planet(self):
        p = PlanetConfig(name="Titan", gravity_ms2=1.352, radius_m=2_575_000.0)
        assert p.name == "Titan"

    def test_mars_surface_pressure(self):
        assert MARS.surface_pressure_pa < 1000.0


# ===========================================================================
# §2 FluidCell 속성
# ===========================================================================
class TestFluidCell:
    def test_speed_pythagoras(self):
        cell = FluidCell(u_ms=3.0, v_ms=4.0)
        assert abs(cell.speed_ms - 5.0) < 1e-9

    def test_calm_speed(self):
        cell = FluidCell(u_ms=0.0, v_ms=0.0)
        assert cell.speed_ms == 0.0

    def test_density_positive(self):
        cell = FluidCell(p_pa=101325.0, T_k=288.15)
        assert cell.density_kg_m3 > 0.0

    def test_virtual_temperature_gt_T(self):
        cell = FluidCell(T_k=300.0, q=0.01)
        assert cell.virtual_temperature_k > 300.0

    def test_mach_low_speed(self):
        cell = FluidCell(u_ms=10.0, v_ms=0.0, T_k=288.15)
        assert cell.mach < 0.1

    def test_wind_direction_range(self):
        cell = FluidCell(u_ms=5.0, v_ms=5.0)
        assert 0.0 <= cell.wind_direction_deg < 360.0


# ===========================================================================
# §3 유체역학
# ===========================================================================
class TestFluidDynamics:
    def test_coriolis_equator_zero(self):
        assert coriolis_parameter(0.0) == 0.0

    def test_coriolis_north_pole(self):
        f = coriolis_parameter(math.pi / 2)
        assert abs(f - 2 * EARTH.rotation_rate_rads) < 1e-12

    def test_coriolis_negative_south(self):
        assert coriolis_parameter(-math.radians(30)) < 0

    def test_beta_positive_north(self):
        assert beta_parameter(math.radians(45)) > 0

    def test_rossby_geostrophic(self):
        Ro = rossby_number(1.0, 1_000_000.0, math.radians(45))
        assert Ro < 0.1

    def test_rossby_convective(self):
        Ro = rossby_number(50.0, 1_000.0, math.radians(45))
        assert Ro > 1.0

    def test_geostrophic_wind_components(self):
        u_g, v_g = geostrophic_wind(-10.0, 0.0, 1.2, math.radians(45))
        assert abs(u_g) > 0 or abs(v_g) > 0

    def test_relative_vorticity(self):
        zeta = relative_vorticity(du_dy=1e-5, dv_dx=3e-5)
        assert abs(zeta - 2e-5) < 1e-15

    def test_absolute_vorticity_gt_relative(self):
        zeta = 1e-5
        eta  = absolute_vorticity(zeta, math.radians(45))
        f    = coriolis_parameter(math.radians(45))
        assert abs(eta - (zeta + f)) < 1e-15

    def test_potential_vorticity(self):
        pv = potential_vorticity(1e-4, 1000.0)
        assert abs(pv - 1e-7) < 1e-15

    def test_divergence_sum(self):
        D = divergence(1e-5, 2e-5)
        assert abs(D - 3e-5) < 1e-18

    def test_gravity_wave_speed_earth(self):
        c = gravity_wave_speed(8500.0)
        assert c > 200.0

    def test_rossby_wave_westward(self):
        beta = beta_parameter(math.radians(45))
        k    = 2 * math.pi / 5_000_000.0
        c    = rossby_wave_speed(k, beta, u_mean=0.0)
        assert c < 0.0

    def test_kinetic_energy_density(self):
        ke = kinetic_energy_density(10.0, 0.0, 1.2)
        assert abs(ke - 0.5 * 1.2 * 100.0) < 1e-9

    def test_step_cell_euler_returns_fluid_cell(self):
        cell = FluidCell(u_ms=5.0, v_ms=2.0, h_m=8500.0,
                         T_k=288.15, φ_rad=math.radians(45))
        result = step_cell_euler(cell, cell, cell, cell, cell,
                                  dt_s=60.0, dx_m=50_000.0, dy_m=50_000.0)
        assert isinstance(result, FluidCell)
        assert result.h_m > 0.0


# ===========================================================================
# §4 열역학
# ===========================================================================
class TestThermodynamics:
    def test_saturation_vp_0c(self):
        es = saturation_vapor_pressure_pa(273.15)
        assert 600 < es < 650

    def test_saturation_vp_increases(self):
        assert saturation_vapor_pressure_pa(300.0) > saturation_vapor_pressure_pa(280.0)

    def test_mixing_ratio_positive(self):
        assert mixing_ratio_sat(300.0, 101325.0) > 0

    def test_rh_saturated(self):
        assert abs(relative_humidity(288.15, 288.15) - 1.0) < 1e-6

    def test_rh_dry(self):
        assert relative_humidity(300.0, 270.0) < 0.5

    def test_dew_point_below_T(self):
        assert dew_point_k(300.0, 0.5) < 300.0

    def test_dry_lapse_earth(self):
        gamma = dry_adiabatic_lapse_rate(EARTH)
        assert abs(gamma - EARTH.gravity_ms2 / EARTH.cp_j_kgk) < 1e-9

    def test_moist_lapse_smaller_than_dry(self):
        gamma_d = dry_adiabatic_lapse_rate(EARTH)
        gamma_m = moist_adiabatic_lapse_rate(300.0, 101325.0, EARTH)
        assert gamma_m < gamma_d

    def test_potential_temperature_surface(self):
        theta = potential_temperature(288.15, 100_000.0)
        assert 285 < theta < 295

    def test_equivalent_pt_ge_pt(self):
        theta   = potential_temperature(300.0, 100_000.0)
        theta_e = equivalent_potential_temperature(300.0, 100_000.0, 0.01)
        assert theta_e >= theta

    def test_insolation_equator_summer(self):
        assert insolation_wm2(0.0, 172) > 300

    def test_insolation_polar_night(self):
        assert insolation_wm2(math.radians(90), 1) == 0.0

    def test_olr_increases_with_T(self):
        assert outgoing_longwave_radiation_wm2(320.0) > outgoing_longwave_radiation_wm2(280.0)

    def test_equilibrium_temp_positive(self):
        assert equilibrium_temperature_k(0.0, 172) > 0.0

    def test_cape_cin_empty_profile(self):
        cape, cin = cape_cin_simple(VerticalProfile(), 300.0, 101325.0, 295.0)
        assert cape == 0.0 and cin == 0.0

    def test_cape_cin_simple_profile(self):
        profile = VerticalProfile(
            altitudes_m=(0.0, 1000.0, 2000.0, 5000.0, 10000.0),
            temperatures_k=(300.0, 294.0, 288.0, 272.0, 250.0),
            pressures_pa=(101325.0, 89874.0, 79501.0, 54048.0, 26500.0),
            densities_kg_m3=(1.225, 1.112, 0.952, 0.736, 0.414),
        )
        cape, cin = cape_cin_simple(profile, 300.0, 101325.0, 295.0)
        assert cape >= 0.0
        assert cin  <= 0.0


# ===========================================================================
# §5 수직 프로파일
# ===========================================================================
class TestVerticalProfile:
    def test_earth_profile_levels(self):
        profile = standard_atmosphere_profile(EARTH)
        assert profile.n_levels > 10

    def test_pressure_monotone_decrease(self):
        profile = standard_atmosphere_profile(EARTH)
        for i in range(1, profile.n_levels):
            assert profile.pressures_pa[i] < profile.pressures_pa[i - 1]

    def test_surface_temp_matches(self):
        profile = standard_atmosphere_profile(EARTH, T_surface_k=300.0)
        assert profile.temperatures_k[0] == 300.0

    def test_mars_surface_pressure(self):
        profile = standard_atmosphere_profile(MARS, T_surface_k=210.0)
        assert abs(profile.pressures_pa[0] - MARS.surface_pressure_pa) < 1.0

    def test_lcl_zero_saturated(self):
        assert lcl_altitude_m(273.15, 273.15) == 0.0

    def test_lcl_larger_for_drier(self):
        assert lcl_altitude_m(300.0, 285.0) > lcl_altitude_m(300.0, 295.0)

    def test_brunt_vaisala_stable(self):
        # -5 K/km > -Γd (-9.8 K/km) → 안정
        N2 = brunt_vaisala_frequency(288.15, -5.0 / 1000.0, EARTH)
        assert N2 > 0

    def test_brunt_vaisala_unstable(self):
        # -12 K/km < -Γd → 불안정
        N2 = brunt_vaisala_frequency(288.15, -12.0 / 1000.0, EARTH)
        assert N2 < 0

    def test_interpolate_at_surface(self):
        profile = standard_atmosphere_profile(EARTH)
        T, p, rho = interpolate_profile_at_altitude(profile, 0.0)
        assert abs(T - 288.15) < 1.0

    def test_hydrostatic_decreases(self):
        p1 = hydrostatic_pressure(101325.0, 288.15, 1000.0)
        assert p1 < 101325.0

    def test_density_ideal_gas(self):
        rho = density_from_ideal_gas(101325.0, 288.15)
        assert abs(rho - 1.225) < 0.05

    def test_scale_height_earth(self):
        H = scale_height(288.15, EARTH)
        assert 8000 < H < 9000


# ===========================================================================
# §6 대순환
# ===========================================================================
class TestCirculation:
    def test_three_cells(self):
        cells = build_circulation_cells()
        assert len(cells) == 3

    def test_cell_types_present(self):
        cells = build_circulation_cells()
        types = {c.cell_type for c in cells}
        assert CirculationCellType.HADLEY in types
        assert CirculationCellType.FERREL in types
        assert CirculationCellType.POLAR  in types

    def test_hadley_strength_large_dT(self):
        s1 = hadley_cell_strength(320.0, 250.0)
        s2 = hadley_cell_strength(300.0, 280.0)
        assert s1 > s2

    def test_jet_speed_positive(self):
        assert jet_stream_speed_ms(1.0, EARTH) > 0

    def test_walker_el_nino(self):
        w = walker_circulation_strength(300.0, 300.0)
        assert abs(w) < 0.1

    def test_walker_normal(self):
        w = walker_circulation_strength(298.0, 302.0)
        assert w > 0

    def test_mars_three_cells(self):
        cells = build_circulation_cells(planet=MARS)
        assert len(cells) == 3

    def test_cell_omega_range(self):
        cells = build_circulation_cells()
        for c in cells:
            assert 0.0 <= c.omega_cell <= 1.0


# ===========================================================================
# §7 기압계·전선 역학
# ===========================================================================
class TestPressureAndFronts:
    def test_rankine_inside_core(self):
        v = rankine_vortex_wind(50_000.0, 100_000.0, 50.0)
        assert 0 < v <= 50.0

    def test_rankine_outside_decays(self):
        # 두 점 모두 core 밖: 더 멀수록 풍속 감소
        v_near = rankine_vortex_wind(150_000.0, 100_000.0, 50.0)
        v_far  = rankine_vortex_wind(400_000.0, 100_000.0, 50.0)
        assert v_far < v_near

    def test_pressure_at_center(self):
        p = pressure_at_radius(95000.0, 101325.0, 0.0, 300_000.0)
        assert abs(p - 95000.0) < 1.0

    def test_cold_faster_than_warm(self):
        assert cold_front_speed_ms(20.0) > warm_front_speed_ms(20.0)

    def test_advance_cold_front_south(self):
        front = Front(
            front_type=FrontType.COLD,
            lat_rad=math.radians(50.0),
            lon_start_rad=0.0, lon_end_rad=1.0,
            temp_gradient_k_m=0.005,
            speed_ms=10.0, precipitation=0.5,
        )
        front2 = advance_front(front, dt_s=3600.0, upper_wind_ms=15.0)
        assert front2.lat_rad < front.lat_rad   # 남쪽으로

    def test_advance_warm_front_north(self):
        front = Front(
            front_type=FrontType.WARM,
            lat_rad=math.radians(45.0),
            lon_start_rad=0.0, lon_end_rad=1.0,
            temp_gradient_k_m=0.003,
            speed_ms=8.0, precipitation=0.3,
        )
        front2 = advance_front(front, dt_s=3600.0, upper_wind_ms=15.0)
        assert front2.lat_rad > front.lat_rad   # 북쪽으로

    def test_occluded_front_type(self):
        cold = Front(FrontType.COLD, math.radians(50), 0.0, 1.0, 0.01, 15.0, 0.7)
        warm = Front(FrontType.WARM, math.radians(52), 0.0, 1.0, 0.005, 8.0, 0.4)
        occ  = occlude_front(cold, warm)
        assert occ.front_type == FrontType.OCCLUDED

    def test_advance_pressure_system_moves(self):
        sys = PressureSystem(
            system_type=PressureSystemType.LOW,
            center_lat_rad=math.radians(20),
            center_lon_rad=math.radians(140),
            central_pressure_pa=98000.0,
            radius_m=300_000.0,
            max_wind_ms=40.0,
            intensity=0.7,
        )
        sys2 = advance_pressure_system(sys, dt_s=3600.0)
        moved = (sys2.center_lat_rad != sys.center_lat_rad or
                 sys2.center_lon_rad != sys.center_lon_rad)
        assert moved

    def test_frontal_precipitation_cold_stronger(self):
        cold = Front(FrontType.COLD, 0.0, 0.0, 1.0, 0.01, 10.0, 0.5)
        warm = Front(FrontType.WARM, 0.0, 0.0, 1.0, 0.01, 10.0, 0.5)
        assert frontal_precipitation(cold) > frontal_precipitation(warm)


# ===========================================================================
# §8 Observer Ω
# ===========================================================================
class TestWeatherHealth:
    def _calm_state(self):
        return GlobalAtmosphereState(
            t_s=0.0, mean_surface_temp_k=288.15,
            energy_imbalance_wm2=0.3, phase=WeatherPhase.CALM,
        )

    def test_omega_stability_low_cape(self):
        s = StabilityIndex(CAPE_j_kg=100.0)
        assert omega_stability(s, WeatherPhase.CALM) > 0.9

    def test_omega_stability_extreme_cape(self):
        s = StabilityIndex(CAPE_j_kg=5000.0, CIN_j_kg=-200.0)
        assert omega_stability(s, WeatherPhase.SEVERE) < 0.3

    def test_omega_energy_balanced(self):
        assert omega_energy(0.3) == 1.0

    def test_omega_energy_extreme(self):
        assert omega_energy(15.0) == 0.0

    def test_omega_moisture_optimal(self):
        assert omega_moisture(0.55) > 0.9

    def test_omega_moisture_dry(self):
        # humidity=0.10: hum_score=0.25, balance_score=1.0 → 0.25*0.6+1.0*0.4=0.55
        # 최적 범위(0.55)보다 낮아야 함
        assert omega_moisture(0.10) < omega_moisture(0.55)

    def test_full_health_nominal(self):
        report = assess_weather_health(self._calm_state())
        assert report.omega_total > 0.0
        assert report.verdict in ("STABLE", "ACTIVE", "FRAGILE", "CRITICAL")

    def test_severe_phase_cap(self):
        state = GlobalAtmosphereState(
            t_s=0.0, mean_surface_temp_k=310.0,
            energy_imbalance_wm2=20.0, phase=WeatherPhase.SEVERE,
        )
        report = assess_weather_health(state)
        assert report.omega_total <= 0.35

    def test_energy_imbalance_blocker(self):
        state = GlobalAtmosphereState(
            t_s=0.0, mean_surface_temp_k=288.0,
            energy_imbalance_wm2=25.0, phase=WeatherPhase.ACTIVE,
        )
        report = assess_weather_health(state)
        assert "ENERGY_IMBALANCE" in report.blockers

    def test_weather_ok_stable(self):
        report = assess_weather_health(self._calm_state())
        # verdict 에 따라 weather_ok 일치 여부 확인
        assert report.weather_ok == (report.verdict in ("STABLE", "ACTIVE"))


# ===========================================================================
# §9 WeatherAgent FSM + 이벤트
# ===========================================================================
class TestWeatherAgent:
    def test_initialize(self):
        agent = WeatherAgent(planet=EARTH)
        agent.initialize(T_surface_k=295.0)
        assert agent._initialized

    def test_tick_advances_time(self):
        agent = WeatherAgent()
        agent.initialize()
        agent.tick(dt_s=3600.0)
        assert agent.t_s == 3600.0

    def test_tick_24h(self):
        agent = WeatherAgent(planet=EARTH, lat_rad=math.radians(35))
        agent.initialize(T_surface_k=300.0)
        for _ in range(24):
            agent.tick(dt_s=3600.0)
        assert agent.t_s == 86400.0
        assert agent.T_surface_k > 0

    def test_event_tropical_cyclone_severe(self):
        agent = WeatherAgent()
        agent.initialize()
        agent.apply_event(WeatherEvent.TROPICAL_CYCLONE, 1.0)
        assert agent.phase == WeatherPhase.SEVERE

    def test_event_volcanic_cools(self):
        agent = WeatherAgent()
        agent.initialize(T_surface_k=300.0)
        T_before = agent.T_surface_k
        agent.apply_event(WeatherEvent.VOLCANIC_ERUPTION, 1.0)
        assert agent.T_surface_k < T_before

    def test_event_el_nino_warms(self):
        agent = WeatherAgent()
        agent.initialize(T_surface_k=295.0)
        T_before = agent.T_surface_k
        agent.apply_event(WeatherEvent.EL_NINO, 1.0)
        assert agent.T_surface_k > T_before

    def test_event_heat_dome_phase(self):
        agent = WeatherAgent()
        agent.initialize(T_surface_k=288.0)
        agent.apply_event(WeatherEvent.HEAT_DOME, 1.0)
        assert agent.phase in (WeatherPhase.ACTIVE, WeatherPhase.SEVERE)

    def test_health_report_type(self):
        agent = WeatherAgent()
        agent.initialize()
        assert isinstance(agent.health_report(), WeatherHealthReport)

    def test_summary_keys(self):
        agent = WeatherAgent()
        agent.initialize()
        s = agent.summary()
        for key in ("T_surface_k", "phase", "omega_total", "verdict", "recommendations"):
            assert key in s

    def test_athena_recs_list(self):
        agent = WeatherAgent()
        agent.initialize()
        recs = agent.athena_recommendations()
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_mars_agent(self):
        agent = WeatherAgent(planet=MARS, lat_rad=math.radians(20))
        agent.initialize(T_surface_k=210.0, humidity=0.01)
        agent.tick(dt_s=3600.0)
        assert agent.T_surface_k > 100.0

    def test_history_grows(self):
        agent = WeatherAgent()
        agent.initialize()
        agent.tick(dt_s=3600.0)
        agent.tick(dt_s=3600.0)
        assert len(agent.history) == 2

    def test_humidity_clipped(self):
        agent = WeatherAgent()
        agent.initialize(humidity=0.99)
        agent.apply_event(WeatherEvent.ATMOSPHERIC_RIVER, 2.0)
        assert agent.mean_humidity <= 0.99


# ===========================================================================
# §10 브릿지 (TerraCore·Lucifer duck-typing)
# ===========================================================================
class TestBridges:
    def test_terracore_from_dict(self):
        d = {"lon_rad": 0.5, "lat_rad": 0.3, "T_k": 290.0, "p_pa": 101000.0}
        cell = fluid_cell_from_terracore(d)
        assert abs(cell.T_k - 290.0) < 1e-6

    def test_terracore_from_object(self):
        class FakeCell:
            u_ms = 5.0; v_ms = 2.0; T_k = 295.0
            p_pa = 100000.0; h_m = 8500.0; q = 0.01

        cell = fluid_cell_from_terracore(FakeCell())
        assert abs(cell.T_k - 295.0) < 1e-6

    def test_global_state_from_dict(self):
        d = {"mean_temp_k": 288.0, "energy_imbalance_wm2": 0.5, "phase": "calm"}
        state = global_state_from_terracore(d)
        assert state.phase == WeatherPhase.CALM

    def test_global_state_unknown_phase(self):
        d = {"phase": "tornado_xyz"}
        state = global_state_from_terracore(d)
        assert state.phase == WeatherPhase.CALM   # fallback

    def test_optional_none_returns_none(self):
        assert optional_terracore_handoff(None) is None

    def test_lucifer_dict(self):
        d = {"nadir_T_k": 300.0, "cloud_fraction": 0.3, "energy_imbalance_wm2": 1.0}
        state = atmosphere_obs_from_lucifer(d)
        assert state is not None
        assert abs(state.mean_surface_temp_k - 300.0) < 1e-6

    def test_lucifer_heavy_cloud_active(self):
        d = {"nadir_T_k": 285.0, "cloud_fraction": 0.9}
        state = atmosphere_obs_from_lucifer(d)
        assert state.phase == WeatherPhase.ACTIVE

    def test_lucifer_none_returns_none(self):
        assert atmosphere_obs_from_lucifer(None) is None

    def test_orbital_coverage(self):
        s, n = orbital_coverage_lat_band(math.radians(51.6))
        assert s < 0 < n

    def test_joe_moe_snapshot_to_eurus_state(self):
        snapshot = {
            "greenhouse_proxy": 0.65,
            "hydrology_stability_proxy": 0.70,
            "biosphere_window_score": 0.75,
            "climate_variance_proxy": 0.20,
            "seasonality_proxy": 0.15,
            "W_surface": 1.2e9,
            "W_total": 1.5e9,
            "P_w": 0.55,
        }
        state = eurus_state_from_planet_snapshot(snapshot)
        assert 200.0 < state.mean_surface_temp_k < 400.0
        assert state.total_water_vapor_kg > 0.0
        assert state.mean_sea_level_pressure_pa > 0.0

    def test_cherubim_context_from_eurus(self):
        agent = WeatherAgent(planet=EARTH, lat_rad=math.radians(20.0), day_of_year=180)
        agent.initialize(T_surface_k=295.0, humidity=0.65)
        ctx = cherubim_context_from_eurus(
            GlobalAtmosphereState(
                t_s=agent.t_s,
                mean_surface_temp_k=agent.T_surface_k,
                mean_sea_level_pressure_pa=101325.0,
                total_water_vapor_kg=1.27e16,
                energy_imbalance_wm2=agent.energy_imbalance_wm2,
                phase=agent.phase,
            ),
            agent.health_report(),
        )
        assert 0.0 <= ctx["temperature_window_proxy"] <= 1.0
        assert 0.0 <= ctx["water_availability_proxy"] <= 1.0
        assert 0.0 <= ctx["radiation_proxy"] <= 1.0
        assert 0.0 <= ctx["eden_climate_score"] <= 1.0

    def test_snapshot_chain_preserves_expected_keys(self):
        snapshot = {
            "sigma_plate": 0.10,
            "P_w": 0.52,
            "S_rot": 0.22,
            "W_surface": 1.0e9,
            "W_total": 1.4e9,
            "dW_surface_dt_norm": 0.02,
            "greenhouse_proxy": 0.62,
            "hydrology_stability_proxy": 0.70,
            "biosphere_window_score": 0.76,
            "climate_variance_proxy": 0.18,
            "seasonality_proxy": 0.20,
            "albedo_eff": 0.29,
        }
        state = eurus_state_from_planet_snapshot(snapshot, planet=EARTH)
        agent = WeatherAgent(planet=EARTH, lat_rad=math.radians(15.0), day_of_year=180)
        agent.initialize(T_surface_k=state.mean_surface_temp_k, humidity=0.65)
        ctx = cherubim_context_from_eurus(state, agent.health_report(), planet=EARTH)
        for key in (
            "temperature_window_proxy",
            "water_availability_proxy",
            "radiation_proxy",
            "climate_stability_proxy",
            "pressure_atm",
            "eden_climate_score",
            "eurus_phase",
            "eurus_verdict",
            "eurus_regime",
            "climate_regime_score",
        ):
            assert key in ctx

    def test_temperate_climate_regime_classification(self):
        state = GlobalAtmosphereState(
            mean_surface_temp_k=294.0,
            mean_sea_level_pressure_pa=101325.0,
            total_water_vapor_kg=1.27e16,
            energy_imbalance_wm2=0.8,
            phase=WeatherPhase.CALM,
        )
        report = assess_weather_health(state, mean_humidity=0.58)
        regime = classify_climate_regime(state, report, mean_humidity=0.58, planet=EARTH)
        assert regime.regime.value == "temperate"
        assert regime.climate_regime_score > 0.7

    def test_hot_greenhouse_regime_classification(self):
        state = GlobalAtmosphereState(
            mean_surface_temp_k=360.0,
            mean_sea_level_pressure_pa=180000.0,
            total_water_vapor_kg=2.0e16,
            energy_imbalance_wm2=12.0,
            phase=WeatherPhase.ACTIVE,
        )
        report = assess_weather_health(state, mean_humidity=0.82)
        regime = classify_climate_regime(state, report, mean_humidity=0.82, planet=EARTH)
        assert regime.regime.value == "hot_greenhouse"
        assert regime.climate_regime_score < 0.7

    def test_calm_critical_state_is_not_forced_to_storm_dominant(self):
        state = GlobalAtmosphereState(
            mean_surface_temp_k=257.0,
            mean_sea_level_pressure_pa=102000.0,
            total_water_vapor_kg=1.1e16,
            energy_imbalance_wm2=-0.4,
            phase=WeatherPhase.CALM,
        )
        report = WeatherHealthReport(
            omega_stability=0.2,
            omega_circulation=0.3,
            omega_energy=0.9,
            omega_moisture=0.7,
            omega_dynamics=0.4,
            omega_total=0.34,
            phase=WeatherPhase.CALM,
            verdict="CRITICAL",
        )
        regime = classify_climate_regime(state, report, mean_humidity=0.55, planet=EARTH)
        assert regime.regime.value != "storm_dominant"

    def test_ground_resolution(self):
        gsd = ground_resolution_m(500_000.0, 1e-4)
        assert abs(gsd - 50.0) < 0.1
