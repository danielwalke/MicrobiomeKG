FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir neo4j==6.1.0 python-dotenv==1.2.2

# Build context is the repo root (see pipeline-docker-compose.yml) so main.py's
# namespace-package imports (src.utils.migrate_metagraph, src.s1_raw_graph.AmbiguityNCBI)
# resolve the same way they do when run on the host via `PYTHONPATH=. python3 -m src.s1_raw_graph.main`.
COPY src/utils/migrate_metagraph.py src/utils/
COPY src/s1_raw_graph/AmbiguityNCBI.py src/s1_raw_graph/main.py src/s1_raw_graph/databases.txt src/s1_raw_graph/merged.dmp src/s1_raw_graph/entrypoint.sh src/s1_raw_graph/
RUN chmod +x src/s1_raw_graph/entrypoint.sh

ENTRYPOINT ["./src/s1_raw_graph/entrypoint.sh"]
