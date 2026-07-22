# Pidio — 프로젝트 규칙

라즈베리파이5 기반 학교 미디어 플레이어. 설계: `docs/01_설계.MD`, 구현계획: `docs/02_구현.md`.

## ⚠️ 개발 시작 전 필수: `uv sync`

Python 버전과 라이브러리는 **uv**로 관리한다. 백엔드 작업을 시작하기 전 **반드시** 아래를 먼저 실행한다:

```bash
cd backend && uv sync
```

- `git pull` 또는 브랜치 전환 후에도 **매번 `uv sync`** (다른 사람이 의존성을 바꿔 `uv.lock`이 갱신됐을 수 있음).
- `uv sync`는 `pyproject.toml` + `uv.lock`을 기준으로 가상환경을 **정확히 재현**한다 → 두 사람(CW·DJ)의 환경이 항상 동일해짐.
- 의존성 추가: `uv add <패키지>` (→ `pyproject.toml`·`uv.lock` 자동 갱신, **반드시 커밋**). 제거: `uv remove <패키지>`.
- Python 버전은 `backend/.python-version`(또는 pyproject의 `requires-python`)로 고정. uv가 해당 버전을 자동으로 받아 사용.
- `pyproject.toml`과 `uv.lock`은 **반드시 커밋**한다. `.venv/`는 커밋하지 않는다.
- **pip를 직접 쓰지 않는다** (환경 불일치 방지). 의존성은 오직 uv로만 관리.

## 스택
- 백엔드: Python 3.11+ (**uv 관리**) / FastAPI / SQLite(sqlite3, ORM 없음) / pytest
- 재생: mpv 2인스턴스(화면·음악) JSON IPC 소켓
- 프론트: Vue 3 + Vite (→ `backend/app/static` 로 빌드)
- 배포 타깃: RPi5 / Raspberry Pi OS Lite (Bookworm, 64-bit) / systemd

## 디렉토리
- `backend/` — **uv 프로젝트 루트**(`pyproject.toml`, `uv.lock`, `.python-version`).
- `backend/app/domain/` — 하드웨어 비의존 순수 로직(데이터·스캐너·재생엔진·스케줄러). mpv/USB 없이 테스트된다.
- `backend/app/web/` — FastAPI 앱·라우터·인증·SSE·업로드·스트리밍.
- `backend/app/static/` — Vue 빌드 산출물(자동 생성, 커밋 안 함).
- `frontend/` — Vue 소스.
- `backend/tests/` — pytest.

## 실행 명령 (uv 기반)
- **의존성 동기화(시작 전 필수):** `cd backend && uv sync`
- 백엔드 테스트: `cd backend && uv run pytest -q`
- 백엔드 개발서버: `cd backend && uv run uvicorn app.web.main:app --reload --host 0.0.0.0`
- 의존성 추가: `cd backend && uv add <패키지>`
- 프론트 개발: `cd frontend && npm run dev`
- 프론트 빌드: `cd frontend && npm run build`

## 개발 규율
- **TDD 필수**: 실패 테스트 → 최소 구현 → 통과 → 커밋. 스텝 단위로 작게.
- **DRY / YAGNI**. 스펙에 없는 기능 임의 추가 금지.
- domain 계층은 mpv/파일시스템을 **인터페이스로 추상화**(목 주입 가능). 하드웨어 직접 호출 금지.
- 커밋 접두어: feat/fix/test/chore/docs. 자주 커밋.
- 커밋 전 `cd backend && uv run pytest -q` 통과 확인. 프론트 변경 시 `npm run build` 통과 확인.

## RPi5 배포/검증
- SSH: `ssh admin@pidio.local`
- 코드 배포: Pi에서 `git pull` → `cd backend && uv sync` → `sudo systemctl restart pidio-web`
- OS: **Raspberry Pi OS Lite (64-bit)**, 계정 `admin`, 시간대 **Asia/Seoul**(예약 재생 필수), 재생 사용자 `video`·`render` 그룹.
- mpv 출력 옵션(0.1에서 확정한 값): `--vo=gpu --gpu-context=drm`
- 실제 재생/USB/4K 확인은 반드시 Pi에서. Windows에선 mpv/USB를 목으로만 테스트.

## 소유
- CW: `backend/app/domain` 전반 + 플레이어 제어
- DJ: `backend/app/web` + `frontend`
- 공통 계약: `docs/02_구현.md` Phase 1(HTTP API 계약, PlayerController 인터페이스). 계약 변경은 상호 합의 후 문서 갱신.

## 주의
- 파일 식별은 항상 content_id(크기+부분해시), 경로 아님.
- domain 순수성 유지(웹/하드웨어 의존 금지)로 테스트 속도·병렬개발 보장.
- 절대 main 브랜치에 직접 대형 변경 금지 — 기능 브랜치 후 머지.
