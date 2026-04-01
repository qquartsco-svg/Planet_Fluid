> **한국어 (정본).** English: [README_EN.md](README_EN.md)

> **Planet_Fluid 모노레포:** 대기·해양 통합 개요는 저장소 루트 [README.md](../README.md) · [README_EN.md](../README_EN.md).

# 🌪️ Eurus_Engine

![version](https://img.shields.io/badge/version-0.1.4-blue)
![python](https://img.shields.io/badge/python-≥3.10-green)
![stdlib](https://img.shields.io/badge/deps-stdlib_only-brightgreen)
![tests](https://img.shields.io/badge/tests-113_passed-success)

**행성 대기 날씨 동역학 엔진**

대기 유체역학(Shallow Water Equations) + 열역학 + 대순환 + 복사 에너지 균형을 단일 엔진으로 통합.
지구·화성·금성·임의 행성에 모두 적용 가능한 **행성 독립 설계**.

---

## 핵심 특징

| 영역 | 구현 내용 |
|------|-----------|
| **유체역학** | Shallow Water Equations (SWE), Coriolis 힘, 지균풍, 와도·발산, CFL 안정성 |
| **열역학** | Magnus 포화수증기압, 건조/습윤 단열 감율, CAPE/CIN, 위온도 θ·θe |
| **복사** | Stefan-Boltzmann OLR, 태양 일사량, 복사 에너지 균형, 평형 온도 |
| **대순환** | Hadley·Ferrel·Polar 셀, 제트기류, ITCZ, Walker 순환 (엘니뇨) |
| **기압계** | Rankine 와류 풍속, 가우시안 기압 프로파일, β-drift 이동 |
| **전선** | 한랭/온난/폐색/정체 전선 이동, 강수 강도, 폐색 합성 |
| **건강도** | Ω 5레이어 Observer: 안정도·순환·에너지·수분·동역학 |
| **기후 체제** | temperate / greenhouse / thin atmosphere 등 climate regime 분류 |
| **FSM** | CALM → DEVELOPING → ACTIVE → SEVERE → DISSIPATING → EQUILIBRIUM |
| **다행성** | PlanetConfig — 지구·화성·금성·타이탄 등 임의 행성 지원 |
| **행성 브리지** | TerraCore / Lucifer 입력, JOE·MOE snapshot 흡수, Cherubim용 habitability proxy 출력 |

---

## 모듈 구조

```
eurus_engine/
├── contracts/
│   └── schemas.py          — PlanetConfig, FluidCell, WeatherPhase, StabilityIndex ...
├── physics/
│   ├── fluid_dynamics.py   — SWE, Coriolis, Rossby, 와도, 발산
│   ├── thermodynamics.py   — Magnus, CAPE/CIN, 복사 균형
│   └── vertical_profile.py — 정수압 프로파일, LCL, 브런트-바이살라
├── circulation/
│   ├── hadley_cell.py      — Hadley·Ferrel·Polar, 제트기류, Walker
│   ├── pressure_system.py  — 기압계 이동, Rankine 와류
│   └── fronts.py           — 전선 이동·합성
├── climate/
│   └── regime.py           — climate basin / regime 분류
├── health/
│   └── weather_health.py   — Ω 5레이어 Observer
├── bridges/
│   ├── terracore_bridge.py — TerraCore 대기 상태 변환
│   ├── lucifer_bridge.py   — 궤도 관측값 → 대기 상태
│   ├── joe_moe_bridge.py   — JOE/MOE snapshot → Eurus 상태
│   └── cherubim_bridge.py  — Eurus 상태/건강도 → Cherubim용 proxy
└── agent/
    └── weather_agent.py    — WeatherAgent FSM 오케스트레이터
```

---

## Quick Start

```python
from eurus_engine import WeatherAgent, WeatherEvent, EARTH, MARS

# 지구 여름 아열대 시뮬레이션
agent = WeatherAgent(planet=EARTH, lat_rad=0.52, day_of_year=182)
agent.initialize(T_surface_k=300.0, humidity=0.65)

# 24시간 시뮬레이션
for _ in range(24):
    agent.tick(dt_s=3600.0)

print(agent.summary())
# {
#   "T_surface_k": 300.12,
#   "phase": "calm",
#   "climate_regime": "temperate",
#   "omega_total": 0.832,
#   "verdict": "STABLE",
#   "recommendations": ["STATUS: nominal — no intervention required"]
# }

# 이벤트 충격
agent.apply_event(WeatherEvent.TROPICAL_CYCLONE, magnitude=0.8)
report = agent.health_report()
print(f"Ω = {report.omega_total:.3f}  →  {report.verdict}")

# 화성 시뮬레이션
mars_agent = WeatherAgent(planet=MARS, lat_rad=0.35, day_of_year=90)
mars_agent.initialize(T_surface_k=210.0, humidity=0.01)
mars_agent.tick(dt_s=3600.0)
```

---

## 핵심 물리 방정식

### 얕은 수층 방정식 (SWE)
```
∂u/∂t + u∂u/∂x + v∂u/∂y − f·v = −g∂h/∂x + ν∇²u
∂v/∂t + u∂v/∂x + v∂v/∂y + f·u = −g∂h/∂y + ν∇²v
∂h/∂t + ∂(hu)/∂x + ∂(hv)/∂y = Q
```

### 코리올리 매개변수
```
f = 2Ω·sin(φ)
```

### 포화 수증기압 (Magnus)
```
es = 611.2 · exp(17.67·Tc / (Tc + 243.5))  [Pa]
```

### 건조/습윤 단열 감율
```
Γd = g / cp  ≈ 9.8 K/km
Γm = g(1 + Lv·ws/Rd·T) / (cp + Lv²·ws/Rv·T²)  ≈ 6.5 K/km (포화)
```

### 복사 에너지 균형
```
R = SW_in·(1−A)·(1−0.3·cf) − ε·σ·T⁴·(1−Greenhouse)
```

### Ω 건강도 (가중합)
```
Ω = 0.25·Ω_stab + 0.25·Ω_circ + 0.20·Ω_energy + 0.15·Ω_moist + 0.15·Ω_dyn
```

### Climate Regime 분류 (보수적 프록시)
`Eurus`는 health score 위에 한 단계 더 올라가, 현재 대기가 어떤 climate basin에 있는지 분류합니다.

- `temperate`
- `hot_greenhouse`
- `cold_dry`
- `humid_active`
- `storm_dominant`
- `thin_atmosphere`
- `dense_atmosphere`
- `unstable_transition`

---

## 행성 프리셋

| 행성 | g (m/s²) | Ω (rad/s) | P₀ (Pa) | cp (J/kg·K) |
|------|----------|-----------|---------|-------------|
| Earth | 9.807 | 7.292e-5 | 101,325 | 1,004 |
| Mars | 3.721 | 7.088e-5 | 636 | 735 |
| Venus | 8.870 | 2.992e-7 | 9,200,000 | 820 |

---

## 이벤트 목록

| 이벤트 | 효과 |
|--------|------|
| `tropical_cyclone` | 에너지 불균형 ↑, 와도 ↑, SEVERE |
| `volcanic_eruption` | 기온 ↓ (일사 차단), 에너지 ↓ |
| `el_nino` | 기온 ↑, 습도 ↑ |
| `la_nina` | 기온 ↓, 습도 ↓ |
| `heat_dome` | 기온 ↑↑, 습도 ↓↓ |
| `drought` | 습도 ↓↓, 기온 ↑ |
| `atmospheric_river` | 습도 ↑↑ |
| `polar_vortex_split` | 기온 ↓↓, 에너지 ↓ |

---

## 테스트

```bash
cd Eurus_Engine && python -m pytest tests/ -q
```

무결성·전체 릴리스 점검은 저장소 루트에서:

```bash
python scripts/verify_signature.py
python scripts/release_check.py
```

---

## 아키텍처 위치

```
ENGINE_HUB
└── Eurus_Engine  ←  여기
    ↑ TerraCore 브릿지 (행성 대기 상태 수신)
    ↑ Lucifer_Engine 브릿지 (궤도 관측값 수신)
    ↑ JOE / MOE snapshot 브릿지 (행성 거시·환경 스냅샷 수신)
    → 날씨 동역학 → 유체 흐름 정렬
    → climate regime 분류
    → Cherubim 브릿지 (거주 가능성 proxy 전달)
```

상세 연결 규약: [docs/PLANETARY_BRIDGES.md](docs/PLANETARY_BRIDGES.md)  
필드 매핑: [docs/EURUS_CHERUBIM_MAPPING.md](docs/EURUS_CHERUBIM_MAPPING.md)

> *"어디로 흘러가는가 — 행성 대기의 흐름을 추적한다."*

---

## 무결성 (Planet_Fluid 모노레포)

이 폴더 단독이 아니라 **저장소 루트**에서 무결성 매니페스트를 관리한다.

- [../SIGNATURE.sha256](../SIGNATURE.sha256) — 전체 트리 SHA-256
- [../BLOCKCHAIN_INFO.md](../BLOCKCHAIN_INFO.md) · English: [../BLOCKCHAIN_INFO_EN.md](../BLOCKCHAIN_INFO_EN.md)
