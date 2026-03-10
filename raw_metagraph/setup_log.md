# Metagraph Setup Log

## 2026-03-10

1.  **Initialized raw_metagraph directory**: Confirmed location at `/Users/danielwalke/git/microbiomeprocheck/raw_metagraph`.
2.  **Created Docker Compose**: Defined `docker-compose.yml` for the target Neo4j instance (Port 7475 for HTTP, 7688 for Bolt).
3.  **Extraction Script (In Progress)**: Developing `extract_metagraph.py` to pull schema information from the source BioDWH2 Neo4j and push it to the target container. (python3 extract_metagraph.py --suri bolt://localhost:8083 --suser neo4j --spass neo4j --turi bolt://localhost:7688 --tuser neo4j --tpass "")
