# Yellowbox Statsd Changelog
## 0.1.1
### Added
* "host" parameter to control the hostname to bind to
* if a metric is not found, a listing of all available metrics will be available in the exception
* "get_*" methods to retrieve metrics without errors
* `add_datagram_callback`, `remove_datagram_callback`, `add_metric_callback`, `remove_metric_callback` methods to
add/remove callbacks for datagrams and metrics.
### Fixed
* sock timeout is now caught as well as timeout errors when polling.
## 0.1.0
* initial
