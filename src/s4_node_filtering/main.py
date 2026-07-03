import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg
from src.s4_node_filtering.llm_filter import get_node_schema, get_llm_filtered_properties, apply_property_filter, save_config

def main():
    load_dotenv()
    
    # Stage 4 Input: NODE_FILTERED_GRAPH_DIR (from Stage 3)
    node_filtered_graph_uri = os.getenv("NODE_FILTERED_GRAPH_BOLT_URI", "bolt://localhost:8089")
    node_filtered_graph_user = os.getenv("NODE_FILTERED_GRAPH_USERNAME", "neo4j")
    node_filtered_graph_password = os.getenv("NODE_FILTERED_GRAPH_PASSWORD", "password")
    node_filtered_graph_dir = os.getenv("NODE_FILTERED_GRAPH_DIR")
    
    # Metagraph Target
    node_filtered_metagraph_uri = os.getenv("NODE_FILTERED_METAGRAPH_BOLT_URI", "bolt://localhost:8090")
    node_filtered_metagraph_user = os.getenv("NODE_FILTERED_METAGRAPH_USERNAME", "neo4j")
    node_filtered_metagraph_password = os.getenv("NODE_FILTERED_METAGRAPH_PASSWORD", "password")
    
    # Clone Target (Stage 5 Input)
    edge_filtered_graph_dir = os.getenv("EDGE_FILTERED_GRAPH_DIR")
    
    # LLM Config
    model_name = os.getenv("MODEL_QWEN", "Qwen 3.6 35B")
    base_url = os.getenv("BASE_URL", "https://llm.bi.denbi.de/v1")
    api_key = os.getenv("API_KEY")

    print(f"Connecting to Node Filtered Graph at {node_filtered_graph_uri}...")
    target_driver = GraphDatabase.driver(node_filtered_graph_uri, auth=(node_filtered_graph_user, node_filtered_graph_password))
    
    print("Running Primary Operation: Node Property Filtering via LLM")
    with target_driver.session() as session:
        schema = get_node_schema(session)
        
    filtered_schema = get_llm_filtered_properties(schema, model_name, base_url, api_key)
    
    save_config(filtered_schema, "config/s4_node_filtering")
    print(f"Saved LLM filtering config to config/s4_node_filtering/filtered_properties.json")

    with target_driver.session() as session:
        apply_property_filter(session, schema, filtered_schema)

    print(f"Connecting to Node Filtered Metagraph at {node_filtered_metagraph_uri}...")
    metagraph_driver = GraphDatabase.driver(node_filtered_metagraph_uri, auth=None)

    print("Generating metagraph...")
    migrate_metagraph(target_driver, metagraph_driver)

    print(f"Cloning Node Filtered Graph to Stage 5 EDGE_FILTERED_GRAPH_DIR: {edge_filtered_graph_dir}")
    clone_kg(node_filtered_graph_dir, edge_filtered_graph_dir)
    print("Stage 4 complete.")

if __name__ == "__main__":
    main()
