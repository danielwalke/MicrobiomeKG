from utils.clone_kg import clone_kg
if __name__ == "__main__":
    source_dir = "s1_raw_graph/workspace/neo4j/neo4j.db/data/"
    target_dir = "s4_filtered_rolledup_graph/"
    clone_kg(source_dir, target_dir)