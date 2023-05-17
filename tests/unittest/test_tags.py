from yellowbox_statsd.metrics import MetricTags


def test_metric_tags():
    tags = MetricTags(["tag1:a", "tag2", "tag3:b", "tag1:b", "tag2", "tag3"])
    dict_to_match = {
        "tag1": frozenset(["a", "b"]),
        "tag3": frozenset(["b"]),
    }
    assert tags == frozenset(["tag1:a", "tag2", "tag3:b", "tag1:b", "tag3"])
    assert tags["tag1"] == frozenset(["a", "b"])
    assert tags.get("tag1") == frozenset(["a", "b"])
    assert tags.get("tag2") is None
    assert "tag1:a" in tags
    assert "tag1:b" in tags
    assert "tag1" not in tags
    assert "tag2" in tags
    assert tags["tag3"] == frozenset(["b"])
    assert "tag3:b" in tags

    assert set(tags.keys()) == set(dict_to_match.keys())
    assert set(tags.values()) == set(dict_to_match.values())
    assert set(tags.items()) == set(dict_to_match.items())
