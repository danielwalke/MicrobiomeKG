import json
import os
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from utils.extract_properties_markdown import extract_schema_with_samples_md
from utils.extract_properties_json import extract_json
from tqdm import tqdm
import time
class ExtractionState(TypedDict):
    messages: Annotated[list, add_messages]
    all_props: List[str]
    extracted_props: dict
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
            extracted_props = parsed_json.get("properties", {})
            
            if type(extracted_props) is not dict:
                return {"valid": False, "messages": [HumanMessage(content="The 'properties' key must be a JSON object mapping keys to reasoning strings.")]}
            
            extracted_keys = list(extracted_props.keys())
            
            invalid_keys = [key for key in extracted_keys if key not in all_props]
            
            if not invalid_keys:
                return {"valid": True, "extracted_props": extracted_props}
            
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
    
    You must return a JSON object with a single key "properties" containing a dictionary. The keys of this dictionary must perfectly match a value from the "Property Key" column in the provided table. The values must be a short string explaining your reasoning for extracting that property.
    
    Example:
    {
        "properties": {
            "name": "Essential identifier for web search.",
            "sequence": "Highly relevant for sequencing analysis."
        }
    }
    """
    user_prompt = f"Topics: {topics}\n\nMarkdown Data:\n{markdown_content}"
    print(markdown_content)
    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        "all_props": all_props,
        "extracted_props": {},
        "valid": False,
        "attempts": 0,
        "max_retries": max_retries
    }
    
    final_state = graph.invoke(initial_state)
    
    if final_state["valid"]:
        return final_state["extracted_props"]
    else:
        raise ValueError("Failed to extract valid keys within retry limit.")

def extract_relevant_properties_as_json(schema_dict, json_schema, output_file="interesting_properties.json", output_removed_file="removed_properties.json"):

    load_dotenv(find_dotenv())
    topics = "I want a knowledge graph for proteome, metaproteome and microbiome research with associated literature research and sequencing anylysis and associated treatments"
    
    custom_api_key = os.getenv("API_KEY")
    custom_base_url = os.getenv("BASE_URL")
    custom_model = "qwen3-235b-a22b"

    relevant_props_dict = dict()
    removed_props_dict = dict()
    
    for label in tqdm(schema_dict, desc="Iterating over labels"):
        print(label)
        markdown_table = schema_dict.get(label)
        all_label_props = json_schema.get(label, [])
        
        try:
            valid_keys_with_reasoning = extract_validated_keys(
                markdown_table, 
                topics, 
                all_label_props,
                custom_api_key, 
                custom_base_url, 
                custom_model
            )
            if not valid_keys_with_reasoning:
                continue
            relevant_props_dict[label] = valid_keys_with_reasoning
            time.sleep(15)  # Sleep to avoid hitting rate limits
            removed_keys = [k for k in all_label_props if k not in valid_keys_with_reasoning]
            removed_props_dict[label] = removed_keys
            
        except Exception as e:
            print(e)
            
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(relevant_props_dict, f, indent=4)
        
    with open(output_removed_file, 'w', encoding='utf-8') as f:
        json.dump(removed_props_dict, f, indent=4)

if __name__ == "__main__":
    port = 8083
    user = "neo4j"
    password = "test"       
    schema_dict_md = extract_schema_with_samples_md(port, user, password, only_concept_nodes = False)
    json_schema = extract_json(port, user, password) ## TODO: Might cache if speed will increase in relevance 
    print(json_schema)
    extract_relevant_properties_as_json(schema_dict_md, json_schema)