from tests.fakes import FakeMpv


def test_loadfile_records_and_applies_extra():
    m = FakeMpv()
    m.loadfile("/v/a.mp4", {"loop-file": "inf"})
    assert m.loaded == "/v/a.mp4"
    assert m.props["loop-file"] == "inf"
    assert ("loadfile", "/v/a.mp4", {"loop-file": "inf"}) in m.calls


def test_stop_clears_loaded():
    m = FakeMpv()
    m.loadfile("/v/a.mp4")
    m.stop()
    assert m.loaded is None
    assert ("stop",) in m.calls


def test_set_property_records():
    m = FakeMpv()
    m.set_property("pause", True)
    assert m.props["pause"] is True


def test_fire_end_file_invokes_callback():
    m = FakeMpv()
    seen = []
    m.on_end_file(lambda reason: seen.append(reason))
    m.fire_end_file("eof")
    assert seen == ["eof"]
