from asyncio import DatagramProtocol, get_running_loop, sleep as asleep
from time import sleep
from unittest.mock import MagicMock

from aiodogstatsd import Client
from datadog.dogstatsd import DogStatsd
from yellowbox.containers import create_and_pull, removing

from yellowbox_statsd import StatsdService
from yellowbox_statsd.metrics import Metric, MetricTags


def test_startup():
    with StatsdService().start() as statsd:
        assert statsd.is_alive()


def test_send_metrics():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
            dogstatsd.increment("test.counter", value=3, tags=["tag1:a", "tag3"])
            sleep(0.1)
        assert capture.count("testns.test.counter").filter(tag1="a").total() == 4
        assert capture.count("testns.test.counter").filter_not("tag2").total() == 3
        assert capture.count("testns.test.counter").filter_not(tag1="a").total() == 0
        assert set(capture.count("testns.test.counter").tags()) == {"tag1:a", "tag2", "tag3"}


def test_send_metrics_many_clients():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
            dogstatsd.increment("test.counter", value=3, tags=["tag1:a", "tag3"])

            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.increment("test.counter", tags=["tag1:a", "tag4"])
            dogstatsd.increment("test.counter", value=3, tags=["tag1:b"])

            sleep(0.1)
        assert capture.count("testns.test.counter").filter(tag1="a").total() == 5

    split = capture.count("testns.test.counter").split("tag1")
    assert split.keys() == {"a", "b"}
    assert split["a"].total() == 5
    assert split["b"].total() == 3
    assert set(capture.count("testns.test.counter").tag_values("tag1")) == {"a", "b"}


def test_repeat_split_metrics():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
            dogstatsd.increment("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.increment("test.counter", tags=["tag1:a", "tag1:b"])
            dogstatsd.increment("test.counter", value=3, tags=["tag1:b"])
            dogstatsd.increment("test.counter", value=3)

            sleep(0.1)
        assert capture.count("testns.test.counter").filter(tag1="a").total() == 5

    split = capture.count("testns.test.counter").split("tag1")
    assert split.keys() == {"a", "b"}
    assert split["a"].total() == 5
    assert split["b"].total() == 4


def test_multi_split_metrics():
    with StatsdService().start() as statsd, statsd.capture() as capture:
        dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
        dogstatsd.increment("test.counter", tags=["tag1:a", "tag2:a"])
        dogstatsd.increment("test.counter", value=3, tags=["tag1:a", "tag2:b"])
        dogstatsd.increment("test.counter", value=10, tags=["tag1:b", "tag2:a"])
        dogstatsd.increment("test.counter", value=3, tags=["tag1:b"])

        sleep(0.1)

    split = capture.count("testns.test.counter").split(("tag1", "tag2"))
    assert split.keys() == {("a", "a"), ("a", "b"), ("b", "a")}
    assert split["a", "a"].total() == 1
    assert split["a", "b"].total() == 3
    assert split["b", "a"].total() == 10


def test_gauge():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.gauge("test.counter", value=10, tags=["tag1:a", "tag2"])
            dogstatsd.gauge("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.gauge("test.counter", value=30, tags=["tag1:b", "tag3"])
            sleep(0.1)
        assert capture.gauge("testns.test.counter").filter(tag1="a").last() == 3


def test_histogram():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.histogram("test.counter", value=10, tags=["tag1:a", "tag2"])
            dogstatsd.histogram("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.histogram("test.counter", value=30, tags=["tag1:b", "tag3"])
            sleep(0.1)
        assert capture.histogram("testns.test.counter").filter(tag1="a").avg() == 13 / 2
        assert capture.histogram("testns.test.counter").filter(tag1="a").max() == 10
        assert capture.histogram("testns.test.counter").filter(tag1="a").min() == 3


def test_timing():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.timing("test.counter", value=10, tags=["tag1:a", "tag2"])
            dogstatsd.timing("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.timing("test.counter", value=30, tags=["tag1:b", "tag3"])
            sleep(0.1)
        assert capture.timing("testns.test.counter").filter(tag1="a").avg() == 13 / 2
        assert capture.timing("testns.test.counter").filter(tag1="a").max() == 10
        assert capture.timing("testns.test.counter").filter(tag1="a").min() == 3


def test_distribution():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.distribution("test.counter", value=10, tags=["tag1:a", "tag2"])
            dogstatsd.distribution("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.distribution("test.counter", value=30, tags=["tag1:b", "tag3"])
            sleep(0.1)
        assert capture.distribution("testns.test.counter").filter(tag1="a").avg() == 13 / 2
        assert capture.distribution("testns.test.counter").filter(tag1="a").max() == 10
        assert capture.distribution("testns.test.counter").filter(tag1="a").min() == 3


def test_set():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
            dogstatsd.set("test.counter", value=10, tags=["tag1:a", "tag2"])
            dogstatsd.set("test.counter", value=3, tags=["tag1:a", "tag3"])
            dogstatsd.set("test.counter", value=30, tags=["tag1:b", "tag3"])
            sleep(0.1)
        assert capture.set("testns.test.counter").filter(tag1="a").unique() == {10, 3}


def test_from_container(docker_client):
    with StatsdService().start() as statsd, statsd.capture() as capture:
        container = create_and_pull(
            docker_client,
            "debian:stable-slim",
            f'''bash -c "echo -n 'mymet:1|c' >> /dev/udp/{statsd.container_host()}/{statsd.port}"''',
        )
        container.start()
        with removing(container):
            container.wait()
            input("READY!")
            sleep(0.1)
    assert capture.count("mymet").total() == 1


def test_idle(capsys):
    with StatsdService().start() as statsd, statsd.capture() as capture:
        sleep(2)
    assert capsys.readouterr() == ("", "")
    assert capture.get_count("mymet").total() == 0
    assert capture.get_gauge("mymet").last() == 0
    assert not capture.get_histogram("mymet")
    assert not capture.get_timing("mymet")
    assert not capture.get_distribution("mymet")
    assert capture.get_set("mymet").unique() == set()


def test_dgram_callback():
    cb = MagicMock()
    with StatsdService().start() as statsd:
        statsd.add_datagram_callback(cb)
        dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
        dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
        sleep(0.1)
        cb.assert_called_once_with(b"testns.test.counter:1|c|#tag1:a,tag2\n")
        statsd.remove_datagram_callback(cb)
        dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
        sleep(0.1)
        assert cb.call_count == 1


def test_message_callback():
    cb = MagicMock()
    with StatsdService().start() as statsd:
        statsd.add_metric_callback(cb)
        dogstatsd = DogStatsd(host="localhost", port=statsd.port, namespace="testns")
        dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
        sleep(0.1)
        cb.assert_called_once_with(
            Metric("testns.test.counter", ["1"], "c", None, MetricTags(["tag1:a", "tag2"]), None, None)
        )
        statsd.remove_metric_callback(cb)
        dogstatsd.increment("test.counter", tags=["tag1:a", "tag2"])
        sleep(0.1)
        assert cb.call_count == 1


class MyProtocol(DatagramProtocol):
    def __init__(self):
        self.on_lost = get_running_loop().create_future()

    def connection_lost(self, exc) -> None:
        self.on_lost.set_result(exc)
        super().connection_lost(exc)


async def test_async_send_raw():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            loop = get_running_loop()
            transport, protocol = await loop.create_datagram_endpoint(
                protocol_factory=MyProtocol, remote_addr=("127.0.0.1", statsd.port)
            )
            transport.sendto(b"testns.test.counter:1:4|c")
            transport.close()
            await asleep(0.1)
            assert await protocol.on_lost is None
        assert capture.count("testns.test.counter").total() == 5


async def test_async_send_metrics():
    with StatsdService().start() as statsd:
        with statsd.capture() as capture:
            client = Client(host="127.0.0.1", port=statsd.port, namespace="testns")
            await client.connect()
            client.increment("test.counter")
            client.increment("test.counter", value=3)
            await client.close()
            sleep(0.1)
        assert capture.count("testns.test.counter").total() == 4
