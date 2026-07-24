import json

from app.domain.mpv_ipc import encode_command


def test_encode_loadfile():
    line = encode_command(["loadfile", "/x.mp4", "replace"])
    assert json.loads(line) == {"command": ["loadfile", "/x.mp4", "replace"]}
    assert line.endswith("\n")  # mpv IPC는 개행으로 명령 구분


def test_encode_set_property():
    line = encode_command(["set_property", "loop-file", "inf"])
    assert json.loads(line)["command"] == ["set_property", "loop-file", "inf"]


def test_encode_preserves_types():
    # bool/number 인자가 JSON 타입으로 보존돼야 함
    line = encode_command(["set_property", "pause", True])
    assert json.loads(line)["command"] == ["set_property", "pause", True]
    line2 = encode_command(["set_property", "image-display-duration", 5.0])
    assert json.loads(line2)["command"][2] == 5.0


def test_encode_is_single_line():
    line = encode_command(["stop"])
    assert line.count("\n") == 1 and line.endswith("\n")


def test_mpvipc_commands_noop_when_not_connected():
    # 미연결 상태(connect 안 함)에서 명령을 보내도 예외 없이 무시돼야 함
    from app.domain.mpv_ipc import MpvIpc
    c = MpvIpc("/nonexistent/mpv.sock")
    c.loadfile("/x.mp4", {"loop-file": "inf"})
    c.set_property("pause", True)
    c.command("stop")
    c.stop()   # 예외 없이 통과하면 성공
