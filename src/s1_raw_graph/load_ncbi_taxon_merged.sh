#!/bin/bash
set -euo pipefail

# Downloads NCBI's taxdump archive and extracts merged.dmp from it — the file
# consumed by AmbiguityNCBI.load_merged_dmp() / NCBI_MERGED_DMP_PATH in
# s1_raw_graph/main.py's NCBI Merged Taxonomies Resolution step.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAXDUMP_URL="https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
merged_dmp_path="${NCBI_MERGED_DMP_PATH:-${SCRIPT_DIR}/merged.dmp}"

if [ -f "$merged_dmp_path" ]; then
    echo "[load_ncbi_taxon_merged] merged.dmp already present at ${merged_dmp_path}, skipping download."
    exit 0
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

echo "[load_ncbi_taxon_merged] Downloading ${TAXDUMP_URL}..."
curl -fSL "$TAXDUMP_URL" -o "${tmp_dir}/taxdump.tar.gz"

echo "[load_ncbi_taxon_merged] Extracting merged.dmp..."
tar -xzf "${tmp_dir}/taxdump.tar.gz" -C "$tmp_dir" merged.dmp

mkdir -p "$(dirname "$merged_dmp_path")"
mv "${tmp_dir}/merged.dmp" "$merged_dmp_path"

echo "[load_ncbi_taxon_merged] NCBI_MERGED_DMP_PATH=${merged_dmp_path}"
