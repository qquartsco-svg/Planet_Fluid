> **한국어 (정본).** English: [README_EN.md](README_EN.md)

# Planet_Fluid

**행성 유체 쌍(Coupled Planet Fluid)** — 대기 **Eurus_Engine** 과 해양 **Oceanus_Engine** 을 한 저장소에서 다루고, 바람 forcing으로 표층 해역을 묶는 **L1 통합 스택**이다.

GitHub 공개 저장소 이름: **`Planet_Fluid`** (`qquartsco-svg/Planet_Fluid`).  
이 레포는 **고정밀 GCM/OGCM** 이 아니라, 00_BRAIN 계열에서 쓰는 **경량·관측·브리지 친화** 유체 코어 두 개를 **동일 프레임**에 둔다.

---

## 레이아웃

```
Planet_Fluid/
├── Eurus_Engine/          ← 행성 대기 (SWE, 순환, 전선, Ω 기후·건강)
├── Oceanus_Engine/        ← 행성 해양 (SWE 표층, 열염, 조석, 해저·판 훅)
├── planet_fluid/          ← 우산 패키지(버전 마커)
├── examples/
│   └── run_planet_fluid_demo.py   ← Eurus FluidCell → Oceanus 격자 1틱
├── scripts/
│   ├── regenerate_signature.py
│   ├── verify_signature.py
│   ├── release_check.py
│   └── cleanup_generated.py
├── BLOCKCHAIN_INFO.md
├── BLOCKCHAIN_INFO_EN.md
├── SIGNATURE.sha256
├── README.md / README_EN.md
└── VERSION
```

---

## 연결(행성 플루이드)

| 방향 | 메커니즘 |
|------|-----------|
| Eurus → Oceanus | `oceanus_engine.bridge.eurus_wind_adapter`: `FluidCell` / `WeatherAgent` 규약 → `OceanGridModel.set_wind_field` |
| Oceanus 단독 | `set_wind_field(u, v)` 로 임의 바람도 동일 경로 |

`eurus_engine` 은 Oceanus 쪽 **필수 의존이 아님**(덕 타이핑). 이 레포는 두 패키지를 **형제 폴더**로 넣어 두었기 때문에 데모는 `sys.path` 로 로드한다.

---

## 빠른 시작

요구: **Python 3.10+**, 표준 라이브러리만 (두 엔진 공통).

```bash
git clone https://github.com/qquartsco-svg/Planet_Fluid.git
cd Planet_Fluid
python examples/run_planet_fluid_demo.py
```

개별 엔진 테스트:

```bash
cd Eurus_Engine && python -m pytest tests/ -q
cd ../Oceanus_Engine && python -m pytest tests/ -q
```

전체 점검(테스트 + 무결성 + 캐시 정리):

```bash
python scripts/release_check.py
```

---

## 무결성 (“블록체인 서명”)

- 상세: [BLOCKCHAIN_INFO.md](BLOCKCHAIN_INFO.md) · English: [BLOCKCHAIN_INFO_EN.md](BLOCKCHAIN_INFO_EN.md)
- 소스·문서 변경 후:

```bash
python scripts/regenerate_signature.py
python scripts/verify_signature.py
```

---

## 엔진별 문서

- 대기: [Eurus_Engine/README.md](Eurus_Engine/README.md) · [Eurus_Engine/README_EN.md](Eurus_Engine/README_EN.md)
- 해양: [Oceanus_Engine/README.md](Oceanus_Engine/README.md) · [Oceanus_Engine/README_EN.md](Oceanus_Engine/README_EN.md)

---

*Planet_Fluid v1.0.0 — 관측·스크리닝 목적의 유체 코어 쌍이며, 확정적 행성 진리를 주장하지 않는다.*
