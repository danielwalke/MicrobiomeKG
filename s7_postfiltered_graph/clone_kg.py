from utils.clone_kg import clone_kg
import os

if __name__ == "__main__":
    source_dir = "~/mnt/client_data/mikrobiome_kg/s4_filtered_rolledup_graph/data/"
    target_dir = "~/mnt/client_data/mikrobiome_kg/s7_postfiltered_graph/"
    source_dir = os.path.expanduser(source_dir)
    target_dir = os.path.expanduser(target_dir)
    clone_kg(source_dir, target_dir)