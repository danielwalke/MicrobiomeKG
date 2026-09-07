# =============================================================================
# MicrobiomeKG pipeline environment
# Sourced by run_pipeline.sh (bash `source`) and by each stage's main.py
# (python-dotenv's load_dotenv()). Keep this file local — it is gitignored.
# =============================================================================

# --- Stage 1: raw graph (BioDWH2-managed) -----------------------------------
# Host path to the pre-built BioDWH2 workspace (config.json / neo4j / sources / tools).
# Bind-mounted into the container at /app/workspaces/test_workspace.
RAW_GRAPH_DIR=/mnt/vdb/benja/TrEMBL_Instance_Node_Mapping

RAW_GRAPH_DESKTOP_PORT=7474
RAW_GRAPH_BOLT_PORT=7687
RAW_GRAPH_BOLT_URI=bolt://localhost:${RAW_GRAPH_BOLT_PORT}
# TODO: confirm against the BioDWH2-Neo4j-Server's actual configured auth
# (its default may differ from a stock neo4j:latest container).
RAW_GRAPH_USERNAME=neo4j
RAW_GRAPH_PASSWORD=""

RAW_BIODWH2_GRAPH_JAR_PATH=/mnt/vdb/benja/BioDWH2_Projekts/BioDWH2-Neo4j-Server-v1.3.2.jar

# Optional override for AmbiguityNCBI's merged.dmp lookup — only needed if you
# want load_ncbi_taxon_merged.sh's download to be picked up from the mounted
# workspace instead of the copy already committed at src/s1_raw_graph/merged.dmp.
# NCBI_MERGED_DMP_PATH=${RAW_GRAPH_DIR}/merged.dmp

# Metagraph containers are currently disabled (run_pipeline.sh and main.py
# both skip them) — left here, unused, for when that gets re-enabled.
# RAW_METAGRAPH_DESKTOP_PORT=7475
# RAW_METAGRAPH_BOLT_PORT=7688
# RAW_METAGRAPH_BOLT_URI=bolt://localhost:${RAW_METAGRAPH_BOLT_PORT}
# RAW_METAGRAPH_USERNAME=
# RAW_METAGRAPH_PASSWORD=

# --- Stage 2: mapping --------------------------------------------------------
# TODO: set to a real host directory before uncommenting s2 in run_pipeline.sh.
MAPPED_GRAPH_DIR=/mnt/vdb/benja/mapped_graph
MAPPED_GRAPH_DESKTOP_PORT=7476
MAPPED_GRAPH_BOLT_PORT=7689
# MAPPED_METAGRAPH_DESKTOP_PORT=7477
# MAPPED_METAGRAPH_BOLT_PORT=7690
# MAPPED_METAGRAPH_DIR=/mnt/vdb/benja/mapped_metagraph

# --- Stage 3: propagation ----------------------------------------------------
# TODO: fill in before uncommenting s3.
# PROPAGATED_GRAPH_DIR=
# PROPAGATED_GRAPH_DESKTOP_PORT=7478
# PROPAGATED_GRAPH_BOLT_PORT=7691
# PROPAGATED_METAGRAPH_DESKTOP_PORT=7479
# PROPAGATED_METAGRAPH_BOLT_PORT=7692
# PROPAGATED_METAGRAPH_DIR=

# --- Stage 4: node filtering --------------------------------------------------
# TODO: fill in before uncommenting s4.
# NODE_FILTERED_GRAPH_DIR=
# NODE_FILTERED_GRAPH_DESKTOP_PORT=7480
# NODE_FILTERED_GRAPH_BOLT_PORT=7693
# NODE_FILTERED_METAGRAPH_DESKTOP_PORT=7481
# NODE_FILTERED_METAGRAPH_BOLT_PORT=7694
# NODE_FILTERED_METAGRAPH_DIR=

# --- Stage 5: edge filtering ---------------------------------------------------
# TODO: fill in before uncommenting s5.
# EDGE_FILTERED_GRAPH_DIR=
# EDGE_FILTERED_GRAPH_DESKTOP_PORT=7482
# EDGE_FILTERED_GRAPH_BOLT_PORT=7695
# EDGE_FILTERED_METAGRAPH_DESKTOP_PORT=7483
# EDGE_FILTERED_METAGRAPH_BOLT_PORT=7696
# EDGE_FILTERED_METAGRAPH_DIR=

# --- Stage 6: accessions (final) ----------------------------------------------
# TODO: fill in before uncommenting s6.
# FINAL_GRAPH_DIR=
# FINAL_GRAPH_DESKTOP_PORT=7484
# FINAL_GRAPH_BOLT_PORT=7697
# FINAL_METAGRAPH_DESKTOP_PORT=7485
# FINAL_METAGRAPH_BOLT_PORT=7698
# FINAL_METAGRAPH_DIR=
