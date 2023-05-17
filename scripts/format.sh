#!/bin/sh
# run various linters
set -e
echo "running black..."
python -m black .
