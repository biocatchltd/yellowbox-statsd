from pytest import mark

from yellowbox_statsd.metrics import (
    CapturedMetric,
    CountCapturedMetric,
    GaugeCapturedMetric,
    HistogramCapturedMetric,
    Metric,
    MetricTags,
    SetCapturedMetric,
)


@mark.parametrize("name", ["test1", "ns.bla", "35.ns_bloo"])
@mark.parametrize("values", [["35"], ["654.12"], ["+15"], ["-45.5"], ["0", "+5", "-3"]])
@mark.parametrize("type", ["c", "ms", "g", "h", "s", "d"])
@mark.parametrize("sample_rate", [None, 0.5, 1, 2])
@mark.parametrize("tags", [None, ["tag1:a", "tag2"], ["tag1:a"], ["hi"]])
@mark.parametrize("container", [None, "blabla"])
@mark.parametrize("time", [None, 1234567890])
def test_parse(name, values, type, sample_rate, tags, container, time):
    value = ":".join(values)
    s = f"{name}:{value}|{type}"
    if sample_rate is not None:
        s += f"|@{sample_rate}"
    if tags is not None:
        s += f"|#{','.join(tags)}"
    if container is not None:
        s += f"|c:{container}"
    if time is not None:
        s += f"|T{time}"
    metric = Metric.parse(s)
    assert metric.name == name
    assert metric.values == values
    assert metric.type == type
    assert metric.sample_rate == sample_rate
    assert metric.tags == (MetricTags(tags) if tags else None)
    assert metric.metric_timestamp == time
    assert metric.container_id == container


def test_metric_matches():
    captured_metric = CapturedMetric(
        ["35"], None, MetricTags(["tag1:a", "tag2", "tag3:b", "tag1:b", "tag2", "tag3"]), None, None
    )
    assert captured_metric.tags_match()
    assert captured_metric.tags_match("tag1:a", "tag2", "tag3:b")
    assert captured_metric.tags_match(tags=["tag1:a", "tag2", "tag3:b"])
    assert captured_metric.tags_match(tags={"tag1": "a", "tag3": "b"})
    assert captured_metric.tags_match("tag2", tag1="a", tag3="b")
    assert captured_metric.tags_match(tag1="a", tag3="b")
    assert not captured_metric.tags_match("tag4")
    assert not captured_metric.tags_match("tag1:c")


def test_metric_matches_empty():
    captured_metric = CapturedMetric(["35"], None, None, None, None)
    assert captured_metric.tags_match()
    assert not captured_metric.tags_match("tag1:a", "tag2", "tag3:b")
    assert not captured_metric.tags_match(tags=["tag1:a", "tag2", "tag3:b"])
    assert not captured_metric.tags_match(tags={"tag1": "a", "tag3": "b"})
    assert not captured_metric.tags_match("tag2", tag1="a", tag3="b")
    assert not captured_metric.tags_match(tag1="a", tag3="b")
    assert not captured_metric.tags_match("tag4")
    assert not captured_metric.tags_match("tag1:c")


def mk_metric(values, sample_rate):
    return CapturedMetric(values, sample_rate, None, None, None)


def test_count_capture():
    cap = CountCapturedMetric(
        [
            mk_metric(["1"], None),
            mk_metric(["2"], 0.5),
            mk_metric(["3", "7"], 0.5),
        ]
    )

    assert cap.total() == 25


def test_histogram_capture():
    cap = HistogramCapturedMetric(
        [
            mk_metric(["1"], None),
            mk_metric(["2"], 0.5),
            mk_metric(["3", "7"], 0.5),
        ]
    )

    assert cap.avg() == 25 / 7
    assert cap.min() == 1
    assert cap.max() == 7


def test_gauge_capture():
    cap = GaugeCapturedMetric(
        [
            mk_metric(["3", "+7.2"], None),
            mk_metric(["-2"], None),
            mk_metric(["+1"], None),
        ]
    )

    assert cap.last() == 9.2


def test_gauge_capture_noinit():
    cap = GaugeCapturedMetric(
        [
            mk_metric(["-3", "+7.2"], None),
            mk_metric(["-2"], None),
            mk_metric(["+1"], None),
        ]
    )

    assert cap.last() == 3.2


def test_gauge_capture_empty():
    cap = GaugeCapturedMetric([])

    assert cap.last() == 0.0


def test_set_capture():
    cap = SetCapturedMetric(
        [
            mk_metric(["1"], None),
            mk_metric(["2"], 0.5),
            mk_metric(["3", "2"], 0.5),
        ]
    )

    assert cap.unique() == {1, 2, 3}
