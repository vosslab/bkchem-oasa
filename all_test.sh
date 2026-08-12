#!/bin/bash

set -eu

source source_me.sh
python3 -m pytest -q \
	tests/ \
	packages/oasa/tests/ \
	packages/bkchem-app/tests/ \
	packages/bkchem-qt.app/tests/
