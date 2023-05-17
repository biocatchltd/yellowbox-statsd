from contextlib import contextmanager
from socket import AF_INET, SOCK_DGRAM, socket
from threading import Thread
from traceback import print_exc
from typing import Iterator, List

from yellowbox import YellowService

from yellowbox_statsd.metrics import CapturedMetricsCollection, Metric


class StatsdService(YellowService):
    sock: socket

    def __init__(self, port: int = 0, buffer_size: int = 4096, polling_time: float = 0.1):
        super().__init__()
        self.port = port
        self.buffer_size = buffer_size
        self.polling_time = polling_time

        self.should_stop = False
        self.listening_thread = Thread(target=self._listen_loop, daemon=True, name="statsd-listener")
        self.captures: List[CapturedMetricsCollection] = []

    def start(self):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.settimeout(self.polling_time)
        self.sock.bind(("localhost", self.port))
        if self.port == 0:
            self.port = self.sock.getsockname()[1]
        self.listening_thread.start()
        return super().start()

    def stop(self):
        self.should_stop = True
        self.listening_thread.join()
        self.sock.close()
        return super().stop()

    def is_alive(self):
        return self.sock is not None

    @contextmanager
    def capture(self) -> Iterator[CapturedMetricsCollection]:
        cap = CapturedMetricsCollection()
        self.captures.append(cap)
        try:
            yield cap
        finally:
            if self.captures.pop() is not cap:
                raise RuntimeError("capture stack is corrupted, concurrent captures are not allowed")

    def _listen_loop(self) -> None:
        while not self.should_stop:
            try:
                data: bytes = self.sock.recv(self.buffer_size)
            except TimeoutError:
                continue
            except Exception:  # noqa: BLE001
                print("unexpected error when listening to statsd socket")  # noqa: T201
                print_exc()
                continue
            try:
                metrics = [Metric.parse(line) for line in data.decode("utf-8").strip().splitlines()]
            except Exception:  # noqa: BLE001
                print("unexpected error when parsing statsd metrics")  # noqa: T201
                print_exc()
                continue
            for cap in self.captures:
                for metric in metrics:
                    cap.append(metric)
