import argparse
import sys
import json
from neo4j import GraphDatabase

def extract_metagraph(source_uri, source_user, source_password, target_uri, target_user, target_password):
    # Connect to source
    try:
        source_driver = GraphDatabase.driver(source_uri, auth=(source_user, source_password))
        source_driver.verify_connectivity()
    except Exception as e:
        print(f"Error connecting to source: {e}")
        sys.exit(1)

    # Connect to target
    try:
        target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_password))
        target_driver.verify_connectivity()
    except Exception as e:
        print(f"Error connecting to target: {e}")
        source_driver.close()
        sys.exit(1)

    print(f"Connected to source: {source_uri}")
    print(f"Connected to target: {target_uri}")

    with source_driver.session() as session:
        # Get Node Labels and counts
        print("Extracting node labels and counts...")
        node_query = """
        CALL db.labels() YIELD label
        CALL {
            WITH label
            MATCH (n) WHERE label IN labels(n)
            RETURN count(n) AS node_count
        }
        RETURN label, node_count
        """
        nodes_raw = session.run(node_query).data()
        
        # Get Node properties and types
        print("Extracting node property metadata...")
        node_prop_query = "CALL db.schema.nodeTypeProperties()"
        node_props_raw = session.run(node_prop_query).data()

        # Get Relationship types and counts
        print("Extracting relationship types and counts...")
        rel_query = """
        MATCH (a)-[r]->(b)
        WITH labels(a)[0] AS start_label, type(r) AS rel_type, labels(b)[0] AS end_label
        RETURN start_label, rel_type, end_label, count(*) AS rel_count
        """
        relationships_raw = session.run(rel_query).data()

        # Get Relationship properties and types
        print("Extracting relationship property metadata...")
        rel_prop_query = "CALL db.schema.relTypeProperties()"
        rel_props_raw = session.run(rel_prop_query).data()

    # Inference and processing solely in Python
    print("Processing metadata in Python...")
    
    # Process Node Metadata
    node_metadata = {}
    for node in nodes_raw:
        label = node['label']
        node_metadata[label] = {
            'count': node['node_count'],
            'properties': {}
        }
    
    for prop in node_props_raw:
        labels = prop.get('nodeLabels', [])
        prop_name = prop.get('propertyName')
        prop_types = prop.get('propertyTypes', [])
        type_str = ", ".join(prop_types) if prop_types else "Unknown"
        
        for label in labels:
            if label in node_metadata:
                node_metadata[label]['properties'][prop_name] = type_str

    # Process Relationship Metadata
    rel_type_props = {}
    for prop in rel_props_raw:
        rtype_raw = prop.get('relType', "")
        # Normalize relType from ":`TYPE`" or ":TYPE" to "TYPE"
        rtype = rtype_raw.strip(":").strip("`")
        
        prop_name = prop.get('propertyName')
        prop_types = prop.get('propertyTypes', [])
        type_str = ", ".join(prop_types) if prop_types else "Unknown"
        
        if rtype not in rel_type_props:
            rel_type_props[rtype] = {}
        rel_type_props[rtype][prop_name] = type_str

    rel_metadata = []
    for rel in relationships_raw:
        rtype = rel['rel_type']
        rel_pattern = {
            'start_label': rel['start_label'],
            'rel_type': rtype,
            'end_label': rel['end_label'],
            'count': rel['rel_count'],
            'properties': rel_type_props.get(rtype, {})
        }
        rel_metadata.append(rel_pattern)

    print(f"Extracted {len(node_metadata)} labels and {len(rel_metadata)} relationship patterns with property info.")

    with target_driver.session() as session:
        # Clear target metagraph
        print("Clearing target metagraph...")
        session.run("MATCH (n:MetaNode) DETACH DELETE n")

        # Create nodes
        print("Creating MetaNodes in target...")
        for label, data in node_metadata.items():
            props_params = {f"p_{k}": v for k, v in data['properties'].items()}
            props_params['name'] = label
            props_params['count'] = data['count']
            props_params['properties_json'] = json.dumps(data['properties'])
            
            set_clause = ", ".join([f"n.`{k}` = ${k}" for k in props_params.keys() if k != 'name'])
            
            session.run(f"""
            MERGE (n:MetaNode {{name: $name}})
            SET {set_clause}
            """, **props_params)

        # Create relationships
        print("Creating MetaRelationships in target...")
        for rel in rel_metadata:
            props_params = {f"p_{k}": v for k, v in rel['properties'].items()}
            props_params['start_label'] = rel['start_label']
            props_params['end_label'] = rel['end_label']
            props_params['rel_type'] = rel['rel_type']
            props_params['count'] = rel['count']
            props_params['properties_json'] = json.dumps(rel['properties'])
            
            set_clause = ", ".join([f"r.`{k}` = ${k}" for k in props_params.keys() if k not in ['start_label', 'end_label', 'rel_type']])
            
            session.run(f"""
            MATCH (a:MetaNode {{name: $start_label}})
            MATCH (b:MetaNode {{name: $end_label}})
            MERGE (a)-[r:META_REL {{type: $rel_type}}]->(b)
            {"SET " + set_clause if set_clause else ""}
            """, **props_params)

    source_driver.close()
    target_driver.close()
    print("Metagraph extraction and storage complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract metagraph with properties from one Neo4j and store in another.')
    parser.add_argument('--suri', default='bolt://localhost:8083', help='Source Neo4j URI')
    parser.add_argument('--suser', default='neo4j', help='Source Neo4j User')
    parser.add_argument('--spass', default='neo4j', help='Source Neo4j Password')
    parser.add_argument('--turi', default='bolt://localhost:7688', help='Target Neo4j URI')
    parser.add_argument('--tuser', default='neo4j', help='Target Neo4j User')
    parser.add_argument('--tpass', default='', help='Target Neo4j Password')

    args = parser.parse_args()
    
    extract_metagraph(args.suri, args.suser, args.spass, args.turi, args.tuser, args.tpass)
