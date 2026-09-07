FROM eclipse-temurin:17-jre

RUN apt-get update && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Workspace creation / population — not needed for now, a pre-built workspace is supplied via volume ---
# COPY BioDWH2Fork/src/biodwh2-main/target/BioDWH2-v0.6.8d.jar .

# BioDWH2-Neo4j-Server-v1.3.2.jar is bind-mounted at container start (see
# docker-compose.yml's volumes: RAW_BIODWH2_GRAPH_JAR_PATH), not copied in at
# build time — it's expected to already exist at /app/BioDWH2-Neo4j-Server-v1.3.2.jar
# by the time entry_point.sh runs.

COPY entry_point.sh .
RUN chmod +x entry_point.sh
COPY load_ncbi_taxon_merged.sh .
RUN chmod +x load_ncbi_taxon_merged.sh

ENTRYPOINT ["./entry_point.sh"]
