## 개요
CW 담당 **백엔드 도메인 계층(Phase 2~5)** 을 완성했습니다. mpv/USB/웹 없이 **순수 로직으로 92개 테스트 전부 통과**하며, 하드웨어 비의존 원칙을 지켰습니다.

## 포함 범위
### Phase 2 — 데이터 계층
- `identity.py` — content_id(크기+앞/뒤 1MB 해시): 이름변경·이동에도 동일 식별
- `db.py` + `schema.sql` — SQLite 6테이블, FK on, init 멱등
- `media_repo.py` — upsert/available/제목/목록 (USB 탈착·재발견 시 메타 보존)
- `scanner.py` — videos/pictures/music 스캔, 타입분류, 미마운트 안전

### Phase 3 — 재생 연결
- `mpv_ipc.py` — JSON IPC(`encode_command` 순수함수 + Pi 유닉스소켓 래퍼)
- `tests/fakes.py` — FakeMpv 테스트더블(하드웨어 없이 재생 검증)

### Phase 4 — 재생 엔진
- `player.py` — 블록 큐 소유, 동영상/슬라이드쇼(+배경음악), 반복(off/all/one)·셔플,
  **재생 중 큐 편집 시 현재 블록 정체성 추적**(remove/reorder/enqueue 정합성), next 무동작 처리

### Phase 5 — 예약/조립
- `scheduler.py` — 우선순위(반복시간대형 > 날짜구간형), 겹침 검사
- `playlist_repo.py` — 플리 CRUD, 블록 왕복(도메인/직렬화), 선택→블록, 예약 겹침 시 `ScheduleConflict`
- `service.py` — `AppService`: 수동/자동 재생, 스케줄 평가, 수동↔자동 복귀

## 테스트
- `cd backend && uv run pytest -q` → **92 passed**
- 전 계층 TDD(실패 테스트 → 최소 구현 → 통과)로 작성

## 다음(별도 PR)
- Phase 8: 웹 API 라우터가 이 도메인(`AppService`·리포)을 소비
- Phase 10.2: mpv `time-pos` 실시간 관측(Pi 실기기 필요) — 계획서에 이월 메모 포함

🤖 Generated with [Claude Code](https://claude.com/claude-code)
