from app.domain.contracts import Block
from app.domain.player import Player
from app.web.background import position_tick
from tests.fakes import FakeMpv


class _Hub:
    def __init__(self):
        self.published = []

    def publish(self, state):
        self.published.append(state)


class _Deps:
    def __init__(self, player):
        self.player = player


def test_position_tick_publishes_position_when_playing():
    v, m = FakeMpv(), FakeMpv()
    v.properties = {"time-pos": 3.0, "duration": 10.0}
    player = Player(v, m, "/s.png", "/mu.png")
    player.play_blocks([Block(kind="video", video_id="/v/a.mp4")], "s")
    hub = _Hub()
    position_tick(_Deps(player), hub)
    assert len(hub.published) == 1
    assert hub.published[0].position_sec == 3.0
    assert hub.published[0].duration_sec == 10.0


def test_position_tick_skips_when_standby():
    v, m = FakeMpv(), FakeMpv()
    player = Player(v, m, "/s.png", "/mu.png")   # standby
    hub = _Hub()
    position_tick(_Deps(player), hub)
    assert hub.published == []
