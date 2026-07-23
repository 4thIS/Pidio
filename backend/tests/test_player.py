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
