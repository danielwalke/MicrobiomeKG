FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir neo4j==6.1.0 python-dotenv==1.2.2 pydantic==2.12.5 tqdm==4.67.3

# Build context is the repo root (see pipeline-docker-compose.yml) so main.py's
# namespace-package imports (src.utils.*, src.s2_mapping.*) resolve the same way
# they do when run on the host via `PYTHONPATH=. python3 -m src.s2_mapping.main`.
# src/s2_mapping/ is copied as a whole tree (unlike s1_raw_graph's selective COPY)
# since it spans dozens of files across models/, integrations/, linking/.
COPY src/utils/migrate_metagraph.py src/utils/
COPY src/s2_mapping/ src/s2_mapping/
RUN chmod +x src/s2_mapping/entrypoint.sh

ENTRYPOINT ["./src/s2_mapping/entrypoint.sh"]
