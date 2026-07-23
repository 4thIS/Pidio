"""mpv JSON IPC 클라이언트 (Phase 3.1).

- encode_command(): mpv 소켓에 보낼 JSON 한 줄 생성(순수함수, 어디서나 테스트 가능).
- MpvIpc: Pi에서 유닉스 소켓으로 mpv를 제어(AF_UNIX). 화면용/음악용 인스턴스별로 하나씩.
  소켓 부분은 Linux(파이) 전용이므로 Windows 단위테스트는 encode_command만 검증하고,
  도메인 로직은 contracts.MpvClient 프로토콜을 목(FakeMpv)으로 주입해 테스트한다.
"""
import json
import socket
import threading


def encode_command(args: list) -> str:
    """mpv IPC 명령 한 줄. 예: ["loadfile","/x.mp4","replace"] → '{"command":[...]}\n'"""
    return json.dumps({"command": args}) + "\n"


class MpvIpc:
    """단일 mpv 인스턴스를 유닉스 소켓으로 제어(contracts.MpvClient 구현).

    on_end_file 콜백은 이벤트 리더 스레드에서 호출된다.
    """

    def __init__(self, sock_path: str):
        self.sock_path = sock_path
        self._end_cb = None
        self._sock = None

    def connect(self) -> None:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)  # Pi 전용
        s.connect(self.sock_path)
        self._sock = s
        threading.Thread(target=self._reader, daemon=True).start()

    def _send(self, args) -> None:
        self._sock.sendall(encode_command(args).encode())

    def _reader(self) -> None:
        buf = b""
        for chunk in iter(lambda: self._sock.recv(4096), b""):
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("event") == "end-file" and self._end_cb:
                    self._end_cb(msg.get("reason"))

    # --- contracts.MpvClient 표면 ---
    def loadfile(self, path, extra=None) -> None:
        self._send(["loadfile", path, "replace"])
        if extra:
            for k, v in extra.items():
                self._send(["set_property", k, v])

    def set_property(self, name, value) -> None:
        self._send(["set_property", name, value])

    def command(self, *args) -> None:
        self._send(list(args))

    def stop(self) -> None:
        self._send(["stop"])

    def on_end_file(self, callback) -> None:
        self._end_cb = callback
