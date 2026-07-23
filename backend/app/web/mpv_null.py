# backend/app/web/mpv_null.py
"""개발/비-Pi 환경용 무동작 mpv 클라이언트.

CW의 Player 는 MpvClient 2개(화면·음악)를 필요로 하지만, 개발 PC엔 mpv가 없다.
NullMpv 는 MpvClient 프로토콜을 무동작으로 구현해 Player 의 큐/상태/advance 로직을
하드웨어 없이 그대로 돌린다(상태는 SSE로 브로드캐스트됨).
실제 재생은 Phase 10(Pi)에서 이 자리에 domain.mpv_ipc.MpvIpc 를 주입해 대체한다.
"""
from __future__ import annotations


class NullMpv:
    """MpvClient(Protocol) 무동작 구현."""

    def loadfile(self, path: str, extra: dict | None = None) -> None:
        pass

    def set_property(self, name: str, value) -> None:
        pass

    def command(self, *args) -> None:
        pass

    def stop(self) -> None:
        pass

    def on_end_file(self, callback) -> None:
        # 자연 종료 이벤트 소스가 없으므로 콜백만 보관(호출되지 않음).
        self._end_cb = callback
