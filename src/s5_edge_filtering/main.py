import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg
from src.s5_edge_filtering.llm_filter import combine_duplicate_edges, get_edge_schema, get_llm_filtered_edge_properties, apply_edge_property_filter, save_config

def main():
    load_dotenv()
    
    # Stage 5 Input: EDGE_FILTERED_GRAPH_DIR (from Stage 4)
    edge_filtered_graph_uri = os.getenv("EDGE_FILTERED_GRAPH_BOLT_URI", "bolt://localhost:8091")
    edge_filtered_graph_user = os.getenv("EDGE_FILTERED_GRAPH_USERNAME", "neo4j")
    edge_filtered_graph_password = os.getenv("EDGE_FILTERED_GRAPH_PASSWORD", "password")
    edge_filtered_graph_dir = os.getenv("EDGE_FILTERED_GRAPH_DIR")
    
    # Metagraph Target
    edge_filtered_metagraph_uri = os.getenv("EDGE_FILTERED_METAGRAPH_BOLT_URI", "bolt://localhost:8092")
    edge_filtered_metagraph_user = os.getenv("EDGE_FILTERED_METAGRAPH_USERNAME", "neo4j")
    edge_filtered_metagraph_password = os.getenv("EDGE_FILTERED_METAGRAPH_PASSWORD", "password")
    
    # Clone Target (Stage 6 Input)
    final_graph_dir = os.getenv("FINAL_GRAPH_DIR")
    
    # LLM Config
    model_name = os.getenv("MODEL_QWEN", "Qwen 3.6 35B")
    base_url = os.getenv("BASE_URL", "https://llm.bi.denbi.de/v1")
    api_key = os.getenv("API_KEY")

    print(f"Connecting to Edge Filtered Graph at {edge_filtered_graph_uri}...")
    target_driver = GraphDatabase.driver(edge_filtered_graph_uri, auth=(edge_filtered_graph_user, edge_filtered_graph_password))
    
    with target_driver.session() as session:
        print("Combining duplicate edges...")
        combine_duplicate_edges(session)
        
        print("Running Edge Property Filtering via LLM...")
        schema = get_edge_schema(session)
        
    filtered_schema = get_llm_filtered_edge_properties(schema, model_name, base_url, api_key)
    
    save_config(filtered_schema, "config/s5_edge_filtering")
    print("Saved LLM filtering config to config/s5_edge_filtering/filtered_edges.json")

    with target_driver.session() as session:
        apply_edge_property_filter(session, schema, filtered_schema)

    print(f"Connecting to Edge Filtered Metagraph at {edge_filtered_metagraph_uri}...")
    metagraph_driver = GraphDatabase.driver(edge_filtered_metagraph_uri, auth=None)

    print("Generating metagraph...")
    migrate_metagraph(target_driver, metagraph_driver)

    print(f"Cloning Edge Filtered Graph to Stage 6 FINAL_GRAPH_DIR: {final_graph_dir}")
    clone_kg(edge_filtered_graph_dir, final_graph_dir)
    print("Stage 5 complete.")

if __name__ == "__main__":
    main()
