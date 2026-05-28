import os
import json
from typing import TypedDict, Annotated, Dict, Any, List
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

def get_node_schema(session):
    query = """CALL db.schema.nodeTypeProperties()
               YIELD nodeLabels, propertyName
               UNWIND nodeLabels AS label
               RETURN label, collect(DISTINCT propertyName) AS properties
            """
    result = session.run(query)
    schema = {}
    for record in result:
        if record["label"]:
            schema[record["label"]] = record["properties"]
    return schema

class FilterState(TypedDict):
    messages: Annotated[list, add_messages]
    schema: list
    extracted_data: list
    valid: bool
    attempts: int
    max_retries: int

def create_filter_graph(model_name, api_key, base_url):
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    def generate(state: FilterState):
        response = llm.invoke(state["messages"])
        return {"messages": [response], "attempts": state["attempts"] + 1}

    def validate(state: FilterState):
        last_message = state["messages"][-1].content
        valid_props = state["schema"]
        
        try:
            parsed_json = json.loads(last_message)
            kept_properties = parsed_json.get("kept_properties", [])
            
            if not isinstance(kept_properties, list):
                return {"valid": False, "messages": [HumanMessage(content="'kept_properties' must be a list.")]}
            
            invalid_props = [p for p in kept_properties if p not in valid_props]
            if invalid_props:
                return {"valid": False, "messages": [HumanMessage(content=f"These properties are invalid and do not exist in the schema: {invalid_props}")]}
                
            return {"valid": True, "extracted_data": kept_properties}
            
        except json.JSONDecodeError:
            return {"valid": False, "messages": [HumanMessage(content="Return valid JSON.")]}

    def route(state: FilterState):
        if state["valid"] or state["attempts"] >= state["max_retries"]:
            return END
        return "generate"

    workflow = StateGraph(FilterState)
    workflow.add_node("generate", generate)
    workflow.add_node("validate", validate)
    
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges("validate", route)
    
    return workflow.compile()

def get_llm_filtered_properties(schema, model_name, base_url, api_key):
    graph = create_filter_graph(model_name, api_key, base_url)
    filtered_schema = {}
    
    for label, properties in schema.items():
        if not properties:
            filtered_schema[label] = []
            continue
            
        print(f"Asking multi-agent system to filter properties for {label}...")
        system_prompt = """
        You are an expert bioinformatician building a microbiome Knowledge Graph for metaproteomics and metagenomics.
        Filter out ALL properties that are irrelevant or redundant for metaproteomics and metagenomics use cases.
        CRITICAL: ALWAYS keep properties that provide stoichiometric information, order information (such as 'order' in modules), structural representations, or mathematical formulas.
        
        Return a JSON object matching this format:
        {
            "kept_properties": ["prop1", "prop2"]
        }
        """
        user_prompt = f"Label: {label}\nAvailable Properties: {properties}"
        
        initial_state = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            "schema": properties,
            "extracted_data": [],
            "valid": False,
            "attempts": 0,
            "max_retries": 3
        }
        
        try:
            final_state = graph.invoke(initial_state)
            if final_state["valid"]:
                filtered_schema[label] = final_state["extracted_data"]
            else:
                print(f"Failed to extract for {label}. Keeping all properties.")
                filtered_schema[label] = properties
        except Exception as e:
            print(f"Error filtering properties for {label}: {e}")
            filtered_schema[label] = properties # keep all on error
            
    return filtered_schema

def apply_property_filter(session, original_schema, kept_schema):
    for label, all_props in original_schema.items():
        kept_props = kept_schema.get(label, [])
        irrelevant_props = [p for p in all_props if p not in kept_props and p]
        
        if not irrelevant_props:
            continue
            
        print(f"Removing {len(irrelevant_props)} irrelevant properties from {label}: {irrelevant_props}")
        props_to_remove = ", ".join([f"n.`{prop}`" for prop in irrelevant_props])
        
        batch_query = f"""
        CALL apoc.periodic.iterate(
            "MATCH (n:`{label}`) RETURN n",
            "REMOVE {props_to_remove}",
            {{batchSize: 10000, parallel: false}}
        )
        """
        session.run(batch_query)

def save_config(filtered_schema, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "filtered_properties.json"), "w") as f:
        json.dump(filtered_schema, f, indent=4)
