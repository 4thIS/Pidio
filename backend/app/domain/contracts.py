# backend/app/domain/contracts.py
"""도메인 계약 (Phase 1).

CW(구현)와 DJ(웹에서 호출) 모두가 준수하는 공용 타입·인터페이스.
계약 변경은 상호 합의 후 이 파일과 docs/03_api_contract.md 를 함께 갱신한다.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Literal, Optional

RepeatMode = Literal["off", "all", "one"]
PlayMode = Literal["auto", "manual"]
MediaType = Literal["video", "photo", "music"]


@dataclass
class Block:
    """재생 단위. kind='video'는 동영상 1개, kind='slideshow'는 사진들+선택 음악."""
    kind: Literal["video", "slideshow"]
    video_id: Optional[str] = None                 # kind='video'
    music_id: Optional[str] = None                 # kind='slideshow' 배경음악(None=무음)
    photos: list[tuple[str, float]] = field(default_factory=list)  # (photo_id, 표시초) 목록


@dataclass
class PlayerState:
    status: Literal["playing", "paused", "standby"]
    mode: PlayMode
    repeat: RepeatMode
    shuffle: bool
    queue_len: int
    current_index: int
    current_title: Optional[str]
    source_label: Optional[str]     # 예 "졸업식 플리 (3/12)" 또는 "전체 선택"
    position_sec: float
    duration_sec: float
    current_id: Optional[str] = None   # 현재 항목 content_id(썸네일용)


class MpvClient(Protocol):
    """단일 mpv 인스턴스 제어. 화면용/음악용 각각 주입."""
    def loadfile(self, path: str, extra: dict | None = None) -> None: ...
    def set_property(self, name: str, value) -> None: ...
    def command(self, *args) -> None: ...
    def stop(self) -> None: ...
    # end-file 이벤트 콜백 등록(자연 종료 통지)
    def on_end_file(self, callback) -> None: ...
    def get_property(self, name: str, timeout: float = 1.0): ...


class PlayerController(Protocol):
    """웹 계층이 호출하는 재생 제어 표면."""
    def get_state(self) -> PlayerState: ...
    def play_blocks(self, blocks: list[Block], source_label: str,
                    repeat: RepeatMode = "off", shuffle: bool = False,
                    manual: bool = True) -> None: ...
    def next(self) -> None: ...
    def prev(self) -> None: ...
    def jump_to(self, index: int) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop_to_standby(self) -> None: ...
    def set_repeat(self, mode: RepeatMode) -> None: ...
    def set_shuffle(self, on: bool) -> None: ...
    def enqueue(self, blocks: list[Block]) -> None: ...
    def remove(self, index: int) -> None: ...
    def reorder(self, from_index: int, to_index: int) -> None: ...
    def resume_auto(self) -> None: ...       # 수동→자동 복귀
