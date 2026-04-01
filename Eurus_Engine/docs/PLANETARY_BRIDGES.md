# Eurus_Engine — Planetary Bridges

## 역할

`Eurus_Engine`은 **행성 대기 유체역학 코어**다.  
그래서 앞단의 거시 행성 스냅샷과 뒷단의 거주 가능성 엔진 사이를 유기적으로 연결해야 한다.

현재 기준 흐름:

```text
Lucifer / TerraCore / JOE / MOE
            ↓
         Eurus
            ↓
        Cherubim
```

## 원칙

1. 엔진은 서로 직접 강하게 import하지 않는다.
2. 공통 상태는 `dict snapshot` 또는 얇은 dataclass로만 주고받는다.
3. Eurus는 “행성 날씨/대기 동역학”만 담당한다.
4. Cherubim은 “에덴 상태 basin / habitability search”를 담당한다.

## 입력: JOE / MOE snapshot -> Eurus

브리지:
- [joe_moe_bridge.py](/Users/jazzin/Desktop/00_BRAIN/_staging/Eurus_Engine/eurus_engine/bridges/joe_moe_bridge.py)

주요 입력 키:

| Key | Used for |
|-----|----------|
| `greenhouse_proxy` | surface temperature / radiative imbalance |
| `albedo_eff` | absorbed shortwave adjustment |
| `hydrology_stability_proxy` | vapor reservoir scaling |
| `biosphere_window_score` | water-cycle moderation |
| `climate_variance_proxy` | phase severity |
| `seasonality_proxy` | seasonal thermal penalty |
| `W_surface`, `W_total` | vapor inventory ratio |
| `P_w` | pressure proxy |

출력:
- `GlobalAtmosphereState`

즉 JOE/MOE는 “행성 조건 공간”을 주고, Eurus는 그 조건 아래에서 대기 유체 상태를 만든다.

## 출력: Eurus -> Cherubim

브리지:
- [cherubim_bridge.py](/Users/jazzin/Desktop/00_BRAIN/_staging/Eurus_Engine/eurus_engine/bridges/cherubim_bridge.py)

주요 출력 키:

| Key | Meaning |
|-----|---------|
| `temperature_window_proxy` | 생명 가능 온도창 근사 |
| `water_availability_proxy` | 수분/수증기 기반 가용성 |
| `radiation_proxy` | 복사 불균형 기반 안정성 |
| `climate_stability_proxy` | Eurus Ω 기반 기후 안정성 |
| `pressure_atm` | 표면 기압 비율 |
| `eden_climate_score` | Cherubim 투입 전 climate score |
| `eurus_phase` | 현재 대기 위상 |
| `eurus_verdict` | Eurus health verdict |

즉 Eurus는 Cherubim이 볼 “기후 거주성 입력”을 정리해주는 역할이다.

## 연결 의미

- `JOE`는 거시 행성 조건을 잡는다.
- `MOE`는 환경 리스크를 분해한다.
- `Eurus`는 그 조건에서 **대기 유체가 실제로 어떻게 흐르는지** 계산한다.
- `Cherubim`은 그 흐름이 에덴 상태를 허용하는지 본다.

이 구조가 맞아야 “행성 유체역학 시스템”으로 유기적으로 맞물린다.
