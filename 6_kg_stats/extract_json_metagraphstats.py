from neo4j import GraphDatabase
from kg_stats.utils.metagraph_stats_extraction import *
from kg_stats.utils.Neo4jAuth import Neo4jAuth
import json
import os



raw_kg_auth = Neo4jAuth("bolt://localhost:8083")
refined_kg_auth = Neo4jAuth("bolt://localhost:7691")
os.makedirs("kg_stats/out", exist_ok=True)

for neo4j_auth in [raw_kg_auth, refined_kg_auth]:
    uri, user, password = neo4j_auth.uri, neo4j_auth.user, neo4j_auth.password
    port = uri.split(":")[-1]
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            node_types = session.execute_read(get_node_types_and_properties)
            edge_types = session.execute_read(get_edge_types_and_properties)

        metagraph = {"nodeTypes": node_types, "edgeTypes": edge_types}
        out = f"kg_stats/out/graph_schema_ckg_complete_{port}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(metagraph, f, indent=2, ensure_ascii=False)
        print(f"Saved to {out}")
    finally:
        driver.close()