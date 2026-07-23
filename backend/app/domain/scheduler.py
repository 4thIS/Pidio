"""예약(스케줄) 판정 로직 (Phase 5.1).

- active_playlist_id: 현재 시각에 틀어야 할 플레이리스트 계산.
    우선순위: weekly(반복 시간대형) > date_range(날짜 구간형) > 기본 재생목록.
- overlaps_same_type: 같은 타입 예약끼리 시간이 겹치는지(저장 시 거부용).
    서로 다른 타입은 우선순위로 해결하므로 겹침으로 보지 않는다.
순수 로직 — DB/시계 없이 테스트된다.
"""
import datetime as dt

_WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _weekly_active(s, now: dt.datetime) -> bool:
    if _WD[now.weekday()] not in s["weekdays"].split(","):
        return False
    st = dt.time.fromisoformat(s["start_time"])
    en = dt.time.fromisoformat(s["end_time"])
    return st <= now.time() < en   # 종료 시각은 배타적


def _date_active(s, now: dt.datetime) -> bool:
    st = dt.datetime.fromisoformat(s["start_dt"])
    en = dt.datetime.fromisoformat(s["end_dt"])
    return st <= now < en


def active_playlist_id(schedules, now: dt.datetime, default_id):
    weekly = [
        s for s in schedules
        if s.get("enabled", 1) and s["sched_type"] == "weekly" and _weekly_active(s, now)
    ]
    if weekly:
        return weekly[0]["playlist_id"]
    dated = [
        s for s in schedules
        if s.get("enabled", 1) and s["sched_type"] == "date_range" and _date_active(s, now)
    ]
    if dated:
        return dated[0]["playlist_id"]
    return default_id


def _ranges_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def overlaps_same_type(existing, new) -> bool:
    for e in existing:
        if e["sched_type"] != new["sched_type"]:
            continue
        if new["sched_type"] == "weekly":
            if set(e["weekdays"].split(",")) & set(new["weekdays"].split(",")):
                if _ranges_overlap(
                    dt.time.fromisoformat(e["start_time"]),
                    dt.time.fromisoformat(e["end_time"]),
                    dt.time.fromisoformat(new["start_time"]),
                    dt.time.fromisoformat(new["end_time"]),
                ):
                    return True
        else:  # date_range
            if _ranges_overlap(
                dt.datetime.fromisoformat(e["start_dt"]),
                dt.datetime.fromisoformat(e["end_dt"]),
                dt.datetime.fromisoformat(new["start_dt"]),
                dt.datetime.fromisoformat(new["end_dt"]),
            ):
                return True
    return False
