FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir neo4j==6.1.0 python-dotenv==1.2.2

# Build context is the repo root (see pipeline-docker-compose.yml) so main.py's
# namespace-package imports (src.utils.*, src.s3_propagation.*) resolve the same way
# they do when run on the host via `PYTHONPATH=. python3 -m src.s3_propagation.main`.
COPY src/utils/migrate_metagraph.py src/utils/
COPY src/s3_propagation/delete_detach_db_nodes.py src/s3_propagation/propagate_db_edges.py src/s3_propagation/propagate_db_nodes.py src/s3_propagation/main.py src/s3_propagation/entrypoint.sh src/s3_propagation/
RUN chmod +x src/s3_propagation/entrypoint.sh

ENTRYPOINT ["./src/s3_propagation/entrypoint.sh"]
