> **한국어 (정본).** English: [README_EN.md](README_EN.md)

> **Planet_Fluid 모노레포:** 통합 개요는 [../README.md](../README.md) · [../README_EN.md](../README_EN.md). 무결성 매니페스트는 저장소 루트 [../SIGNATURE.sha256](../SIGNATURE.sha256).

# Oceanus_Engine

**행성 해양 동역학 공통 엔진** — Eurus(대기)와 짝을 이루는 **바다의 유체·열염·조석·해저·판 훅** 레이어.  
선박 자율 엔진이 아니라 **배가 떠 있는 바다 자체**의 상태를 시간에 따라 갱신·요약·외부 스택에 넘기는 **L1 물리 코어 + 계약**이다.

## 레이어

| Layer | 내용 |
|-------|------|
| **L0** | `OceanCellState`, `CurrentFieldState`, `ThermohalineState`, `TideState`, `SeafloorState`, `PlateBoundaryState`, `CoastalState`, `OceanObservation`, `OceanForecastFrame` |
| **L1** | 2D 얕은물(SWE): η, H, u, v, 코리올리, 바람 응력, 수치 확산 |
| **L2** | 선형 EOS, `ThermohalineState` 집계, 전환 경향 프록시 |
| **L3** | M2/S2/K1/O1 조화 + 달·태양 합삭 위상 프록시, 조석 연속식 소스 + 조류 성분 중첩 |
| **L4** | 해저 경사·분류, `PlateHookRegistry` 이벤트 훅 |
| **L4.5** | `Tectonic_Resonance_Scan` — FrequencyCore(가능 시) 기반 공명 스캔 후 `PlateEvent` emit |
| **L5** | `route_utility`, 연안/항만 프록시, Marine 브리지용 보간 |
| **L6** | `Ω_*` 스칼라, `OceanHealthVerdict` |

## 빠른 사용

```python
from oceanus_engine import OceanGridModel
from oceanus_engine.observer.ocean_observer import build_forecast_frame
from oceanus_engine.bridge.marine_autonomy_bridge import marine_perception_dict_from_ocean

m = OceanGridModel(24, 24, 10_000.0, 10_000.0, default_bathymetry_m=500.0)
m.set_wind_field(10.0, 3.0)
m.step(60.0)
cf = m.current_field_state()
frame = build_forecast_frame(cf, m.all_cells(), horizon_s=3600.0)
d = marine_perception_dict_from_ocean(0.2, -0.1, psi_rad=0.0)
# MarinePerception(**d) — marine_autonomy 설치 시

# tectonic resonance scan (FrequencyCore 있으면 자동 사용)
signal = [0.0, 0.3, 0.8, 0.3, 0.0, -0.3, -0.8, -0.3]
scan = m.scan_tectonic_resonance(
    signal,
    sample_rate_hz=8.0,
    natural_freq_hz=1.0,
    boundary_id="pacific_ring",
)
```

## L4 `engine_ref`

- `ocean.current.forecast`, `ocean.route.utility` — 상위 `00_BRAIN` 워크스페이스의 `design_workspace` / `l4_runner`와 연동되는 계약이다. (이 GitHub 클론에는 해당 폴더가 없을 수 있음.)

## 연계

- **Eurus**: `wind_stress_*` / 바람 벡터를 `set_wind_field`로 주입.
- **Eurus (FluidCell / WeatherAgent)**: `oceanus_engine.bridge.eurus_wind_adapter` — `apply_eurus_fluid_wind_to_ocean_grid(grid, fluid_cell)`, `apply_eurus_weather_agent_wind_to_ocean_grid(grid, agent)` (`eurus_engine` 비필수·덕 타이핑).
- **Marine_Autonomy_Stack**: `marine_perception_dict_from_ocean` 또는 `sample_current_for_vessel`.
- **design_workspace**: `ocean.current.forecast`, `ocean.route.utility` 등 노드로 `OceanForecastFrame` 매핑.

## 테스트

```bash
cd Oceanus_Engine && python -m pytest tests/ -q
```

## 의존성

표준 라이브러리만 사용 (`requires-python >= 3.10`).
