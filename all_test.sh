#!/bin/sh

source source_me.sh && pytest tests/ && pytest packages/oasa/tests/ && pytest packages/bkchem-app/tests/
