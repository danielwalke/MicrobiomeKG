import os
import json
import time
from typing import Dict, Any, List
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv
from tqdm import tqdm

load_dotenv(find_dotenv())

class GraphState(TypedDict):
    tsv_content: str
    generated_json: Dict[str, Any]
    retry_count: int
    errors: List[str]
    status: str

def read_tsv_node(state: GraphState) -> GraphState:
    print("-> Executing: Read TSV Node")
    with open("config/s1_raw_graph/schema_overlaps.tsv", "r") as f:
        content = f.read()
    return {"tsv_content": content, "retry_count": state.get("retry_count", 0), "errors": [], "status": "read"}

def llm_generation_node(state: GraphState) -> GraphState:
    attempt = state.get("retry_count", 0) + 1
    print(f"-> Executing: LLM Generation Node (Attempt {attempt}/3)")
    
    llm = ChatOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        model="qwen3.5-35b-a3b"
    )
    
    system_prompt = """Extract the tab-separated data and identify node labels and properties that require preprocessing for exact ID matching.
    Output ONLY a valid JSON object with the following structure:
    {
      "NodeLabel": {
        "propertyName": {
          "cypher": "MATCH (n:`NodeLabel`) WHERE n.propertyName IS NOT NULL SET n.propertyName = ...",
          "reasoning": "String explaining the transformation logic"
        }
      }
    }"""
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["tsv_content"])
        ])
        
        raw_content = response.content.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(raw_content)
        
        print("Successfully generated JSON from LLM.")
        return {"generated_json": parsed_json, "status": "generated"}
        
    except Exception as e:
        print(f"LLM Error encountered: {e}. Waiting 30s before retry...")
        time.sleep(30)
        return {"errors": [str(e)], "retry_count": state["retry_count"] + 1, "status": "llm_error"}

def validate_neo4j_node(state: GraphState) -> GraphState:
    print("-> Executing: Neo4j Validation Node")
    driver = GraphDatabase.driver("bolt://localhost:8083", auth=None)
    data = state["generated_json"]
    errors = []
    
    try:
        with driver.session() as session:
            for label, properties in tqdm(data.items(), desc="Validating Node Labels"):
                label_check = session.run(
                    "CALL db.labels() YIELD label WHERE label = $lbl RETURN count(label) AS c", 
                    lbl=label
                ).single()["c"]
                
                if label_check == 0:
                    errors.append(f"Label {label} not found in database.")
                    continue
                    
                for prop, details in properties.items():
                    prop_check = session.run(
                        "MATCH (n:`" + label + "`) WHERE n." + prop + " IS NOT NULL RETURN count(n) AS c"
                    ).single()["c"]
                    
                    if prop_check == 0:
                        errors.append(f"Property {prop} not found for label {label}.")
                        continue
                        
                    cypher_query = details["cypher"]
                    try:
                        session.run("EXPLAIN " + cypher_query)
                    except Exception as ce:
                        errors.append(f"Invalid Cypher logic for {label}.{prop}: {str(ce)}")
                        
    finally:
        driver.close()
        
    if errors:
        print(f"Validation finished with {len(errors)} errors.")
        return {"errors": errors, "status": "validation_failed"}
        
    print("Validation finished successfully. No errors found.")
    return {"status": "validated"}

def router(state: GraphState) -> str:
    print(f"-> Routing from status: {state['status']}")
    if state["status"] == "read":
        return "generate"
    if state["status"] == "llm_error":
        if state["retry_count"] < 3:
            return "generate"
        return "end"
    if state["status"] == "generated":
        return "validate"
    return "end"

workflow = StateGraph(GraphState)

workflow.add_node("read", read_tsv_node)
workflow.add_node("generate", llm_generation_node)
workflow.add_node("validate", validate_neo4j_node)

workflow.set_entry_point("read")

workflow.add_conditional_edges("read", router, {"generate": "generate"})
workflow.add_conditional_edges(
    "generate", 
    router, 
    {"generate": "generate", "validate": "validate", "end": END}
)
workflow.add_conditional_edges("validate", router, {"end": END})

app = workflow.compile()

if __name__ == "__main__":
    print("=== Starting LangGraph Execution ===")
    initial_state = {"retry_count": 0}
    result = app.invoke(initial_state)
    
    if "generated_json" in result:
        with open("generated_queries.json", "w") as f:
            json.dump(result["generated_json"], f, indent=2)
        print("Saved outputs to generated_queries.json")
            
    print("=== Execution Complete ===")
    if result.get("errors"):
        print("Encountered Errors:")
        for e in result.get("errors", []):
            print(f" - {e}")