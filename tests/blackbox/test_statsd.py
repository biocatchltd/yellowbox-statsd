from time import sleep

from datadog.dogstatsd import DogStatsd

from yellowbox_statsd import StatsdService


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
