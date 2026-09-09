#!/usr/bin/env bash
set -euo pipefail

for var in RAW_GRAPH_BOLT_URI; do
    if [ -z "${!var:-}" ]; then
        echo "[entrypoint] ERROR: required env var ${var} is not set" >&2
        exit 1
    fi
done

merged_dmp_path="${NCBI_MERGED_DMP_PATH:-$(pwd)/merged.dmp}"
if [ ! -f "$merged_dmp_path" ]; then
    echo "[entrypoint] ERROR: merged.dmp not found at ${merged_dmp_path} (mount it via docker-compose volumes)" >&2
    exit 1
fi

echo "[entrypoint] RAW_GRAPH_BOLT_URI=${RAW_GRAPH_BOLT_URI}"
echo "[entrypoint] NCBI_MERGED_DMP_PATH=${merged_dmp_path}"

if [ "$#" -eq 0 ]; then
    exec python NCBI_Merged_Taxonomies_Ambiguity.py
fi

exec "$@"
