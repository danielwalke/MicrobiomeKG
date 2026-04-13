import os
import json
import time
from dotenv import load_dotenv, find_dotenv
from typing import Dict, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.extract_properties_markdown import extract_schema_with_samples_md

class PreprocessingStep(BaseModel):
    new_property_name: str = Field(description="The name of the new property created by the Cypher query to hold the cleaned identifier.")
    reasoning: str = Field(description="Detailed reasoning for why this preprocessing is necessary.")
    description: str = Field(description="A plain text description of what the preprocessing step actually does.")
    cypher_query: str = Field(description="A valid Cypher query that creates the new property on the node.")

class DatabaseMapping(BaseModel):
    raw_property_name: str = Field(description="The exact property key from the markdown table that contains the source data.")
    final_property_name: str = Field(description="The property name to be used for mapping. If preprocessing is used, this MUST match the 'new_property_name'. If no preprocessing, this MUST match 'raw_property_name'.")
    reasoning: str = Field(description="Why this specific property was chosen over the others.")
    preprocessing: Optional[PreprocessingStep] = Field(default=None, description="Include only if the property needs transformation before it can be mapped.")

class ConceptMappingOutput(BaseModel):
    concept_label: str = Field(description="The higher order Concept name.")
    databases: Dict[str, DatabaseMapping] = Field(description="Mapping details keyed by the raw database label.")

def main():
    print("Initializing environment...")
    load_dotenv(find_dotenv())
    custom_api_key = os.getenv("API_KEY")
    custom_base_url = os.getenv("BASE_URL")

    print("Configuring LLM with model: qwen3.5-397b-a17b")
    llm = ChatOpenAI(
        api_key=custom_api_key,
        base_url=custom_base_url,
        model="qwen3.5-397b-a17b",
        temperature=0
    )

    structured_llm = llm.with_structured_output(ConceptMappingOutput)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            "You are an expert graph database architect and bioinformatician mapping multiple raw database schemas into unified higher-order concept nodes.\n"
            "Your task is to identify the best property to use as a universal identifier for each database label to map to the given Concept.\n\n"
            "CRITICAL DOMAIN RULES FOR IDENTIFIER SELECTION:\n"
            "1. AVOID internal database IDs (e.g., `__id`).\n"
            "2. AVOID auto-generated UUIDs or MD5 hashes (e.g., `id`) unless explicitly stated they are deterministic hashes of biological data.\n"
            "3. PREFER stable, universal biological standards. Properties containing RefSeq Accession numbers (like 'NM_...', 'NG_...'), standard gene symbols, or coordinate mappings are universally recognized.\n\n"
            "If a property requires transformation to be a clean identifier, you MUST provide a preprocessing step with a Cypher query to create a NEW property on the node itself.\n"
            "When validating, `raw_property_name` MUST exactly match the Property Key from the provided markdown table. `final_property_name` MUST be the new property name if preprocessing is used, or the raw name if not."
        ),
        (
            "user", 
            "Concept: {concept}\n\nSchemas:\n{schemas}"
        )
    ])

    chain = prompt | structured_llm

    print("Extracting markdown schemas...")
    schema_dict = extract_schema_with_samples_md()
    
    print("Loading database-to-concept mapping...")
    with open("config/s1_raw_graph/database_to_concept_mapping.json", "r") as f:
        db_to_concept = json.load(f)
        
    concept_to_dbs_dict = {}
    for db_label, mapping_info in db_to_concept.items():
        concept = mapping_info["mapped_concept"]
        if concept not in concept_to_dbs_dict:
            concept_to_dbs_dict[concept] = []
        concept_to_dbs_dict[concept].append(db_label)

    output_path = "config/s1_raw_graph/database_mapping_identifiers.json"
    final_registry = {}

    if os.path.exists(output_path):
        print(f"Found existing progress at {output_path}. Loading checkpoint...")
        with open(output_path, "r") as f:
            try:
                final_registry = json.load(f)
                print(f"Loaded {len(final_registry)} already processed concepts.")
            except json.JSONDecodeError:
                print("Warning: Could not decode existing JSON. Starting fresh.")

    os.makedirs("config/s1_raw_graph", exist_ok=True)

    for concept, db_labels in concept_to_dbs_dict.items():
        if concept == "UNCLASSIFIED":
            print(f"\n[SKIP] Concept '{concept}' is marked as UNCLASSIFIED. Skipping...")
            continue
        if concept in final_registry:
            print(f"\n[SKIP] Concept '{concept}' is already evaluated. Moving to next...")
            continue

        print(f"\n[START] Processing Concept: {concept}...")
        
        schemas_text = ""
        for db_label in db_labels:
            if db_label in schema_dict:
                schemas_text += f"### Database Label: {db_label}\n{schema_dict[db_label]}\n\n"
        
        if not schemas_text.strip():
            print(f"[WARNING] Skipping {concept} - no schema data found.")
            continue

        try:
            print(f"  -> Invoking LLM for '{concept}'...")
            result = chain.invoke({"concept": concept, "schemas": schemas_text})
            
            validated_concept_mapping = {}
            for db_label, mapping_data in result.databases.items():
                property_markdown_string = f"`{mapping_data.raw_property_name}`"
                
                mapping_dict = mapping_data.model_dump()
                
                if db_label in schema_dict and property_markdown_string not in schema_dict[db_label]:
                    mapping_dict["VALIDATION_ERROR"] = f"Warning: '{mapping_data.raw_property_name}' was not found in the markdown schema."
                    print(f"  [!] Validation failed for {db_label}: Property '{mapping_data.raw_property_name}' missing.")
                else:
                    print(f"  [✓] Validated {db_label} -> Raw: {mapping_data.raw_property_name} | Final: {mapping_data.final_property_name}")
                    
                validated_concept_mapping[db_label] = mapping_dict
                
            final_registry[concept] = validated_concept_mapping

            with open(output_path, "w") as f:
                json.dump(final_registry, f, indent=4)
            print(f"  [SAVE] Progress saved for '{concept}' to {output_path}")

            print("  [WAIT] Sleeping for 15 seconds to prevent API rate limits...")
            time.sleep(15)

        except Exception as e:
            print(f"  [X] ERROR: Failed to process {concept}: {str(e)}")
            print("  -> Continuing to next concept...")

    print(f"\nPipeline complete. Final results saved to {output_path}")

if __name__ == "__main__":
    main()