"""mpv JSON IPC 클라이언트 (Phase 3.1 + 10.2 보강).

- encode_command(): 명령 한 줄 직렬화(request_id 옵션).
- MpvIpc: 유닉스 소켓 제어. 스레드 락, get_property(응답 상관), 자동 재연결 포함.
  소켓 부분은 Linux(파이) 전용 — Windows 단위테스트는 encode_command만 검증하고
  도메인 로직은 FakeMpv(contracts.MpvClient)로 테스트한다.
"""
import itertools
import json
import socket
import threading
import time


def encode_command(args: list, request_id=None) -> str:
    obj = {"command": args}
    if request_id is not None:
        obj["request_id"] = request_id
    return json.dumps(obj) + "\n"


class MpvIpc:
    """단일 mpv 인스턴스를 유닉스 소켓으로 제어(contracts.MpvClient 구현).

    - _send는 락으로 보호(웹 동시 요청 안전).
    - mpv가 죽었다 살아나면 monitor 스레드가 소켓을 자동 재연결.
    - get_property는 request_id로 응답을 상관해 값을 읽음(진행바 time-pos용).
    """

    def __init__(self, sock_path: str):
        self.sock_path = sock_path
        self._end_cb = None
        self._sock = None
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        self._pending: dict = {}   # request_id -> [Event, result]
        self._stop = False

    # ---- 연결/재연결 ----
    def connect(self) -> None:
        self._open()
        threading.Thread(target=self._monitor, daemon=True).start()

    def _open(self) -> bool:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.sock_path)
        except OSError:
            self._sock = None
            return False
        self._sock = s
        threading.Thread(target=self._reader, args=(s,), daemon=True).start()
        return True

    def _monitor(self) -> None:
        while not self._stop:
            if self._sock is None:
                self._open()   # mpv 재기동 시 소켓 복구
            time.sleep(2)

    def _reader(self, sock) -> None:
        buf = b""
        try:
            for chunk in iter(lambda: sock.recv(4096), b""):
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        continue
                    rid = msg.get("request_id")
                    if rid is not None and rid in self._pending:
                        slot = self._pending.get(rid)
                        if slot:
                            slot[1] = msg.get("data")
                            slot[0].set()
                    elif msg.get("event") == "end-file" and self._end_cb:
                        self._end_cb(msg.get("reason"))
        except OSError:
            pass
        finally:
            if self._sock is sock:
                self._sock = None   # 끊김 → monitor가 재연결

    # ---- 전송 ----
    def _send_line(self, line: str) -> bool:
        if self._sock is None:
            return False
        with self._lock:
            try:
                self._sock.sendall(line.encode())
                return True
            except OSError:
                self._sock = None
                return False

    def _send(self, args) -> None:
        self._send_line(encode_command(args))

    # ---- contracts.MpvClient ----
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

    def get_property(self, name, timeout: float = 1.0):
        """mpv 속성값을 읽어 반환(없거나 타임아웃이면 None). time-pos/duration용."""
        if self._sock is None:
            return None
        rid = next(self._ids)
        ev = threading.Event()
        self._pending[rid] = [ev, None]
        if not self._send_line(encode_command(["get_property", name], request_id=rid)):
            self._pending.pop(rid, None)
            return None
        ok = ev.wait(timeout)
        slot = self._pending.pop(rid, None)
        return slot[1] if (ok and slot) else None
