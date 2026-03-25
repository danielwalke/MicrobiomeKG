import json
import os
from neo4j import GraphDatabase

def apply_accessions_to_graph(uri, user, password, json_filepath):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with open(json_filepath, 'r', encoding='utf-8') as f:
        accession_data = json.load(f)

    with driver.session() as session:
        for label, data in accession_data.items():
            primary = data.get("primary_accession", {})
            secondary = data.get("secondary_accessions", {})
            
            p_prop = primary.get("property")
            p_index = primary.get("index")
            
            if p_index is not None:
                p_expr = f"n.`{p_prop}`[{p_index}]"
            else:
                p_expr = f"n.`{p_prop}`"
                
            s_props = secondary.get("properties", [])
            if s_props:
                props_list = ", ".join([f"n.`{sp}`" for sp in s_props])
                s_expr = f"[x IN apoc.coll.flatten([p IN [{props_list}] WHERE p IS NOT NULL]) | toString(x)]"
            else:
                s_expr = "[]"
                
            query = f"MATCH (n:`{label}`) SET n.primary_accession = {p_expr}, n.secondary_accession = {s_expr}"
            
            session.run(query)
            print(f"Successfully processed label: {label}")

    driver.close()

if __name__ == "__main__":
    target_uri = "bolt://localhost:7693"
    target_user = "neo4j"
    target_password = "password"
    accession_keys_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s8_postfiltered_graph_with_accessions/accession_keys.json")

    apply_accessions_to_graph(target_uri, target_user, target_password, accession_keys_file_path)