import os
from dotenv import load_dotenv
from src.s4_node_filtering.llm_filter import get_llm_filtered_properties

load_dotenv()
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_QWEN", "vllm/Qwen/Qwen3.6-35B-A3B")

dummy_schema = {
    "PUBLICATION": ["id", "title", "authors", "date", "internal_db_hash", "irrelevant_flag"],
    "PROTEIN": ["sequence", "mass", "random_string_xyz"]
}

print(f"Testing LLM Filter Logic with model: {model_name}\n")
filtered = get_llm_filtered_properties(dummy_schema, model_name, base_url, api_key)
print("\nFinal Output:")
for k, v in filtered.items():
    print(f"{k}: {v}")
