> **한국어 (정본).** English: [README_EN.md](README_EN.md)

# Planet_Fluid

**행성 유체 쌍(Coupled Planet Fluid)** — 대기 **Eurus_Engine** 과 해양 **Oceanus_Engine** 을 한 저장소에서 다루고, 바람 forcing으로 표층 해역을 묶는 **L1 통합 스택**이다.

GitHub 공개 저장소 이름: **`Planet_Fluid`** (`qquartsco-svg/Planet_Fluid`).  
이 레포는 **고정밀 GCM/OGCM** 이 아니라, 00_BRAIN 계열에서 쓰는 **경량·관측·브리지 친화** 유체 코어 두 개를 **동일 프레임**에 둔다.

---

## 두 엔진의 역할 (요약)

### Eurus_Engine (대기)

- **무엇을 다루는가:** 행성 대기의 **얕은 유체층 근사(SWE 계열)**, 코리올리, 지균·와도·발산, **열역학·복사·CAPE/CIN**, 대순환(Hadley 등), 기압계·전선, **기후 regime·Ω 건강**까지 포함한 **날씨·기후 스크리닝 코어**.
- **행성 독립:** `PlanetConfig` 등으로 지구·화성·금성 등 프리셋을 바꿔 **다른 행성 대기**에도 같은 골격을 적용할 수 있게 설계됨(정밀도는 스크리닝 수준).
- **브리지:** TerraCore / Lucifer / JOE·MOE / Cherubim 등 **형제 스택과 덕 타이핑 연결**이 전제(상세는 `Eurus_Engine/docs/`, README).

### Oceanus_Engine (해양 · “오셔너스”)

- **무엇을 다루는가:** **표층 해양**을 2D SWE 격자(η, H, u, v, 코리올리, **바람 응력**)로 갱신하고, **열염(thermohaline)**, **조석(M2/S2/K1/O1 등)**, **해저·판 경계 훅**, 연안·항로 유틸, **Ω 스타일 해양 건강**까지 **L0~L6 레이어**로 정리한 **해양 상태 필드 코어**.
- **선박 자율과의 관계:** “배의 두뇌”가 아니라 **배가 떠 있는 바다 자체**의 상태·예측 프레임을 넘기는 쪽에 가깝다.
- **브리지:** `eurus_wind_adapter`(대기→바람), Marine Autonomy·design_workspace 노드 등 **외부 스택 소비**를 전제(상세는 Oceanus README).

---

## 유체역학적 공통점과 차이

| 구분 | 공통 | Eurus 쪽 강조 | Oceanus 쪽 강조 |
|------|------|---------------|-----------------|
| **L1 골격** | 회전 좌표계·SWE류 **2D 유체 업데이트** | 대기층 두께·기압·습도·복사·순환 | 해수층 두께·**바람 응력**·저해상 |
| **열** | 단순/프록시 열역학 | 건습윤 단열·OLR·일사 등 **대기 에너지 루프** | 선형 EOS·**thermohaline** 집계 |
| **외력·경계** | 코리올리 | 전선·기압계·jet | **조석**, 해저 경사, 판 이벤트 훅 |

Planet_Fluid에서의 **결합**은 위 표의 Oceanus 열 **“바람 응력”** 행에 해당한다: Eurus가 준 **표층 풍(u, v)** 을 Oceanus가 **동일 API**로 받는다.

---

## 확장성 · 활용성

- **의존성:** 두 엔진 모두 **표준 라이브러리만**, `requires-python >= 3.10` (각 `pyproject.toml`과 일치).
- **덕 타이핑:** Oceanus는 Eurus 패키지 없이도 동작; 대기는 **임의 (u, v)** 또는 **FluidCell/WeatherAgent 유사 객체**로 주입 가능.
- **모노레포:** 형제 폴더 + `examples/run_planet_fluid_demo.py` 의 `sys.path` 패턴 → CI·에이전트·다른 레포에서 **서브트리/복사**하기 쉬움.
- **`planet_fluid/`:** 현재는 **`__version__` 등 메타**와 문서상 **통합 facade 예약**; 향후 `python -m planet_fluid...` 형 **단일 진입점**을 두어도 하위 엔진 폴더 구조는 유지 가능.
- **동기화:** `_staging` 정본 → `scripts/sync_from_staging.sh` 로 공개본을 맞춘 뒤 **루트 `SIGNATURE.sha256` 재생성**까지 한 번에.

---

## 한계 (스코프를 넘지 않기)

- **GCM/OGCM 급이 아님:** 해상도·물리·자료동화·검증 체계가 **운용 예측**을 대체하지 않는다.
- **결합은 MVP:** **단방향 풍 forcing**만 공식 경로; 증발·강수·감열·염분 피드백 등 **양방향 플럭스**는 구현 범위 밖이다.
- **공간 균일성:** 데모는 어댑터를 통해 격자에 **균일 풍**을 넣는 패턴이 중심이다. 셀별 공간 변동 풍장은 **별도 파이프**(격자 루프·재분석 필드)로 확장해야 한다.
- **정밀 항해/안전:** 해양·대기 수치는 **screening·설계 입력**용이며, 실선 운항 인증·법적 책임을 대신하지 않는다.

---

## 앞으로의 방향 (로드맵 후보)

1. **공간 가변 forcing:** Eurus 격자/셀과 Oceanus 격자 간 **보간·타일 매핑** (커플링 레이어를 `planet_fluid` 또는 전용 모듈로).
2. **양방향 피드백(선택):** SST → 대기 경계층, 증발·강수·염분 최소 모델 등 **단계적 추가** (여전히 “경량” 유지할지 명시).
3. **통합 CLI / 틱:** `first_orbital_tick` 유사 **Planet Fluid Tick** 스크립트(데모·테스트·서명 순회).
4. **패키징:** 루트 `pyproject` 또는 **workspace 메타**로 `pip install -e` 경로 문서화(선택).
5. **문서:** GitHub **About** 설명·토픽·릴리스 태그는 저장소 설정에서 별도 권장(코드와 무관).

---

## 레이아웃

```
Planet_Fluid/
├── Eurus_Engine/          ← 행성 대기 (SWE, 순환, 전선, Ω 기후·건강)
├── Oceanus_Engine/        ← 행성 해양 (SWE 표층, 열염, 조석, 해저·판 훅)
├── planet_fluid/          ← 우산 패키지(메타/버전 노출, 통합 facade 예약)
├── examples/
│   └── run_planet_fluid_demo.py   ← Eurus FluidCell → Oceanus 격자 1틱
├── scripts/
│   ├── regenerate_signature.py
│   ├── verify_signature.py
│   ├── release_check.py
│   ├── cleanup_generated.py
│   └── sync_from_staging.sh
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

현재 결합 수준은 **단방향 MVP (Eurus → Oceanus wind forcing)** 이다.  
양방향 열·수분·염분 피드백 coupling은 후속 확장 범위다.

---

## 활용 포인트 (스크리닝)

- 대기 바람이 해양 표층 전단·응력에 주는 1차 영향 관측
- 행성 기후-해양 개념 coupling 데모/교육
- 해류 기반 항로·운용 의사결정의 입력장 생성
- Element_Capture_Foundation 연동 전 환경 스캐닝 전처리

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

원본 `_staging` 엔진(Eurus/Oceanus) 변경분 동기화:

```bash
bash scripts/sync_from_staging.sh --dry-run  # 반영 예정 변경 미리 보기
bash scripts/sync_from_staging.sh            # 실제 동기화 + 루트 서명 갱신
```

동기화는 **`Eurus_Engine/README*.md`**, **`Oceanus_Engine/README*.md`** 를 **덮어쓰지 않는다**(Planet_Fluid 전용 문서 유지). 업스트림 README 변경을 반영하려면 수동 병합한다.

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
