FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir neo4j==6.1.0 python-dotenv==1.2.2

# Build context is the repo root (see pipeline-docker-compose.yml) so main.py's
# namespace-package imports (src.utils.*, src.s3_propagation.*) resolve the same way
# they do when run on the host via `PYTHONPATH=. python3 -m src.s3_propagation.main`.
COPY src/s4_node_filtering/main.py
COPY src/s4_node_filtering/llm_filter.py
COPY src/s4_node_filtering/entrypoint.sh

RUN chmod +x src/s4_node_filtering/entrypoint.sh
ENTRYPOINT ["./src/s4_node_filtering/entrypoint.sh"]