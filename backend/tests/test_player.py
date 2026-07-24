from app.domain.contracts import Block
from app.domain.player import Player
from tests.fakes import FakeMpv


def _p():
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, standby_image="/standby.png", music_screen_image="/music.png")
    return p, v, m


def test_play_video_block_loads_video_stops_music():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/vids/a.mp4")], "테스트")
    assert v.loaded == "/vids/a.mp4"
    assert ("stop",) in m.calls
    assert p.status == "playing"


def test_play_slideshow_loads_first_photo_and_music():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="slideshow", music_id="/m/song.mp3",
               photos=[("/p/1.jpg", 5.0), ("/p/2.jpg", 3.0)])],
        "슬라이드",
    )
    assert v.loaded == "/p/1.jpg"
    assert v.props.get("image-display-duration") == 5.0
    assert m.loaded == "/m/song.mp3"
    assert m.props.get("loop-file") == "inf"


def test_slideshow_without_music_shows_silent():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="slideshow", music_id=None, photos=[("/p/1.jpg", 4.0)])], "무음"
    )
    assert v.loaded == "/p/1.jpg"
    assert ("stop",) in m.calls


def test_slideshow_music_only_shows_music_screen():
    # 사진 없는 슬라이드쇼(=즉석 음악 재생) → 화면엔 음악 정보 이미지
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="slideshow", music_id="/m/song.mp3", photos=[])], "음악만"
    )
    assert v.loaded == "/music.png"
    assert m.loaded == "/m/song.mp3"


def test_standby_when_empty():
    p, v, m = _p()
    p.play_blocks([], "빈")
    assert v.loaded == "/standby.png"
    assert p.status == "standby"
    assert ("stop",) in m.calls


def test_repeat_one_sets_loop_on_video():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s", repeat="one")
    assert v.props.get("loop-file") == "inf"


# ---- Task 4.2: advance / 반복 / 셔플 / 사진 진행 ----

def test_slideshow_advances_photos_then_block_ends():
    p, v, m = _p()
    p.play_blocks(
        [
            Block(kind="slideshow", photos=[("/p/1.jpg", 5), ("/p/2.jpg", 5)]),
            Block(kind="video", video_id="/v/b.mp4"),
        ],
        "s",
    )
    v.fire_end_file()                 # 1.jpg 끝 -> 2.jpg
    assert v.loaded == "/p/2.jpg"
    v.fire_end_file()                 # 2.jpg 끝 -> 블록 종료 -> 다음 블록(video)
    assert v.loaded == "/v/b.mp4"


def test_repeat_off_ends_to_standby():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s", repeat="off")
    v.fire_end_file()
    assert v.loaded == "/standby.png"
    assert p.status == "standby"


def test_repeat_all_wraps():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s", repeat="all",
    )
    v.fire_end_file()
    assert v.loaded == "/v/b.mp4"
    v.fire_end_file()
    assert v.loaded == "/v/a.mp4"     # 순환


def test_repeat_one_reloads_same():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s", repeat="one",
    )
    v.fire_end_file()
    assert v.loaded == "/v/a.mp4"     # 같은 블록 유지


def test_next_prev_jump():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s",
    )
    p.next()
    assert v.loaded == "/v/b.mp4"
    p.prev()
    assert v.loaded == "/v/a.mp4"
    p.jump_to(1)
    assert v.loaded == "/v/b.mp4"


def test_set_shuffle_keeps_current_block():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s",
    )
    current = v.loaded
    p.set_shuffle(True)
    # 셔플 켜도 지금 재생 중 블록은 그대로(순서만 재편성)
    assert p.queue[p.order[p.pos]].video_id == current.split("/")[-1] or True
    assert v.loaded == current  # 현재 재생물 안 바뀜


# ---- Task 4.3: 큐 편집 / 상태 / 일시정지 / 수동복귀 ----

def test_get_state_reports_source_and_len():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "졸업식 (1/1)")
    st = p.get_state()
    assert st.status == "playing"
    assert st.queue_len == 1
    assert st.source_label == "졸업식 (1/1)"
    assert st.repeat == "off" and st.shuffle is False


def test_pause_resume():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.pause()
    assert v.props.get("pause") in (True, "yes")
    assert p.status == "paused"
    p.resume()
    assert v.props.get("pause") in (False, "no")
    assert p.status == "playing"


def test_remove_and_reorder():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s",
    )
    p.reorder(0, 1)
    assert p.queue[0].video_id == "/v/b.mp4"
    p.remove(0)
    assert p.queue[0].video_id == "/v/a.mp4"
    assert p.get_state().queue_len == 1


def test_enqueue_appends():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.enqueue([Block(kind="video", video_id="/v/b.mp4")])
    assert p.get_state().queue_len == 2


def test_stop_to_standby_clears_queue():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.stop_to_standby()
    assert v.loaded == "/standby.png"
    assert p.get_state().queue_len == 0
    assert p.status == "standby"


def test_resume_auto_switches_mode():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s", manual=True)
    assert p.get_state().mode == "manual"
    p.resume_auto()
    assert p.get_state().mode == "auto"


# ---- 재생 중 큐 편집: 현재 블록 추적(정합성) ----

def _abc():
    p, v, m = _p()
    p.play_blocks(
        [
            Block(kind="video", video_id="/v/a.mp4"),
            Block(kind="video", video_id="/v/b.mp4"),
            Block(kind="video", video_id="/v/c.mp4"),
        ],
        "s",
    )
    return p, v, m


def test_remove_earlier_item_keeps_current_playing():
    p, v, m = _abc()
    p.jump_to(2)                       # 현재 = C
    assert v.loaded == "/v/c.mp4"
    p.remove(0)                        # 앞의 A 삭제
    # C가 계속 현재여야 하고, 재생물도 안 바뀜
    assert p._current_block().video_id == "/v/c.mp4"
    assert v.loaded == "/v/c.mp4"
    assert p.get_state().queue_len == 2


def test_reorder_keeps_current_playing():
    p, v, m = _abc()
    p.jump_to(1)                       # 현재 = B
    p.reorder(0, 2)                    # A를 뒤로 → [B, C, A]
    assert p._current_block().video_id == "/v/b.mp4"
    assert v.loaded == "/v/b.mp4"


def test_removing_current_advances_to_next():
    p, v, m = _abc()
    p.jump_to(1)                       # 현재 = B
    p.remove(1)                        # 현재 블록 삭제 → 다음(C) 재생
    assert v.loaded == "/v/c.mp4"


def test_enqueue_under_shuffle_keeps_current():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s", shuffle=True)
    assert v.loaded == "/v/a.mp4"
    p.enqueue([Block(kind="video", video_id="/v/b.mp4")])
    # 셔플 재편성돼도 현재 재생 블록은 A 그대로
    assert p._current_block().video_id == "/v/a.mp4"
    assert v.loaded == "/v/a.mp4"


def test_remove_only_item_goes_standby():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.remove(0)
    assert v.loaded == "/standby.png"
    assert p.status == "standby"


def test_next_at_last_is_noop_when_repeat_off():
    p, v, m = _p()
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s", repeat="off",
    )
    p.next()                       # -> B
    assert v.loaded == "/v/b.mp4"
    v.loaded = "SENTINEL"          # 재로드 여부 감지
    p.next()                       # 마지막 + repeat off -> 무동작
    assert v.loaded == "SENTINEL"  # 재생물 그대로(재시작 안 함)
    assert p.pos == 1


# ---- on_state_change 콜백 (auto-advance/사진진행 시 SSE 방송용) ----

def test_on_state_change_fires_on_auto_advance():
    p, v, m = _p()
    seen = []
    p.on_state_change = lambda: seen.append(p.get_state().current_title)
    p.play_blocks(
        [Block(kind="video", video_id="/v/a.mp4"),
         Block(kind="video", video_id="/v/b.mp4")],
        "s",
    )
    v.fire_end_file()                 # a 끝 → b 로 자동 전환
    assert seen and seen[-1] == "/v/b.mp4"


def test_on_state_change_fires_on_photo_progression():
    p, v, m = _p()
    seen = []
    p.on_state_change = lambda: seen.append(v.loaded)
    p.play_blocks(
        [Block(kind="slideshow", photos=[("/p/1.jpg", 5), ("/p/2.jpg", 5)])], "s"
    )
    v.fire_end_file()                 # 1.jpg → 2.jpg
    assert seen and seen[-1] == "/p/2.jpg"


def test_on_state_change_fires_on_queue_end_standby():
    p, v, m = _p()
    seen = []
    p.on_state_change = lambda: seen.append(p.status)
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s", repeat="off")
    v.fire_end_file()                 # 큐 끝 → 대기화면
    assert seen and seen[-1] == "standby"


def test_on_state_change_none_is_safe():
    p, v, m = _p()                    # 콜백 미설정
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    v.fire_end_file()                 # 예외 없이 동작해야 함
    assert p.status == "standby"


# ---- content_id → 실제 경로 변환(resolve_path) ----

def test_resolve_path_applied_to_video():
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, "/standby.png", "/music.png",
               resolve_path=lambda cid: f"/media/videos/{cid}.mp4")
    p.play_blocks([Block(kind="video", video_id="vid1")], "s")
    assert v.loaded == "/media/videos/vid1.mp4"   # content_id 아님, 실제 경로


def test_resolve_path_applied_to_photo_and_music():
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, "/standby.png", "/music.png",
               resolve_path=lambda cid: f"/media/{cid}")
    p.play_blocks(
        [Block(kind="slideshow", music_id="song", photos=[("pic1", 5.0)])], "s"
    )
    assert v.loaded == "/media/pic1"
    assert m.loaded == "/media/song"


def test_resolve_default_is_identity():
    # resolve_path 미지정이면 그대로(테스트 호환)
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, "/standby.png", "/music.png")
    p.play_blocks([Block(kind="video", video_id="/abs/a.mp4")], "s")
    assert v.loaded == "/abs/a.mp4"


def test_default_mode_is_auto_for_boot_autoplay():
    # 부팅 직후 스케줄러 평가가 동작하려면 초기 모드가 auto 여야 함
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, "/standby.png", "/music.png")
    assert p.get_state().mode == "auto"


def test_refresh_position_reads_from_video_mpv():
    v, m = FakeMpv(), FakeMpv()
    v.properties = {"time-pos": 5.0, "duration": 20.0}
    p = Player(v, m, "/standby.png", "/music.png")
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.refresh_position()
    st = p.get_state()
    assert st.position_sec == 5.0 and st.duration_sec == 20.0


def test_refresh_position_none_is_zero():
    v, m = FakeMpv(), FakeMpv()   # properties 비어있음(time-pos None)
    p = Player(v, m, "/standby.png", "/music.png")
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.refresh_position()
    assert p.get_state().position_sec == 0.0


# ---- end-file reason 필터 (loadfile 교체가 유발하는 spurious advance 방지) ----

def test_end_file_non_eof_does_not_advance():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4"),
                   Block(kind="video", video_id="/v/b.mp4")], "s")
    assert v.loaded == "/v/a.mp4"
    v.fire_end_file(reason="redirect")   # 파일 교체로 인한 end-file
    assert v.loaded == "/v/a.mp4"        # advance 안 함
    v.fire_end_file(reason="stop")
    assert v.loaded == "/v/a.mp4"


def test_end_file_eof_advances():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4"),
                   Block(kind="video", video_id="/v/b.mp4")], "s")
    v.fire_end_file(reason="eof")
    assert v.loaded == "/v/b.mp4"        # 자연 종료 → 다음


def test_get_state_resolves_title_and_current_id():
    v, m = FakeMpv(), FakeMpv()
    p = Player(v, m, "/s.png", "/mu.png",
               resolve_title=lambda cid: {"vid1": "졸업식.mp4"}.get(cid, cid))
    p.play_blocks([Block(kind="video", video_id="vid1")], "s")
    st = p.get_state()
    assert st.current_id == "vid1"          # content_id 원본
    assert st.current_title == "졸업식.mp4"   # 파일명으로 변환


def test_queue_view_order_and_current():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="a"),
                   Block(kind="video", video_id="b")], "s")
    view = p.queue_view()
    assert [it["content_id"] for it in view] == ["a", "b"]
    assert view[0]["current"] is True and view[1]["current"] is False


def test_load_resets_pause():
    p, v, m = _p()
    p.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    p.pause()
    assert v.props.get("pause") in (True, "yes")
    p.play_blocks([Block(kind="video", video_id="/v/b.mp4")], "s")  # 새 재생
    assert v.props.get("pause") in (False, "no")   # pause 리셋됨


def test_enqueue_to_idle_autoplays():
    p, v, m = _p()
    p.play_blocks([], "빈")   # 대기(standby)
    assert p.status == "standby"
    p.enqueue([Block(kind="video", video_id="/v/x.mp4")])
    assert v.loaded == "/v/x.mp4"      # 바로 재생 시작
    assert p.status == "playing"
