#!/bin/sh
# run various linters
set -e
echo "running black..."
python -m ruff format .
echo "sorting import with ruff..."
python -m ruff check . --select I,F401 --fix --show-fixes