#!/usr/bin/env bash
set -euo pipefail

for var in MAPPED_GRAPH_BOLT_URI MAPPED_GRAPH_DIR PROPAGATED_GRAPH_DIR; do
    if [ -z "${!var:-}" ]; then
        echo "[entrypoint] ERROR: required env var ${var} is not set" >&2
        exit 1
    fi
done

echo "[entrypoint] MAPPED_GRAPH_BOLT_URI=${MAPPED_GRAPH_BOLT_URI}"
echo "[entrypoint] Running s2_mapping.main (integrations + linking against s2_neo4j, then clone to PROPAGATED_GRAPH_DIR)..."
exec python3 -m src.s2_mapping.main
