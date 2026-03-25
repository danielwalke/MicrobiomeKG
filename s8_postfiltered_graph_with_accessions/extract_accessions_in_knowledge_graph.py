import json
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7691)
    parser.add_argument("--user", type=str, default="neo4j")
    parser.add_argument("--password", type=str, default="test")
    parser.add_argument("--file", type=str, default="step_5_2_accession_aggregations/accession_keys.json")
    
    args = parser.parse_args()
    
    uri = f"bolt://localhost:{args.port}"
    apply_accessions_to_graph(uri, args.user, args.password, args.file)