import os
from dotenv import load_dotenv
from src.utils.clone_kg import clone_kg

load_dotenv()
mapped_graph_dir = os.getenv("MAPPED_GRAPH_DIR")
propagated_graph_dir = os.getenv("PROPAGATED_GRAPH_DIR")
print(f"Cloning {mapped_graph_dir} to {propagated_graph_dir}...")
clone_kg(mapped_graph_dir, propagated_graph_dir)
print("Done!")
