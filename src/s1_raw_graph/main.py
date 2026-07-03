import os
import subprocess
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg

def main():
    load_dotenv()
    
    # 1. Primary Operation: For s1, the raw graph is already started by Java application.
    raw_graph_uri = os.getenv("RAW_GRAPH_BOLT_URI")
    raw_graph_user = os.getenv("RAW_GRAPH_USERNAME")
    raw_graph_password = os.getenv("RAW_GRAPH_PASSWORD")
    raw_graph_dir = os.getenv("RAW_GRAPH_DIR")
    
    mapped_graph_dir = os.getenv("MAPPED_GRAPH_DIR")

    raw_metagraph_uri = os.getenv("RAW_METAGRAPH_BOLT_URI")
    raw_metagraph_user = os.getenv("RAW_METAGRAPH_USERNAME")
    raw_metagraph_password = os.getenv("RAW_METAGRAPH_PASSWORD")
    
    print(f"Connecting to Raw Graph at {raw_graph_uri}...")
    source_driver = GraphDatabase.driver(raw_graph_uri, auth=(raw_graph_user, raw_graph_password))
    
    print(f"Connecting to Raw Metagraph at {raw_metagraph_uri}...")
    # NOTE: Assuming the neo4j-raw-metagraph container is already running.
    # We use auth=None because docker-compose specifies NEO4J_AUTH=none.
    metagraph_driver = GraphDatabase.driver(raw_metagraph_uri, auth=None)

    # 2. Metagraph Generation
    print("Generating metagraph...")
    migrate_metagraph(source_driver, metagraph_driver)

    # 3. Clone
    print(f"Cloning Raw Graph to Stage 2 MAPPED_GRAPH_DIR: {mapped_graph_dir}")
    clone_kg(raw_graph_dir, mapped_graph_dir)
    print("Stage 1 complete.")

if __name__ == "__main__":
    main()
