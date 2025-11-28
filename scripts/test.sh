#!/usr/bin/env bash
set -e

# Run unit tests for the example MCP server
cd "$(dirname "$0")/.."
python3 -m pytest -q servers/santa-clara/tests
