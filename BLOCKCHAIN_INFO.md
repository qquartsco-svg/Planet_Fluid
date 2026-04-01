> **한국어 (정본).** English: [BLOCKCHAIN_INFO_EN.md](BLOCKCHAIN_INFO_EN.md)

# BLOCKCHAIN_INFO — Planet_Fluid 무결성 매니페스트

## 개요

이 저장소의 **블록체인 서명**은 합의형 분산 원장이나 스마트 컨트랙트가 **아니다**.  
`SIGNATURE.sha256`에 기록된 **파일별 SHA-256 해시 목록**으로, 클론·릴리스 시점의 소스·문서 표면 변조를 빠르게 검증하기 위한 것이다.

## 범위

서명 대상은 저장소 루트 기준으로 `regenerate_signature.py`가 순회하는 모든 파일이며,  
`.git`, `__pycache__`, `.pytest_cache`, `SIGNATURE.sha256` 자체 등은 제외된다.

`Eurus_Engine/` · `Oceanus_Engine/` 하위 소스·테스트·문서가 **한 매니페스트**에 포함된다.

## 검증

```bash
python scripts/regenerate_signature.py
python scripts/verify_signature.py
# 또는: shasum -a 256 -c SIGNATURE.sha256
python scripts/release_check.py
```

## 신뢰 모델

무결성 매니페스트는 **체크섬 기반 감사 표면**이다. 비밀키 코드 서명이나 온체인 영속성을 대체하지 않는다.
