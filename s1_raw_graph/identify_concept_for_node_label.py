import os
import json
import logging
from typing import TypedDict, List
from dotenv import load_dotenv, find_dotenv
from neo4j import GraphDatabase
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from utils.extract_properties_markdown import extract_schema_with_samples_md
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

class MappingState(TypedDict):
    database_label: str
    markdown_schema: str
    concept_labels: List[str]
    mapped_concept: str
    reasoning: str
    error: str
    retries: int

class ConceptMapping(BaseModel):
    reasoning: str = Field(description="Reasoning for the assigned concept label based on the schema and samples")
    mapped_concept: str = Field(description="The exact concept label assigned, or 'UNCLASSIFIED' if no match is found or you are not sure")

def generate_mapping(state: MappingState) -> MappingState:
    load_dotenv(find_dotenv())
    
    llm = ChatOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        model="qwen3.5-397b-a17b",
        temperature=0.0
    )
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            "You are a strict ontology mapping assistant. Your task is to evaluate the provided database label, schema, and samples.\n\n"
            "Allowed Concept Labels: {concept_labels}\n\n"
            "CRITICAL INSTRUCTION: You must ONLY map to an allowed concept label if there is a direct, undeniable semantic match. "
            "Do not force a fit. If the entity represents a concept not explicitly listed (e.g., mapping an experiment to PUBLICATION, "
            "or a sub-protein feature to PROTEIN is INVALID), you MUST return 'UNCLASSIFIED' as the mapped_concept."
        ),
        (
            "user", 
            "Database Label: {database_label}\n\n"
            "Schema and Samples:\n{markdown_schema}\n\n"
            "Previous Error: {error}\n\n"
            "Provide the mapped concept and reasoning."
        )
    ])
    
    chain = prompt | llm.with_structured_output(ConceptMapping)
    
    try:
        result = chain.invoke({
            "concept_labels": json.dumps(state["concept_labels"]),
            "database_label": state["database_label"],
            "markdown_schema": state["markdown_schema"],
            "error": state["error"]
        })
        return {"mapped_concept": result.mapped_concept, "reasoning": result.reasoning, "error": ""}
    except Exception as e:
        logging.error(f"LLM Error generating mapping for {state['database_label']}: {str(e)}")
        return {"error": str(e), "retries": state["retries"] + 1}

def validate_mapping(state: MappingState) -> MappingState:
    mapped = state.get("mapped_concept")
    valid_concepts = state.get("concept_labels", [])
    
    if not mapped:
        return {"error": "Mapping generation failed.", "retries": state["retries"] + 1}
        
    if mapped == "UNCLASSIFIED":
        return {"error": ""}
        
    if mapped not in valid_concepts:
        return {
            "error": f"Invalid assignment '{mapped}'. Must be strictly one of: {valid_concepts} or 'UNCLASSIFIED'",
            "mapped_concept": "",
            "retries": state["retries"] + 1
        }
        
    return {"error": ""}

def route_validation(state: MappingState) -> str:
    if not state.get("error"):
        return END
    if state["retries"] >= 3:
        return END
    return "generate"

def build_mapping_graph():
    workflow = StateGraph(MappingState)
    
    workflow.add_node("generate", generate_mapping)
    workflow.add_node("validate", validate_mapping)
    
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges("validate", route_validation)
    
    return workflow.compile()

def get_node_database_labels_without_mappings(session):
    query = "MATCH (n) WHERE NOT (n)-[:MAPPED_TO]->() AND NOT all(l IN labels(n) WHERE l =~ '^[A-Z]+$') UNWIND labels(n) AS label RETURN DISTINCT label"
    result = session.run(query)
    return [record["label"] for record in result]

def get_concept_labels():
    with open("config/s1_raw_graph/concept_labels.json", "r") as f:
        return list(set(json.load(f)))

def main():
    logging.info("Initializing Neo4j driver connection.")
    driver = GraphDatabase.driver("bolt://localhost:8083", auth=None)
    
    logging.info("Extracting markdown schema samples...")
    markdown_output_label_map = extract_schema_with_samples_md(port=8083, user="neo4j", password="neo4j", only_concept_nodes=False)
    
    logging.info("Loading valid concept labels.")
    concept_labels = get_concept_labels()
    
    logging.info("Building LangGraph mapping workflow.")
    mapping_graph = build_mapping_graph()

    output_path = "config/s1_raw_graph/database_to_concept_mapping.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    final_results = {}
    
    if os.path.exists(output_path):
        try:
            with open(output_path, "r") as f:
                final_results = json.load(f)
            logging.info(f"Loaded {len(final_results)} cached mappings from {output_path}")
        except json.JSONDecodeError:
            logging.warning(f"Cache file {output_path} is corrupted. Starting fresh.")
    
    try:
        with driver.session() as session:
            logging.info("Querying for unmapped database labels.")
            unmapped_database_labels = get_node_database_labels_without_mappings(session)
            
            labels_to_process = [label for label in unmapped_database_labels if label not in final_results]
            
            total_labels = len(labels_to_process)
            skipped_labels = len(unmapped_database_labels) - total_labels
            logging.info(f"Found {total_labels} labels to map (skipped {skipped_labels} already cached).")
            
            for database_label in tqdm(labels_to_process, desc="Mapping Database Labels", unit="label"):
                markdown_example = markdown_output_label_map.get(database_label, "No schema information available")
                
                initial_state = MappingState(
                    database_label=database_label,
                    markdown_schema=markdown_example,
                    concept_labels=concept_labels,
                    mapped_concept="",
                    reasoning="",
                    error="",
                    retries=0
                )
                
                result = mapping_graph.invoke(initial_state)
                
                if result.get("mapped_concept") and not result.get("error"):
                    final_results[database_label] = {
                        "mapped_concept": result["mapped_concept"],
                        "reasoning": result["reasoning"],
                        "status": "SUCCESS" if result["mapped_concept"] != "UNCLASSIFIED" else "UNCLASSIFIED"
                    }
                else:
                    logging.warning(f"Failed to find valid concept for '{database_label}' after retries. Defaulting to UNCLASSIFIED.")
                    final_results[database_label] = {
                        "mapped_concept": "UNCLASSIFIED",
                        "reasoning": result.get("error") or "Failed after maximum retries without a valid mapping.",
                        "status": "UNCLASSIFIED"
                    }
                
                with open(output_path, "w") as f:
                    json.dump(final_results, f, indent=4)
                    
    finally:
        driver.close()
        logging.info("Neo4j driver connection closed.")
        
    logging.info(f"Mapping workflow complete. All results safely stored in {output_path}")

if __name__ == "__main__":
    main()