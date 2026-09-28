#!/usr/bin/env bash
set -euo pipefail

for var in PROPAGATED_GRAPH_BOLT_URI PROPAGATED_GRAPH_DIR FILTERED_GRAPH_DIR; do
    if [ -z "${!var:-}" ]; then
        echo "[entrypoint] ERROR: required env var ${var} is not set" >&2
        exit 1
    fi
done

echo "[entrypoint] PROPAGATED_GRAPH_BOLT_URI=${PROPAGATED_GRAPH_BOLT_URI}"
echo "[entrypoint] Running s3_propagation.main (propagation against s3_neo4j, then clone to FILTERED_GRAPH_DIR)..."
exec python3 -m src.s3_propagation.main
