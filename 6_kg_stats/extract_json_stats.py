from kg_stats.utils.stats_extraction import *
from kg_stats.utils.Neo4jAuth import Neo4jAuth
import os
from neo4j import GraphDatabase

raw_kg_auth = Neo4jAuth("bolt://localhost:8083")
refined_kg_auth = Neo4jAuth("bolt://localhost:7691")

out_path_dir = "kg_stats/out_stats"
os.makedirs(out_path_dir, exist_ok=True)

for neo4j_auth in [raw_kg_auth, refined_kg_auth]:
    
    NEO4J_URI = neo4j_auth.uri
    NEO4J_USER = neo4j_auth.user
    NEO4J_PASS = neo4j_auth.password
    port = NEO4J_URI.split(":")[-1]
    kg_id = port
    kg_name = port

    out_path = out_path_dir + f"/{port}_stats.json"


    # ----------- CONNECT -----------
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    stats_dict = {
        "node_count_per_type": {
            "data": get_node_counts_multilabel(driver),
        },
        "node_count_aggregated": {
        "data": get_node_counts_aggregated(driver),
        },
        "total_degree_distribution": {
            "data": get_total_degree_distribution(driver),
        },
        "out_degree_distribution": {
            "data": get_out_degree_distribution(driver),
        },
        "in_degree_distribution": {
            "data": get_in_degree_distribution(driver),
        },
        "total_degree_by_label": {
        "data": get_total_degree_distribution_by_label(driver),
        },
        "out_degree_by_label": {
            "data": get_out_degree_distribution_by_label(driver),
        },
        "in_degree_by_label": {
            "data": get_in_degree_distribution_by_label(driver),
        },
        "out_degree_by_label_combo": {
            "data": get_out_degree_distribution_by_label_combo(driver),
        },
        "in_degree_by_label_combo": {
            "data": get_in_degree_distribution_by_label_combo(driver),
        },
        "total_degree_by_label_combo": {
            "data": get_total_degree_distribution_by_label_combo(driver),
        },
        "relationship_count_per_type": {
            "data": get_relationship_counts(driver),
        },
        "sankey_links_unaggregated": {
            "data": get_sankey_links_unaggregated(driver)
        },
        "sankey_links_aggregated": {
            "data": get_sankey_links_aggregated(driver)
        },
        "zero_degree_nodes": {
            "data": get_zero_degree_node_stats(driver),
        },
    }

    save_kg_stats_json(
        kg_id=kg_id,
        kg_name=kg_name,
        stats_dict=stats_dict,
        out_path=out_path
    )

    driver.close()