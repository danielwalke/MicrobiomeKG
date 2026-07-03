import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.s6_accessions.llm_accessions import extract_accession_keys
from src.utils.extract_properties_markdown import extract_schema_with_samples_md
from src.utils.extract_properties_json import extract_json
from src.s6_accessions.apply_accessions import apply_accessions_to_graph

def main():
    load_dotenv()
    
    final_graph_uri = os.getenv("FINAL_GRAPH_BOLT_URI", "bolt://localhost:8093")
    final_graph_user = os.getenv("FINAL_GRAPH_USERNAME", "neo4j")
    final_graph_password = os.getenv("FINAL_GRAPH_PASSWORD", "password")
    
    final_metagraph_uri = os.getenv("FINAL_METAGRAPH_BOLT_URI", "bolt://localhost:8094")
    final_metagraph_user = os.getenv("FINAL_METAGRAPH_USERNAME", "neo4j")
    final_metagraph_password = os.getenv("FINAL_METAGRAPH_PASSWORD", "password")
    
    output_file_path = "config/s6_accessions/accessions.json"
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    
    print("Extracting schema for accessions...")
    port = int(os.getenv("FINAL_GRAPH_BOLT_PORT", 8093))
    
    schema_dict_md = extract_schema_with_samples_md(port, final_graph_user, final_graph_password, only_concept_nodes=True)
    json_schema = extract_json(port, final_graph_user, final_graph_password)
    
    print("Identifying accession keys via LLM...")
    extract_accession_keys(schema_dict_md, json_schema, output_file_path)
    
    print("Applying accessions to graph...")
    apply_accessions_to_graph(final_graph_uri, final_graph_user, final_graph_password, output_file_path)

    print(f"Connecting to Final Metagraph at {final_metagraph_uri}...")
    target_driver = GraphDatabase.driver(final_graph_uri, auth=(final_graph_user, final_graph_password))
    metagraph_driver = GraphDatabase.driver(final_metagraph_uri, auth=None)

    print("Generating metagraph...")
    migrate_metagraph(target_driver, metagraph_driver)

    print("Stage 6 complete. Pipeline finished!")

if __name__ == "__main__":
    main()
