"""재생 엔진 (Phase 4).

블록의 순서 있는 큐를 백엔드가 소유하고, 화면 mpv엔 현재 파일 하나만 loadfile 한다.
- 동영상 블록: 화면 mpv 재생, 음악 채널 정지.
- 슬라이드쇼 블록: 사진 순차 표시(각 표시시간) + 선택적 배경음악. 사진 없으면 음악정보 화면.
- 재생 중 큐 편집(enqueue/remove/reorder) 시 현재 재생 블록을 정체성으로 추적해 pos 재계산.
mpv/USB 없이 FakeMpv(contracts.MpvClient) 주입으로 테스트된다.
"""
import random

from .contracts import PlayerState


class Player:
    def __init__(self, video, music, standby_image, music_screen_image, on_state_change=None, resolve_path=None):
        self.v = video
        self.m = music
        self.standby_image = standby_image
        self.music_screen_image = music_screen_image
        self.queue = []        # list[Block]
        self.order = []        # 셔플 반영된 재생 순서(원본 인덱스 목록)
        self.pos = -1          # order 상의 위치
        self.repeat = "off"
        self.shuffle = False
        self.mode = "manual"
        self.status = "standby"
        self.source_label = None
        self._photo_idx = 0
        self.on_state_change = on_state_change   # 상태 변경 콜백(SSE 방송용)
        self._resolve = resolve_path or (lambda cid: cid)  # content_id → 실제 파일 경로
        self.v.on_end_file(lambda reason: self._on_end())

    # ---- 재생 시작/이동 ----
    def play_blocks(self, blocks, source_label, repeat="off", shuffle=False, manual=True):
        self.queue = list(blocks)
        self.source_label = source_label
        self.repeat = repeat
        self.shuffle = shuffle
        self.mode = "manual" if manual else "auto"
        self._rebuild_order()
        self.pos = 0 if self.order else -1
        self._load_current()

    def next(self):
        if self.pos + 1 < len(self.order):
            self.pos += 1
            self._load_current()
        elif self.repeat == "all" and self.order:
            self.pos = 0
            self._load_current()
        # 마지막 트랙 + repeat off → 무동작(현재곡 재시작하지 않음)

    def prev(self):
        if self.pos > 0:
            self.pos -= 1
        self._load_current()

    def jump_to(self, index):
        if 0 <= index < len(self.order):
            self.pos = index
            self._load_current()

    # ---- 재생 옵션 ----
    def set_repeat(self, mode):
        self.repeat = mode

    def set_shuffle(self, on):
        cur = self._current_block()
        self.shuffle = on
        self._rebuild_order()
        self._restore_pos(cur)

    # ---- 일시정지/정지/수동복귀 ----
    def pause(self):
        self.v.set_property("pause", True)
        self.m.set_property("pause", True)
        self.status = "paused"

    def resume(self):
        self.v.set_property("pause", False)
        self.m.set_property("pause", False)
        self.status = "playing"

    def stop_to_standby(self):
        self.queue = []
        self.order = []
        self.pos = -1
        self._to_standby()

    def resume_auto(self):
        self.mode = "auto"

    # ---- 큐 편집 (현재 재생 블록 유지) ----
    def enqueue(self, blocks):
        cur = self._current_block()
        self.queue.extend(blocks)
        self._rebuild_order()
        self._restore_pos(cur)

    def remove(self, index):
        if not (0 <= index < len(self.queue)):
            return
        cur = self._current_block()
        removed = self.queue.pop(index)
        self._rebuild_order()
        if removed is cur:
            # 현재 재생 블록이 삭제됨 → 남은 큐에서 다음 것 재생(없으면 대기)
            if self.order:
                self.pos = min(self.pos, len(self.order) - 1)
                self._load_current()
            else:
                self.pos = -1
                self._to_standby()
        else:
            self._restore_pos(cur)

    def reorder(self, from_index, to_index):
        cur = self._current_block()
        b = self.queue.pop(from_index)
        self.queue.insert(to_index, b)
        self._rebuild_order()
        self._restore_pos(cur)

    # ---- 상태 ----
    def get_state(self) -> PlayerState:
        b = self._current_block()
        title = None
        if b:
            if b.kind == "video":
                title = b.video_id
            elif b.photos:
                title = b.photos[self._photo_idx][0]
            else:
                title = "음악"
        return PlayerState(
            status=self.status,
            mode=self.mode,
            repeat=self.repeat,
            shuffle=self.shuffle,
            queue_len=len(self.queue),
            current_index=self.pos,
            current_title=title,
            source_label=self.source_label,
            position_sec=0.0,   # 실시간 값은 Phase 10.2에서 mpv time-pos로 채움
            duration_sec=0.0,
        )

    # ---- 내부 ----
    def _rebuild_order(self):
        self.order = list(range(len(self.queue)))
        if self.shuffle:
            random.shuffle(self.order)

    def _index_in_queue(self, block):
        """block 객체의 큐 내 인덱스(정체성 비교). 없으면 None."""
        if block is None:
            return None
        for i, b in enumerate(self.queue):
            if b is block:
                return i
        return None

    def _restore_pos(self, block):
        """큐/순서 변경 후, 재생 중이던 block 을 계속 가리키도록 pos 재계산."""
        qi = self._index_in_queue(block)
        self.pos = self.order.index(qi) if qi is not None else -1

    def _current_block(self):
        if self.pos < 0 or self.pos >= len(self.order):
            return None
        return self.queue[self.order[self.pos]]

    def _load_current(self):
        b = self._current_block()
        if b is None:
            self._to_standby()
            return
        self.status = "playing"
        self._photo_idx = 0
        if b.kind == "video":
            self.m.stop()
            extra = {"loop-file": "inf"} if self.repeat == "one" else None
            self.v.loadfile(self._resolve(b.video_id), extra)
        else:  # slideshow
            if b.music_id:
                self.m.loadfile(self._resolve(b.music_id), {"loop-file": "inf"})
            else:
                self.m.stop()
            if b.photos:
                pid, sec = b.photos[0]
                self.v.loadfile(self._resolve(pid), {"image-display-duration": sec})
            else:
                self.v.loadfile(
                    self.music_screen_image, {"image-display-duration": "inf"}
                )

    def _to_standby(self):
        self.status = "standby"
        self.v.loadfile(self.standby_image, {"image-display-duration": "inf"})
        self.m.stop()

    def _notify(self):
        """상태 변경을 외부(웹 SSE)에 알린다. 미설정이면 무시."""
        if self.on_state_change:
            self.on_state_change()

    def _on_end(self):
        """mpv 재생 종료 이벤트: 슬라이드쇼면 다음 사진, 아니면 다음 블록.

        라우터를 거치지 않는 자동 전환이므로 여기서 on_state_change 를 호출해
        '지금 재생 중'이 즉시 갱신되게 한다(SSE).
        """
        b = self._current_block()
        if (
            b
            and b.kind == "slideshow"
            and b.photos
            and self._photo_idx < len(b.photos) - 1
        ):
            self._photo_idx += 1
            pid, sec = b.photos[self._photo_idx]
            self.v.loadfile(self._resolve(pid), {"image-display-duration": sec})
        else:
            self._advance()
        self._notify()

    def _advance(self):
        """블록 자연 종료 시 다음 블록으로(반복/셔플 규칙 적용)."""
        if self.repeat == "one":
            self._load_current()
            return
        if self.pos + 1 < len(self.order):
            self.pos += 1
            self._load_current()
            return
        if self.repeat == "all":
            if self.shuffle:
                self._rebuild_order()   # 한 바퀴 다 돌면 새로 셔플(멜론 방식)
            self.pos = 0
            self._load_current()
        else:
            self.pos = -1
            self._to_standby()
