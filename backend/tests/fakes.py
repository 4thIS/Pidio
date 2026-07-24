"""테스트용 mpv 더블 (Phase 3.2).

contracts.MpvClient 프로토콜을 구현하며, 명령을 기록하고 fire_end_file()로
'재생 끝' 이벤트를 시뮬레이션한다. Phase 4 재생엔진 테스트에서 화면/음악 mpv로 주입.
"""


class FakeMpv:
    def __init__(self):
        self.calls = []       # 모든 호출 기록 [(op, ...), ...]
        self.loaded = None    # 마지막 loadfile 경로(stop 시 None)
        self.props = {}        # set_property 로 설정된 속성
        self._end = None       # on_end_file 콜백
        self.properties = {}   # get_property 반환용(테스트)

    def loadfile(self, path, extra=None):
        self.loaded = path
        self.calls.append(("loadfile", path, extra or {}))
        if extra:
            for k, v in extra.items():
                self.props[k] = v

    def set_property(self, name, value):
        self.props[name] = value
        self.calls.append(("set", name, value))

    def command(self, *args):
        self.calls.append(("cmd",) + args)

    def stop(self):
        self.loaded = None
        self.calls.append(("stop",))

    def on_end_file(self, callback):
        self._end = callback

    def get_property(self, name, timeout=1.0):
        return self.properties.get(name)

    def fire_end_file(self, reason="eof"):
        """mpv '재생 끝' 이벤트를 흉내낸다."""
        if self._end:
            self._end(reason)
