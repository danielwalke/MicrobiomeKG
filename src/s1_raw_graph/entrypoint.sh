#!/usr/bin/env bash
set -euo pipefail

for var in RAW_GRAPH_BOLT_URI RAW_GRAPH_DIR MAPPED_GRAPH_DIR; do
    if [ -z "${!var:-}" ]; then
        echo "[entrypoint] ERROR: required env var ${var} is not set" >&2
        exit 1
    fi
done

echo "[entrypoint] RAW_GRAPH_BOLT_URI=${RAW_GRAPH_BOLT_URI}"
echo "[entrypoint] Running s1_raw_graph.main (NCBI resolution + clone to MAPPED_GRAPH_DIR)..."
exec python3 -m src.s1_raw_graph.main
