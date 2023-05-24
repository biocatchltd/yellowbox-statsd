from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import chain, product
from typing import (
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    ItemsView,
    Iterable,
    KeysView,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    ValuesView,
    overload,
)


class MetricTags(FrozenSet[str]):
    assigned: Dict[str, FrozenSet[str]]

    def __new__(cls, tags: Iterable[str]):
        ret = super().__new__(cls, tags)  # type: ignore[arg-type, type-var]
        assigned: Dict[str, List[str]] = {}
        for tag in ret:
            key, sep, value = tag.partition(":")
            if not sep:
                continue
            assigned.setdefault(key, []).append(value)
        ret.assigned = {k: frozenset(v) for k, v in assigned.items()}
        return ret

    def __getitem__(self, key) -> FrozenSet[str]:
        return self.assigned[key]

    def get(self, key, default=None):
        return self.assigned.get(key, default)

    def keys(self) -> KeysView[str]:
        return self.assigned.keys()

    def values(self) -> ValuesView[FrozenSet[str]]:
        return self.assigned.values()

    def items(self) -> ItemsView[str, FrozenSet[str]]:
        return self.assigned.items()


DOGSTATSD_PATTERN = re.compile(
    r"(?P<name>[\w.]+)"
    r"(?P<values>(?::[+-]?[0-9][0-9.]*)+)"
    r"\|(?P<type>[a-z]+)"
    r"(?:\|@(?P<sample_rate>[0-9][0-9.]*))?"
    r"(?:\|\#(?P<tags>[a-zA-Z][\w\-:.]*(?:,[a-zA-Z][\w\-:.]*)*))?"
    r"(?:\|c:(?P<container>[a-z0-9]+))?"
    r"(?:\|T(?P<time>[0-9]+))?",
    re.X,
)


@dataclass
class Metric:
    name: str
    values: List[str]
    type: str
    sample_rate: Optional[float]
    tags: Optional[MetricTags]
    metric_timestamp: Optional[int]
    container_id: Optional[str]

    @classmethod
    def parse(cls, s: str) -> Metric:
        match = DOGSTATSD_PATTERN.fullmatch(s)
        if not match:
            raise ValueError(f"invalid metric: {s}")
        name = match.group("name")
        values = match.group("values").split(":")[1:]
        type = match.group("type")
        sample_rate_raw = match.group("sample_rate")
        sample_rate = float(sample_rate_raw) if sample_rate_raw is not None else None
        tags_raw = match.group("tags")
        tags = MetricTags(set(tags_raw.split(","))) if tags_raw is not None else None
        metric_timestamp_raw = match.group("time")
        metric_timestamp = int(metric_timestamp_raw) if metric_timestamp_raw is not None else None
        container_id = match.group("container")
        return cls(name, values, type, sample_rate, tags, metric_timestamp, container_id)


@dataclass
class CapturedMetric:
    values: List[str]
    sample_rate: Optional[float]
    tags: Optional[MetricTags]
    metric_timestamp: Optional[int]
    container_id: Optional[str]

    def tags_match(
        self, *extra_tags, tags: Union[Iterable[str], Mapping[str, str]] = (), **extra_tags_assigned
    ) -> bool:
        tags_to_match = set(chain(extra_tags, (f"{k}:{v}" for k, v in extra_tags_assigned.items())))
        if isinstance(tags, Mapping):
            tags_to_match.update(f"{k}:{v}" for k, v in tags.items())
        else:
            tags_to_match.update(tags)
        if self.tags is None:
            return not tags_to_match
        return tags_to_match.issubset(self.tags)

    @classmethod
    def from_metric(cls, metric: Metric) -> CapturedMetric:
        return cls(metric.values, metric.sample_rate, metric.tags, metric.metric_timestamp, metric.container_id)


Self = TypeVar("Self", bound="CapturedMetrics")


class CapturedMetrics(List[CapturedMetric]):
    def tags(self) -> Iterable[str]:
        s: Set[str] = set()
        for m in self:
            if m.tags is not None:
                s.update(m.tags)
        return sorted(s)

    def tag_values(self, tag: str) -> Iterable[str]:
        s: Set[str] = set()
        for m in self:
            if m.tags is not None:
                s.update(m.tags[tag])
        return sorted(s)

    def filter(
        self: Self, *extra_tags, tags: Union[Iterable[str], Mapping[str, str]] = (), **extra_tags_assigned
    ) -> Self:
        return type(self)(m for m in self if m.tags_match(*extra_tags, tags=tags, **extra_tags_assigned))

    def filter_not(
        self: Self, *extra_tags, tags: Union[Iterable[str], Mapping[str, str]] = (), **extra_tags_assigned
    ) -> Self:
        return type(self)(m for m in self if not m.tags_match(*extra_tags, tags=tags, **extra_tags_assigned))

    @overload
    def split(self: Self, tag: str) -> Dict[Optional[str], Self]:
        ...

    @overload
    def split(self: Self, tag: Tuple[str, ...]) -> Dict[Tuple[Optional[str], ...], Self]:
        ...

    def split(self: Self, tag: Union[str, Tuple[str, ...]]) -> Dict[Any, Self]:
        if isinstance(tag, str):

            def get_keys(metric: CapturedMetric):
                return metric.tags.get(tag, ()) if metric.tags is not None else ()

        else:

            def get_keys(metric: CapturedMetric):
                return product(*(metric.tags.get(t, ()) for t in tag)) if metric.tags is not None else ()

        ret: Dict[Any, Self] = {}
        for metric in self:
            keys = get_keys(metric)
            for key in keys:
                cm = ret.get(key)
                if cm is None:
                    cm = ret[key] = type(self)()
                cm.append(metric)
        return ret


class CountCapturedMetric(CapturedMetrics):
    def total(self) -> float:
        return sum(float(v) / (m.sample_rate or 1.0) for m in self for v in m.values)


class HistogramCapturedMetric(CapturedMetrics):
    def avg(self) -> float:
        total_ms = 0.0
        total_inv_sample_rate = 0.0
        for m in self:
            sample_rate = m.sample_rate or 1.0
            total_ms += sum(float(v) / sample_rate for v in m.values)
            total_inv_sample_rate += len(m.values) / sample_rate
        return total_ms / total_inv_sample_rate

    def min(self) -> float:
        return min(float(v) for m in self for v in m.values)

    def max(self) -> float:
        return max(float(v) for m in self for v in m.values)


class GaugeCapturedMetric(CapturedMetrics):
    def last(self) -> float:
        rev_values_iter = chain.from_iterable(reversed(m.values) for m in reversed(self))
        addant = 0.0
        for v in rev_values_iter:
            if v.startswith("+"):
                addant += float(v[1:])
            elif v.startswith("-"):
                addant -= float(v[1:])
            else:
                return float(v) + addant
        return addant


class SetCapturedMetric(CapturedMetrics):
    def unique(self) -> Set[float]:
        return {float(v) for m in self for v in m.values}


class CapturedMetricsCollection(Dict[Tuple[str, str], CapturedMetrics]):
    METRIC_TYPES_TO_CLASS: ClassVar[Dict[str, Type[CapturedMetrics]]] = {
        "c": CountCapturedMetric,
        "g": GaugeCapturedMetric,
        "ms": HistogramCapturedMetric,
        "h": HistogramCapturedMetric,
        "s": SetCapturedMetric,
        "d": HistogramCapturedMetric,
    }

    def append(self, metric: Metric):
        key = metric.name, metric.type
        if key not in self:
            capture_cls = self.METRIC_TYPES_TO_CLASS.get(metric.type, CapturedMetrics)
            self[key] = capture_cls()
        m = CapturedMetric.from_metric(metric)
        self[key].append(m)

    def __getitem__(self, key: Tuple[str, str]) -> CapturedMetrics:
        try:
            return super().__getitem__(key)
        except KeyError:
            if self:
                raise KeyError(
                    f"Metric {key[0]} of type {key[1]} not found, available metrics: {sorted(self.keys())}"
                ) from None
            else:
                raise

    def count(self, name: str) -> CountCapturedMetric:
        return self[name, "c"]  # type: ignore[return-value]

    def get_count(self, name: str, tags=(), **tags_kwargs) -> CountCapturedMetric:
        return self.get((name, "c"), CountCapturedMetric()).filter(
            tags=tags, **tags_kwargs
        )  # type: ignore[return-value]

    def gauge(self, name: str) -> GaugeCapturedMetric:
        return self[name, "g"]  # type: ignore[return-value]

    def get_gauge(self, name: str, tags=(), **tags_kwargs) -> GaugeCapturedMetric:
        return self.get((name, "g"), GaugeCapturedMetric()).filter(
            tags=tags, **tags_kwargs
        )  # type: ignore[return-value]

    def histogram(self, name: str) -> HistogramCapturedMetric:
        return self[name, "h"]  # type: ignore[return-value]

    def get_histogram(self, name: str, tags=(), **tags_kwargs) -> HistogramCapturedMetric:
        return self.get((name, "h"), HistogramCapturedMetric()).filter(
            tags=tags, **tags_kwargs
        )  # type: ignore[return-value]

    def set(self, name: str) -> SetCapturedMetric:
        return self[name, "s"]  # type: ignore[return-value]

    def get_set(self, name: str, tags=(), **tags_kwargs) -> SetCapturedMetric:
        return self.get((name, "s"), SetCapturedMetric()).filter(tags=tags, **tags_kwargs)  # type: ignore[return-value]

    def timing(self, name: str) -> HistogramCapturedMetric:
        return self[name, "ms"]  # type: ignore[return-value]

    def get_timing(self, name: str, tags=(), **tags_kwargs) -> HistogramCapturedMetric:
        return self.get((name, "ms"), HistogramCapturedMetric()).filter(
            tags=tags, **tags_kwargs
        )  # type: ignore[return-value]

    def distribution(self, name: str) -> HistogramCapturedMetric:
        return self[name, "d"]  # type: ignore[return-value]

    def get_distribution(self, name: str, tags=(), **tags_kwargs) -> HistogramCapturedMetric:
        return self.get((name, "d"), HistogramCapturedMetric()).filter(
            tags=tags, **tags_kwargs
        )  # type: ignore[return-value]
