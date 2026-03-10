import argparse
import sys
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
        nodes = session.run(node_query).data()

        # Get Relationship types and counts
        print("Extracting relationship types and counts...")
        # Note: Using labels(a)[0] assuming first label is primary/most descriptive
        rel_query = """
        MATCH (a)-[r]->(b)
        WITH labels(a)[0] AS start_label, type(r) AS rel_type, labels(b)[0] AS end_label
        RETURN start_label, rel_type, end_label, count(*) AS rel_count
        """
        relationships = session.run(rel_query).data()

    print(f"Extracted {len(nodes)} labels and {len(relationships)} relationship patterns.")

    with target_driver.session() as session:
        # Clear target metagraph
        print("Clearing target metagraph...")
        session.run("MATCH (n:MetaNode) DETACH DELETE n")

        # Create nodes
        print("Creating MetaNodes in target...")
        for node in nodes:
            session.run("""
            MERGE (n:MetaNode {name: $name})
            SET n.count = $count
            """, name=node['label'], count=node['node_count'])

        # Create relationships
        print("Creating MetaRelationships in target...")
        for rel in relationships:
            session.run("""
            MATCH (a:MetaNode {name: $start_label})
            MATCH (b:MetaNode {name: $end_label})
            MERGE (a)-[r:META_REL {type: $rel_type}]->(b)
            SET r.count = $count
            """, start_label=rel['start_label'], 
                 end_label=rel['end_label'], 
                 rel_type=rel['rel_type'], 
                 count=rel['rel_count'])

    source_driver.close()
    target_driver.close()
    print("Metagraph extraction and storage complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract metagraph from one Neo4j and store in another.')
    parser.add_argument('--suri', default='bolt://localhost:7687', help='Source Neo4j URI')
    parser.add_argument('--suser', default='neo4j', help='Source Neo4j User')
    parser.add_argument('--spass', default='neo4j', help='Source Neo4j Password')
    parser.add_argument('--turi', default='bolt://localhost:7688', help='Target Neo4j URI')
    parser.add_argument('--tuser', default='neo4j', help='Target Neo4j User')
    parser.add_argument('--tpass', default='neo4j', help='Target Neo4j Password')

    args = parser.parse_args()
    
    # Try with empty auth if defaults fail for source
    extract_metagraph(args.suri, args.suser, args.spass, args.turi, args.tuser, args.tpass)
