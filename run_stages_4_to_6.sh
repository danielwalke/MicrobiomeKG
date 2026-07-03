#!/bin/bash
set -e

wait_for_neo4j() {
  local port=$1
  echo "Waiting for Neo4j on port $port..."
  while ! wget --no-verbose --tries=1 --spider localhost:$port 2>/dev/null; do
    sleep 5
  done
  echo "Neo4j is up on port $port!"
  sleep 5
}

run_stage() {
  local module_name=$1
  local dir_path="src/${module_name#src.}"
  local desktop_port=$2
  local meta_desktop_port=$3

  echo "==========================================="
  echo "Starting Stage: $module_name"
  echo "==========================================="
  
  cd /mnt/vdb/daniel/git/MicrobiomeKG/$dir_path
  docker compose up -d
  docker compose -f meta-docker-compose.yml up -d
  
  wait_for_neo4j $desktop_port
  wait_for_neo4j $meta_desktop_port
  
  cd /mnt/vdb/daniel/git/MicrobiomeKG
  echo "Running main.py for $module_name..."
  PYTHONPATH=. python3 -m $module_name.main
  echo "Completed Stage: $module_name"
}

set -a
source /mnt/vdb/daniel/git/MicrobiomeKG/.env
set +a

# Since Stage 4 will modify NODE_FILTERED_GRAPH_DIR (which was already cloned perfectly by Stage 3),
# we don't need to re-run Stage 3. We can just execute from Stage 4 onwards.
run_stage "src.s4_node_filtering" $NODE_FILTERED_GRAPH_DESKTOP_PORT $NODE_FILTERED_METAGRAPH_DESKTOP_PORT
run_stage "src.s5_edge_filtering" $EDGE_FILTERED_GRAPH_DESKTOP_PORT $EDGE_FILTERED_METAGRAPH_DESKTOP_PORT
run_stage "src.s6_accessions" $FINAL_GRAPH_DESKTOP_PORT $FINAL_METAGRAPH_DESKTOP_PORT

echo "All remaining stages successfully triggered and completed."
