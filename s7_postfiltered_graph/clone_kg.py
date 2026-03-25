from utils.clone_kg import clone_kg

if __name__ == "__main__":
    source_dir = "s4_filtered_rolledup_graph/data/"
    target_dir = "s7_postfiltered_graph/"
    clone_kg(source_dir, target_dir)