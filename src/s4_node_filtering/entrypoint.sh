set -euo pipefail

for var in PROPAGATED_GRAPH_BOLT_URI NODE_FILTERED_GRAPH_DIR EDGE_FILTERED_GRAPH_DIR API_KEY; do
    if [ -z "${!var:-}" ]; then
        echo "[entrypoint] ERROR: required env var ${var} is not set" >&2
        exit 1
    fi
done

echo "[entrypoint] NODE_FILTERED_GRAPH_DIR=${NODE_FILTERED_GRAPH_DIR}"
echo "[entrypoint] EDGE_FILTERED_GRAPH_DIR=${EDGE_FILTERED_GRAPH_DIR}"
echo "[entrypoint] Running s3_propagation.main (node filtering against s4_neo4j, then clone to EDGE_FILTERED_GRAPH_DIR)..."
exec python3 -m src.s3_propagation.main