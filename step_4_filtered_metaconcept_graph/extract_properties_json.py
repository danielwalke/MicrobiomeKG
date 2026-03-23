import argparse
from neo4j import GraphDatabase

def extract_json(port = 8083, user = "neo4j", password = "neo4j"):
    user = user
    password = password
    port = port

    driver = GraphDatabase.driver(f"bolt://localhost:{port}", auth=(user, password))
    
    unique_properties = set()

    with driver.session() as session:
        schema_info = session.run("CALL db.schema.nodeTypeProperties()").data()
        
        label_map = {}
        for row in schema_info:
            prop_name = row['propertyName']
            unique_properties.add(prop_name)
            for label in row['nodeLabels']:
                label_map.setdefault(label, []).append(prop_name)
    return label_map
        