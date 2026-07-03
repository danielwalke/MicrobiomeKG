CONTAINERS=(
  "neo4j-raw-metagraph"
  "neo4j-mapped-graph"
  "neo4j-mapped-metagraph"
  "neo4j-propagation-graph"
  "neo4j-propagation-metagraph"
  "neo4j-node-filtered-graph"
  "neo4j-node-filtered-metagraph"
  "neo4j-edge-filtered-graph"
  "neo4j-edge-filtered-metagraph"
  "neo4j-final-graph"
  "neo4j-final-metagraph"
)

for container in "${CONTAINERS[@]}"; do
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${container}\$"; then
    echo "Stopping and removing ${container}..."
    docker stop "${container}" >/dev/null 2>&1 || true
    docker rm "${container}" >/dev/null 2>&1 || true
  fi
done

echo "Cleanup complete."