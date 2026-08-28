FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir neo4j==6.1.0 python-dotenv==1.2.2

COPY AmbiguityNCBI.py NCBI_Merged_Taxonomies_Ambiguity.py databases.txt entrypoint.sh ./
RUN chmod +x entrypoint.sh

# merged.dmp is not baked in: it is bind-mounted at runtime (see docker-compose.yml)
# so it can be swapped for a fresh NCBI taxdump without rebuilding the image.

ENTRYPOINT ["./entrypoint.sh"]
