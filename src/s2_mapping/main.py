import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg
from src.s2_mapping.integrations.main import run_integrations
from src.s2_mapping.linking.main import main as run_linking

def main():
    load_dotenv()
    
    mapped_graph_uri = os.getenv("MAPPED_GRAPH_BOLT_URI", "bolt://localhost:8085")
    mapped_graph_user = os.getenv("MAPPED_GRAPH_USERNAME", "neo4j")
    mapped_graph_password = os.getenv("MAPPED_GRAPH_PASSWORD", "password")
    mapped_graph_dir = os.getenv("MAPPED_GRAPH_DIR")
    
    propagated_graph_dir = os.getenv("PROPAGATED_GRAPH_DIR")

    mapped_metagraph_uri = os.getenv("MAPPED_METAGRAPH_BOLT_URI", "bolt://localhost:8086")
    mapped_metagraph_user = os.getenv("MAPPED_METAGRAPH_USERNAME", "neo4j")
    mapped_metagraph_password = os.getenv("MAPPED_METAGRAPH_PASSWORD", "password")
    
    print("Running Primary Operation: Integrations")
    run_integrations()
    
    print("Running Primary Operation: Linking")
    run_linking()

    # TODO: Implement missing concept ID finder via LLM.
    print("TODO: Address missing concept mappings.")

    print(f"Connecting to Mapped Graph at {mapped_graph_uri}...")
    source_driver = GraphDatabase.driver(mapped_graph_uri, auth=(mapped_graph_user, mapped_graph_password))
    
    print(f"Connecting to Mapped Metagraph at {mapped_metagraph_uri}...")
    metagraph_driver = GraphDatabase.driver(mapped_metagraph_uri, auth=None)

    print("Generating metagraph...")
    migrate_metagraph(source_driver, metagraph_driver)

    print(f"Cloning Mapped Graph to Stage 3 PROPAGATED_GRAPH_DIR: {propagated_graph_dir}")
    clone_kg(mapped_graph_dir, propagated_graph_dir)
    print("Stage 2 complete.")

if __name__ == "__main__":
    main()
