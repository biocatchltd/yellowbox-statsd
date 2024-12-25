# Yellowbox Statsd Changelog
## NEXT
### Internal
* updated github actions
## 0.1.3
### Fixed
* slashes are now allowed in metric tags to comply with datadog standards
## 0.1.2
### Added
* `values`, `min`, `max` methods to gauge captures
* `unbunch` methods to captured metrics
* support for python 3.12 
### Fixed
* correctly check the `YB_STATSD_CONTAINER_HOST` env var
### Internal
* CI workflows
## 0.1.1
### Added
* "host" parameter to control the hostname to bind to
* if a metric is not found, a listing of all available metrics will be available in the exception
* "get_*" methods to retrieve metrics without errors
* `add_datagram_callback`, `remove_datagram_callback`, `add_metric_callback`, `remove_metric_callback` methods to
add/remove callbacks for datagrams and metrics.
* `container_host` method to retrieve the host of a container.
### Fixed
* sock timeout is now caught as well as timeout errors when polling.
## 0.1.0
* initial
