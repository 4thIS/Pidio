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
    def __init__(self, video, music, standby_image, music_screen_image, on_state_change=None, resolve_path=None, resolve_title=None):
        self.v = video
        self.m = music
        self.standby_image = standby_image
        self.music_screen_image = music_screen_image
        self.queue = []        # list[Block]
        self.order = []        # 셔플 반영된 재생 순서(원본 인덱스 목록)
        self.pos = -1          # order 상의 위치
        self.repeat = "off"
        self.shuffle = False
        self.mode = "auto"       # 부팅 시 스케줄러가 평가하도록(수동 재생 시 manual로 전환)
        self.status = "standby"
        self.source_label = None
        self.position_sec = 0.0
        self.duration_sec = 0.0
        self._photo_idx = 0
        self.on_state_change = on_state_change   # 상태 변경 콜백(SSE 방송용)
        self._resolve = resolve_path or (lambda cid: cid)  # content_id → 실제 파일 경로
        self._resolve_title = resolve_title or (lambda cid: cid)  # content_id → 표시 제목
        self.v.on_end_file(lambda reason: self._on_end(reason))

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
        was_idle = self.pos < 0 or not self.order
        cur = self._current_block()
        self.queue.extend(blocks)
        self._rebuild_order()
        if was_idle and self.order and blocks:
            new_first = len(self.queue) - len(blocks)   # 첫 새 블록의 큐 인덱스
            self.pos = self.order.index(new_first)
            self._load_current()   # 대기중이었으면 새 항목부터 바로 재생
        else:
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

    def remove_content(self, content_id):
        """content_id 를 참조하는 블록을 큐에서 정리(파일 삭제와 연동).

        - 동영상 블록: 그 content_id면 블록 제거.
        - 슬라이드쇼: 배경음악이면 무음 처리, 사진이면 그 사진만 제외.
          사진·음악이 모두 사라지면 블록 제거.
        현재 재생 블록이 사라지면 다음 블록으로(없으면 대기).
        """
        cur = self._current_block()
        kept = []
        changed = False
        for b in self.queue:
            if b.kind == "video":
                if b.video_id == content_id:
                    changed = True
                    continue
            else:  # slideshow
                if b.music_id == content_id:
                    b.music_id = None
                    changed = True
                if b.photos and any(pid == content_id for pid, _ in b.photos):
                    b.photos = [(pid, sec) for pid, sec in b.photos if pid != content_id]
                    changed = True
                if not b.music_id and not b.photos:
                    continue  # 빈 슬라이드쇼 제거
            kept.append(b)
        if not changed:
            return
        cur_gone = cur is not None and all(cur is not b for b in kept)
        self.queue = kept
        self._rebuild_order()
        if cur_gone:
            if self.order:
                self.pos = min(self.pos, len(self.order) - 1)
                self._load_current()
            else:
                self.pos = -1
                self._to_standby()
        else:
            self._restore_pos(cur)

    # ---- 상태 ----
    def get_state(self) -> PlayerState:
        b = self._current_block()
        cid = None
        if b:
            if b.kind == "video":
                cid = b.video_id
            elif b.photos:
                cid = b.photos[self._photo_idx][0]
            else:
                cid = b.music_id
        title = self._resolve_title(cid) if cid else None
        return PlayerState(
            status=self.status,
            mode=self.mode,
            repeat=self.repeat,
            shuffle=self.shuffle,
            queue_len=len(self.queue),
            current_index=self.pos,
            current_title=title,
            current_id=cid,
            source_label=self.source_label,
            position_sec=self.position_sec,
            duration_sec=self.duration_sec,
        )

    def queue_view(self):
        """재생 큐를 재생 순서대로 [{content_id, kind, current, sec}]. 큐 패널용.

        sec: 사진 블록의 표시시간(초), 사진 아니면 None.
        """
        out = []
        for i, oi in enumerate(self.order):
            b = self.queue[oi]
            sec = None
            if b.kind == "video":
                cid = b.video_id
            elif b.photos:
                cid = b.photos[0][0]
                sec = b.photos[0][1]
            else:
                cid = b.music_id
            out.append({"content_id": cid, "kind": b.kind, "current": i == self.pos, "sec": sec})
        return out

    def _primary_id(self, b):
        if b is None:
            return None
        if b.kind == "video":
            return b.video_id
        if b.photos:
            return b.photos[0][0]
        return b.music_id

    def set_queue_blocks(self, blocks):
        """큐를 새 블록 구조로 교체(라이브 편집). 재생 중이던 항목은 최대한 유지.

        - 현재 재생 블록과 '대표 content_id'가 같은 블록을 새 큐에서 찾아 이어감.
        - 그 블록의 음악/사진이 바뀌었으면 다시 로드(배경음악 시작/정지 반영).
        - 못 찾으면 처음부터(재생 중이었으면), 큐가 비면 대기화면.
        """
        was_playing = self.status == "playing"
        cur = self._current_block()
        old_primary = self._primary_id(cur)
        old_music = cur.music_id if cur else None
        old_photos = list(cur.photos) if cur else None
        self.queue = list(blocks)
        self._rebuild_order()
        if not self.order:
            self.pos = -1
            self._to_standby()
            return
        new_pos = None
        for i, oi in enumerate(self.order):
            if self._primary_id(self.queue[oi]) == old_primary:
                new_pos = i
                break
        if new_pos is None:
            self.pos = 0
            # 재생 중이었거나, 대기(standby)였다가 항목이 생기면 재생 시작
            if was_playing or old_primary is None:
                self._load_current()
            return
        self.pos = new_pos
        newb = self.queue[self.order[new_pos]]
        changed = (newb.music_id != old_music) or (list(newb.photos) != (old_photos or []))
        if was_playing and changed:
            self._load_current()

    def set_photo_duration(self, index, sec):
        """큐 index 블록(사진 슬라이드쇼)의 표시시간을 갱신."""
        if not (0 <= index < len(self.queue)):
            return
        b = self.queue[index]
        if b.kind == "slideshow" and b.photos:
            b.photos = [(pid, float(sec)) for pid, _ in b.photos]

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
        self.position_sec = 0.0
        self.duration_sec = 0.0
        self.v.set_property("pause", False)   # 이전 일시정지 상태가 남지 않게
        self.m.set_property("pause", False)
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

    def refresh_position(self):
        """현재 재생 위치/길이를 화면 mpv에서 읽어 캐시(진행바용). 이미지/유휴면 0."""
        pos = self.v.get_property("time-pos")
        dur = self.v.get_property("duration")
        self.position_sec = float(pos) if pos is not None else 0.0
        self.duration_sec = float(dur) if dur is not None else 0.0

    def _notify(self):
        """상태 변경을 외부(웹 SSE)에 알린다. 미설정이면 무시."""
        if self.on_state_change:
            self.on_state_change()

    def _on_end(self, reason="eof"):
        """mpv 재생 종료 이벤트: 슬라이드쇼면 다음 사진, 아니면 다음 블록.

        자연 종료(eof)·오류(error)에만 진행한다. loadfile 교체가 유발하는
        stop/redirect 등의 end-file은 무시해야 spurious advance(연쇄 전환)를 막는다.
        라우터를 거치지 않는 자동 전환이므로 on_state_change 로 '지금 재생 중'을 즉시 갱신(SSE).
        """
        if reason not in ("eof", "error"):
            return
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
