# Eurus -> Cherubim Mapping

## 목적

`Eurus_Engine`이 계산한 대기 유체역학 상태를
`Cherubim`이 읽을 수 있는 **거주 가능성 프록시 상태공간**으로 변환한다.

이 문서는 “어떤 필드가 어떤 의미로 넘어가는가”를 고정해 연결이 꼬이지 않게 한다.

## 입력

- [GlobalAtmosphereState](/Users/jazzin/Desktop/00_BRAIN/_staging/Eurus_Engine/eurus_engine/contracts/schemas.py)
- [WeatherHealthReport](/Users/jazzin/Desktop/00_BRAIN/_staging/Eurus_Engine/eurus_engine/contracts/schemas.py)
- 변환기: [cherubim_bridge.py](/Users/jazzin/Desktop/00_BRAIN/_staging/Eurus_Engine/eurus_engine/bridges/cherubim_bridge.py)

## 출력 필드

| Eurus output | Cherubim-facing key | Meaning |
|---------------|---------------------|---------|
| `mean_surface_temp_k` | `temperature_window_proxy` | 생명 가능 온도창 근사 |
| `total_water_vapor_kg` + `omega_moisture` | `water_availability_proxy` | 수분/수증기 가용성 |
| `energy_imbalance_wm2` | `radiation_proxy` | 복사 불균형 기반 안정성 |
| `omega_total` | `climate_stability_proxy` | 전체 기후 안정성 |
| `mean_sea_level_pressure_pa` | `pressure_atm` | 표면 압력 비율 |
| 조합 점수 | `eden_climate_score` | Cherubim 투입 전 climate suitability |
| `phase` | `eurus_phase` | 현재 대기 위상 |
| `verdict` | `eurus_verdict` | Eurus health verdict |

## 상태공간 흐름

```text
planet snapshot (JOE/MOE)
  -> eurus_state_from_planet_snapshot()
  -> WeatherAgent / health_report()
  -> cherubim_context_from_eurus()
  -> Cherubim input context
```

## 해석 원칙

1. Eurus는 날씨와 대기 흐름을 계산한다.
2. Cherubim은 그 결과를 “에덴 basin 가능성” 쪽으로 읽는다.
3. 따라서 Eurus 출력은 Cherubim의 최종 판정을 대신하지 않는다.
4. `eden_climate_score`는 후보 점수이지, 에덴 확정이 아니다.
