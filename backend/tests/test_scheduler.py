import datetime as dt

from app.domain import scheduler as sc


def W(pl, days, s, e, enabled=1):
    return {
        "playlist_id": pl, "sched_type": "weekly", "weekdays": days,
        "start_time": s, "end_time": e, "enabled": enabled,
    }


def D(pl, s, e, enabled=1):
    return {
        "playlist_id": pl, "sched_type": "date_range",
        "start_dt": s, "end_dt": e, "enabled": enabled,
    }


def test_weekly_beats_date_range():
    now = dt.datetime(2026, 8, 3, 12, 30)  # 월요일 12:30
    scheds = [
        D(1, "2026-08-01 09:00", "2026-08-07 18:00"),
        W(2, "mon,tue,wed,thu,fri", "12:00", "13:00"),
    ]
    assert sc.active_playlist_id(scheds, now, default_id=9) == 2


def test_date_range_when_no_weekly_active():
    now = dt.datetime(2026, 8, 3, 15, 0)  # 점심시간 아님
    scheds = [
        D(1, "2026-08-01 09:00", "2026-08-07 18:00"),
        W(2, "mon,tue,wed,thu,fri", "12:00", "13:00"),
    ]
    assert sc.active_playlist_id(scheds, now, default_id=9) == 1


def test_default_when_nothing_active():
    now = dt.datetime(2026, 9, 1, 10, 0)
    assert sc.active_playlist_id([], now, default_id=9) == 9


def test_none_when_no_default():
    now = dt.datetime(2026, 9, 1, 10, 0)
    assert sc.active_playlist_id([], now, default_id=None) is None


def test_weekly_end_time_is_exclusive():
    now = dt.datetime(2026, 8, 3, 13, 0)  # 13:00 정각 = 종료 → 비활성
    scheds = [W(2, "mon", "12:00", "13:00")]
    assert sc.active_playlist_id(scheds, now, default_id=9) == 9


def test_weekly_wrong_day_inactive():
    now = dt.datetime(2026, 8, 2, 12, 30)  # 일요일
    scheds = [W(2, "mon,tue,wed,thu,fri", "12:00", "13:00")]
    assert sc.active_playlist_id(scheds, now, default_id=9) == 9


def test_disabled_schedule_ignored():
    now = dt.datetime(2026, 8, 3, 12, 30)
    scheds = [W(2, "mon", "12:00", "13:00", enabled=0)]
    assert sc.active_playlist_id(scheds, now, default_id=9) == 9


def test_overlap_same_type_weekly():
    existing = [W(2, "mon,tue", "12:00", "13:00")]
    assert sc.overlaps_same_type(existing, W(3, "tue,wed", "12:30", "13:30")) is True
    assert sc.overlaps_same_type(existing, W(3, "wed", "12:30", "13:30")) is False


def test_overlap_different_type_allowed():
    existing = [D(1, "2026-08-01 00:00", "2026-08-07 00:00")]
    # 다른 타입(weekly)은 겹쳐도 겹침으로 보지 않음(우선순위로 해결)
    assert sc.overlaps_same_type(existing, W(2, "mon", "12:00", "13:00")) is False
