import json
import os
import re
from typing import TypedDict, Annotated, Dict, Any, List
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from utils.extract_properties_markdown import extract_schema_with_samples_md
from utils.extract_properties_json import extract_json

class ExtractionState(TypedDict):
    messages: Annotated[list, add_messages]
    prop_metadata: Dict[str, Dict[str, Any]]
    extracted_data: dict
    valid: bool
    attempts: int
    max_retries: int

def build_metadata_from_inputs(md_string: str, valid_keys_from_schema: List[str]) -> Dict[str, Dict[str, Any]]:
    prop_metadata = {}
    lines = md_string.strip().split('\n')
    
    for line in lines:
        if line.startswith('|') and 'Property Key' not in line and '---' not in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                raw_key = parts[1]
                key = re.sub(r'[^a-zA-Z0-9_]', '', raw_key)
                
                if key not in valid_keys_from_schema:
                    continue
                    
                prop_type = parts[2]
                samples_str = parts[3]
                
                is_array = 'Array' in prop_type
                max_len = 0
                if is_array:
                    list_matches = re.findall(r'\[(.*?)\]', samples_str)
                    for match in list_matches:
                        elements = [e.strip() for e in match.split(',') if e.strip() and e.strip() != '...']
                        if len(elements) > max_len:
                            max_len = len(elements)
                
                if key:
                    prop_metadata[key] = {
                        "type": prop_type,
                        "is_array": is_array,
                        "sample_max_len": max_len
                    }
    
    for key in valid_keys_from_schema:
        if key not in prop_metadata:
            prop_metadata[key] = {
                "type": "unknown",
                "is_array": False,
                "sample_max_len": 0
            }
            
    return prop_metadata

def create_extraction_graph(model_name, api_key, base_url):
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    def generate(state: ExtractionState):
        response = llm.invoke(state["messages"])
        return {"messages": [response], "attempts": state["attempts"] + 1}

    def validate(state: ExtractionState):
        last_message = state["messages"][-1].content
        prop_metadata = state["prop_metadata"]
        valid_keys = list(prop_metadata.keys())
        
        try:
            parsed_json = json.loads(last_message)
            primary = parsed_json.get("primary_accession", {})
            secondary = parsed_json.get("secondary_accessions", {})
            
            if not isinstance(primary, dict) or not isinstance(secondary, dict):
                return {"valid": False, "messages": [HumanMessage(content="Ensure 'primary_accession' and 'secondary_accessions' are objects.")]}
            
            if "reasoning" not in primary or "reasoning" not in secondary:
                return {"valid": False, "messages": [HumanMessage(content="Both primary and secondary accessions must include a 'reasoning' string.")]}
            
            p_prop = primary.get("property")
            p_index = primary.get("index")
            s_props = secondary.get("properties", [])
            
            if not isinstance(s_props, list):
                return {"valid": False, "messages": [HumanMessage(content="'properties' inside 'secondary_accessions' must be a list.")]}
            
            if p_prop not in valid_keys:
                return {"valid": False, "messages": [HumanMessage(content=f"Primary property '{p_prop}' is invalid. Choose from: {valid_keys}")]}
            
            p_meta = prop_metadata[p_prop]
            if p_meta["is_array"]:
                if not isinstance(p_index, int) or p_index < 0:
                    return {"valid": False, "messages": [HumanMessage(content=f"Primary property '{p_prop}' is an array. Provide a valid integer index >= 0.")]}
                if p_meta["sample_max_len"] > 0 and p_index >= p_meta["sample_max_len"]:
                    return {"valid": False, "messages": [HumanMessage(content=f"Index {p_index} exceeds sample length {p_meta['sample_max_len']} for '{p_prop}'.")]}
            else:
                if p_index is not None:
                    return {"valid": False, "messages": [HumanMessage(content=f"Primary property '{p_prop}' is not an array. Index must be null.")]}
            
            for s_prop in s_props:
                if s_prop not in valid_keys:
                    return {"valid": False, "messages": [HumanMessage(content=f"Secondary property '{s_prop}' is invalid. Choose from: {valid_keys}")]}
            
            return {"valid": True, "extracted_data": parsed_json}
            
        except json.JSONDecodeError:
            return {"valid": False, "messages": [HumanMessage(content="Return valid JSON.")]}

    def route(state: ExtractionState):
        if state["valid"] or state["attempts"] >= state["max_retries"]:
            return END
        return "generate"

    workflow = StateGraph(ExtractionState)
    workflow.add_node("generate", generate)
    workflow.add_node("validate", validate)
    
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges("validate", route)
    
    return workflow.compile()

def extract_accessions_for_label(label, markdown_content, json_schema_list, api_key, base_url, model_name, max_retries=3):
    graph = create_extraction_graph(model_name, api_key, base_url)
    prop_metadata = build_metadata_from_inputs(markdown_content, json_schema_list)
    
    system_prompt = """
    You are an API that identifies the best primary and secondary accession properties for a database node based on its markdown schema.
    
    1. primary_accession: A single property that identifies the node (e.g.,  a gene name or specific identifier). If the chosen property is an Array type, provide the integer index of the element to use. If it is not an Array, index must be null. Include your reasoning. Choose string types over integers where possible.
    2. secondary_accessions: A list of property keys that, when concatenated, provide a secondary unique identifier. Include your reasoning for this combination.
    
    Return a JSON object strictly matching this format:
    {
        "primary_accession": {
            "property": "exact_property_key",
            "index": 0,
            "reasoning": "string"
        },
        "secondary_accessions": {
            "properties": ["prop1", "prop2"],
            "reasoning": "string"
        }
    }
    """
    
    user_prompt = f"Label: {label}\nSchema:\n{markdown_content}"
    
    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        "prop_metadata": prop_metadata,
        "extracted_data": {},
        "valid": False,
        "attempts": 0,
        "max_retries": max_retries
    }
    
    final_state = graph.invoke(initial_state)
    
    if final_state["valid"]:
        return final_state["extracted_data"]
    else:
        print(f"Failed to extract for {label}. Last message: {final_state['messages'][-1].content}")
        return None

def extract_accession_keys(schema_dict_md, json_schema, output_file):
    load_dotenv(find_dotenv())
    custom_api_key = os.getenv("API_KEY")
    custom_base_url = os.getenv("BASE_URL")
    custom_model = "medgemma-27b-it" #"qwen3-235b-a22b"
    
    results = {}
    
    for label, md_content in schema_dict_md.items():
        print(f"Processing {label}...")
        json_schema_list = json_schema.get(label, [])
        
        extracted = extract_accessions_for_label(
            label=label,
            markdown_content=md_content,
            json_schema_list=json_schema_list,
            api_key=custom_api_key,
            base_url=custom_base_url,
            model_name=custom_model
        )
        if extracted:
            results[label] = extracted

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    port = 7693
    user = "neo4j"
    password = "test"       
    
    schema_dict_md = extract_schema_with_samples_md(port, user, password, only_concept_nodes=True)
    json_schema = extract_json(port, user, password) 
    output_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s8_postfiltered_graph_with_accessions/accession_keys.json")
    extract_accession_keys(schema_dict_md, json_schema, output_file_path)