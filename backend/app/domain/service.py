"""앱 서비스 — 도메인 조립 (Phase 5.3).

DB(playlist_repo)·Player·scheduler 를 묶어 웹 계층이 쓸 고수준 API를 제공한다.
- play_selection / play_playlist: 수동/자동 재생.
- evaluate_schedule: 자동 모드에서 현재 시각에 맞는 플리로 전환(수동이면 무시).
- resume_auto: 수동→자동 복귀 후 즉시 스케줄 재평가.
"""
import datetime as dt

from . import playlist_repo, scheduler


def _block_to_dict(b):
    """도메인 Block → update_playlist 용 dict."""
    if b.kind == "video":
        return {"kind": "video", "video_id": b.video_id}
    return {
        "kind": "slideshow",
        "music_id": b.music_id,
        "photos": [{"photo_id": pid, "duration_sec": sec} for pid, sec in b.photos],
    }


class AppService:
    def __init__(self, conn, player, now_fn=None):
        self.conn = conn
        self.player = player
        self._now = now_fn or dt.datetime.now
        self._active_playlist_id = None   # 자동 재생 중인 플리(수동이면 None)
        self.current_source_playlist_id = None  # 현재 재생 소스가 플리면 그 id(즉석선택이면 None)
        self._showing_standby = False

    # ---- 수동 재생 ----
    def play_selection(self, content_ids, repeat="off", shuffle=False):
        blocks = playlist_repo.selection_to_blocks(self.conn, content_ids)
        self.player.play_blocks(
            blocks, source_label="전체 선택", repeat=repeat, shuffle=shuffle, manual=True
        )
        self._active_playlist_id = None
        self.current_source_playlist_id = None
        self._showing_standby = False

    def play_playlist(self, playlist_id, manual=True):
        pl = playlist_repo.get_playlist(self.conn, playlist_id)
        if pl is None:
            return
        blocks = playlist_repo.blocks_of(self.conn, playlist_id)
        self.player.play_blocks(
            blocks,
            source_label=pl["name"],
            repeat=pl["repeat_mode"],
            shuffle=bool(pl["shuffle"]),
            manual=manual,
        )
        self._active_playlist_id = None if manual else playlist_id
        self.current_source_playlist_id = playlist_id
        self._showing_standby = False

    def save_queue_as_playlist(self, name):
        """현재 재생 큐(블록들)를 새 플레이리스트로 저장. 새 id 반환."""
        pid = playlist_repo.create_playlist(self.conn, name)
        blocks = [_block_to_dict(b) for b in self.player.queue]
        playlist_repo.update_playlist(
            self.conn, pid, name,
            self.player.repeat, bool(self.player.shuffle), blocks,
        )
        return pid

    # ---- 자동(스케줄) ----
    def evaluate_schedule(self, now=None):
        if self.player.mode == "manual":
            return
        now = now or self._now()
        target = scheduler.active_playlist_id(
            playlist_repo.list_schedules(self.conn), now, self._default_playlist_id()
        )
        if target is None:
            if not self._showing_standby:
                self.player.stop_to_standby()
                self._active_playlist_id = None
                self.current_source_playlist_id = None
                self._showing_standby = True
            return
        if target != self._active_playlist_id:
            self.play_playlist(target, manual=False)

    def resume_auto(self):
        self.player.resume_auto()
        self.evaluate_schedule()

    # ---- 내부 ----
    def _default_playlist_id(self):
        r = self.conn.execute(
            "SELECT value FROM settings WHERE key='default_playlist_id'"
        ).fetchone()
        return int(r["value"]) if r and r["value"] else None
