from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from socket import AF_INET, SOCK_DGRAM, socket, timeout
from threading import Thread
from traceback import print_exc
from typing import Any, Iterator, List, Set

from yellowbox import YellowService
from yellowbox.utils import docker_host_name

from yellowbox_statsd.metrics import CapturedMetricsCollection, Metric


class StatsdService(YellowService):
    sock: socket

    def __init__(self, port: int = 0, buffer_size: int = 4096, polling_time: float = 0.1, host="0.0.0.0"):
        super().__init__()
        self.port = port
        self.host = host
        self.buffer_size = buffer_size
        self.polling_time = polling_time

        self.should_stop = False
        self.listening_thread = Thread(target=self._listen_loop, daemon=True, name="statsd-listener")
        self.captures: List[CapturedMetricsCollection] = []
        self.metric_callbacks: Set[Callable[[Metric], Any]] = set()
        self.datagram_callbacks: Set[Callable[[bytes], Any]] = set()

    def start(self):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.settimeout(self.polling_time)
        self.sock.bind((self.host, self.port))
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

    def add_metric_callback(self, callback: Callable[[Metric], Any]) -> None:
        self.metric_callbacks.add(callback)

    def remove_metric_callback(self, callback: Callable[[Metric], Any]) -> None:
        self.metric_callbacks.remove(callback)

    def add_datagram_callback(self, callback: Callable[[bytes], Any]) -> None:
        self.datagram_callbacks.add(callback)

    def remove_datagram_callback(self, callback: Callable[[bytes], Any]) -> None:
        self.datagram_callbacks.remove(callback)

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
            except (TimeoutError, timeout):
                continue
            except Exception:  # noqa: BLE001
                print("unexpected error when listening to statsd socket")  # noqa: T201
                print_exc()
                continue
            for dgram_callback in self.datagram_callbacks:
                try:
                    dgram_callback(data)
                except Exception:  # noqa: BLE001
                    print("unexpected error when calling datagram callback")  # noqa: T201
                    print_exc()
            try:
                metrics = [Metric.parse(line) for line in data.decode("utf-8").strip().splitlines()]
            except Exception:  # noqa: BLE001
                print("unexpected error when parsing statsd metrics")  # noqa: T201
                print_exc()
                continue
            for cap in self.captures:
                for metric in metrics:
                    cap.append(metric)

            for metric_callback in self.metric_callbacks:
                for metric in metrics:
                    try:
                        metric_callback(metric)
                    except Exception:  # noqa: BLE001
                        print("unexpected error when calling message callback")  # noqa: T201
                        print_exc()

    def container_host(self):
        uname = platform.uname().release.lower()
        if ("microsoft" in uname) and ("wsl2" in uname):
            # udp mirroring is not supported in wsl2 yet
            # https://github.com/microsoft/WSL/issues/4825
            # the inference mechanism here can by bypassed by setting the env var YB_STATSD_CONTAINER_HOST

            try:
                proc = subprocess.run(
                    ["/usr/bin/sh", "-c", r'''ip addr show eth0 | grep -oP "(?<=inet\s)\d+(\.\d+){3}"'''],  # noqa: S603
                    capture_output=True,
                    check=True,
                )
            except Exception:  # noqa: BLE001
                print("Could not get wsl host name, using default")  # noqa: T201
                print_exc()
            else:
                return proc.stdout.decode("utf-8").strip()
        return docker_host_name
