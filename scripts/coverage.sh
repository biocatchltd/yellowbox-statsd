#!/bin/sh
set -e
coverage run --branch --context=ut --include="yellowbox_statsd/*" -m pytest tests/unittest "$@"
coverage run -a --branch --context=blackbox --include="yellowbox_statsd/*" -m pytest tests/blackbox "$@"
coverage html
coverage report -m
coverage xml