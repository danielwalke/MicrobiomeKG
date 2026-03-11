# Metagraph Setup Log

## 2026-03-10

1.  **Initialized raw_metagraph directory**: Confirmed location at `/Users/danielwalke/git/microbiomeprocheck/3_metaconceptgraph`.
2.  **Created Docker Compose**: Defined `docker-compose.yml` for the target Neo4j instance (Port 7476 for HTTP, 7689 for Bolt).
3. **Transferration script**: Concept extraction script to infer concept nodes and difefrenatiate from database nodes
 (python3 extract_concepts.py --suri bolt://localhost:7688 --suser neo4j --spass neo4j --turi bolt://localhost:7689 --tuser neo4j --tpass "")