from utils.clone_kg import clone_kg
import os
if __name__ == "__main__":
    source_dir = "~/mnt/client_data/mikrobiome_kg/workspace/neo4j/neo4j.db/data/"
    source_dir = os.path.expanduser(source_dir)
    target_dir = "~/mnt/client_data/mikrobiome_kg/s4_filtered_rolledup_graph/"
    clone_kg(source_dir, target_dir)