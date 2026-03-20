import json
import os
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from step_4_filtered_metaconcept_graph.get_properties_markdown import *


from tqdm import tqdm

class ExtractionState(TypedDict):
    messages: Annotated[list, add_messages]
    all_props: List[str]
    extracted_keys: List[str]
    valid: bool
    attempts: int
    max_retries: int

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
        all_props = state["all_props"]
        
        try:
            parsed_json = json.loads(last_message)
            extracted_keys = parsed_json.get("properties", [])
            
            invalid_keys = [key for key in extracted_keys if key not in all_props]
            
            if not invalid_keys:
                return {"valid": True, "extracted_keys": extracted_keys}
            
            error_msg = f"Invalid keys found: {invalid_keys}. Only return keys from this list: {all_props}"
            return {"valid": False, "messages": [HumanMessage(content=error_msg)]}
            
        except json.JSONDecodeError:
            return {"valid": False, "messages": [HumanMessage(content="Return valid JSON with the 'properties' key.")]}

    def route(state: ExtractionState):
        if state["valid"]:
            return END
        if state["attempts"] >= state["max_retries"]:
            return END
        return "generate"

    workflow = StateGraph(ExtractionState)
    workflow.add_node("generate", generate)
    workflow.add_node("validate", validate)
    
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges("validate", route, {END: END, "generate": "generate"})
    
    return workflow.compile()

def extract_validated_keys(markdown_content, topics, all_props, api_key, base_url, model_name, max_retries=3):
    graph = create_extraction_graph(model_name, api_key, base_url)
    
    system_prompt = """
    You are an API that extracts relevant property keys for a given node label based on the provided markdown text. 
    Extract properties that have a clear or moderate relevance to the topics discussed in the text and remove any properties that might yield redundant information. 
    If you extract any properties, your final list must include at least one property key that represents a name or identifier to ensure the entity can be searched via the web.
    You must return a JSON object with a single key "properties" containing a list of strings. Every string in this list must perfectly match a value from the "Property Key" column in the provided table.
    """
    user_prompt = f"Topics: {topics}\n\nMarkdown Data:\n{markdown_content}"
    print(markdown_content)
    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        "all_props": all_props,
        "extracted_keys": [],
        "valid": False,
        "attempts": 0,
        "max_retries": max_retries
    }
    
    final_state = graph.invoke(initial_state)
    
    if final_state["valid"]:
        return final_state["extracted_keys"]
    else:
        raise ValueError("Failed to extract valid keys within retry limit.")

def extract_relevant_properties_as_json(schema_dict, all_props, output_file="interesting_properties.json"):

    load_dotenv(find_dotenv())
    topics = "I want a knowledge graph for proteome, metaproteome and microbiome research with associated literature research and sequencing anylysis and associated treatments"
    

    custom_api_key = os.getenv("API_KEY")
    custom_base_url = os.getenv("BASE_URL")
    custom_model = "qwen3-235b-a22b"

    relevant_props_dict = dict()
    
    for label in tqdm(schema_dict, desc="Iterating over labels"):
        print(label)
        markdown_table = schema_dict.get(label) #GeneOntology_Header
        
        try:
            valid_keys = extract_validated_keys(
                markdown_table, 
                topics, 
                all_props, 
                custom_api_key, 
                custom_base_url, 
                custom_model
            )
            if not valid_keys:
                continue
            relevant_props_dict[label] = valid_keys
        except Exception as e:
            print(e)
    ## TODO run this and now it should also eclude node props -> but probably need to remove it in the actual filtering
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(relevant_props_dict, f, indent=4)

if __name__ == "__main__":
    port = 8083
    user = "neo4j"
    password = "test"       
    schema_dict, all_props = extract_schema_with_samples(port, user, password, only_concept_nodes = False)
    extract_relevant_properties_as_json(schema_dict, all_props, output_file="interesting_properties.json")