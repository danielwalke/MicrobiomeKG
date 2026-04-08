import os
import json
import time
import re
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
    return {"tsv_content": content, "retry_count": state.get("retry_count", 0), "errors": state.get("errors", []), "status": "read"}

def llm_generation_node(state: GraphState) -> GraphState:
    attempt = state.get("retry_count", 0) + 1
    print(f"-> Executing: LLM Generation Node (Attempt {attempt}/3)")
    
    llm = ChatOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        model="qwen3.5-35b-a3b"
    )
    
    system_prompt = """Extract the tab-separated data and identify node labels and properties that require preprocessing for exact ID matching.
    
    CRITICAL HEURISTIC RULE FOR NEO4J DATA TYPES:
    You must look at the property name to determine if it is a String or a StringArray.
    
    1. PLURAL PROPERTIES: If the property ends in 's', it is a StringArray.
       YOU MUST USE LIST COMPREHENSIONS. 
       Correct: MATCH (n:`Label`) WHERE n.xrefs IS NOT NULL SET n.xrefs = [x IN n.xrefs | replace(x, 'EC:', '')]
       
    2. SINGULAR PROPERTIES: If the property does not end in 's', it is a standard String.
       YOU MUST USE STANDARD STRING FUNCTIONS.
       Correct: MATCH (n:`Label`) WHERE n.id IS NOT NULL SET n.id = replace(n.id, 'ChEMBL:', '')
    
    Output ONLY a valid JSON object with the following structure:
    {
      "NodeLabel": {
        "propertyName": {
          "cypher": "MATCH (n:`NodeLabel`) WHERE n.propertyName IS NOT NULL SET n.propertyName = ...",
          "reasoning": "String explaining the transformation logic"
        }
      }
    }"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Here is the schema data:\n{state['tsv_content']}")
    ]
    
    if state.get("errors"):
        error_feedback = "CRITICAL: Your previous JSON attempt failed validation with these errors:\n"
        for err in state["errors"]:
            error_feedback += f"- {err}\n"
        error_feedback += "\nDO NOT REPEAT THE SAME MISTAKE. If it says 'got: StringArray', you MUST rewrite that specific query to use `[x IN n.propertyName | replace(x, ...)]`."
        messages.append(HumanMessage(content=error_feedback))
    
    try:
        response = llm.invoke(messages)
        raw_content = response.content.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(raw_content)
        
        print("Successfully generated JSON from LLM.")
        return {"generated_json": parsed_json, "status": "generated", "errors": []}
        
    except Exception as e:
        print(f"LLM Error encountered: {e}. Waiting 30s before retry...")
        time.sleep(30)
        return {"errors": [str(e)], "retry_count": state["retry_count"] + 1, "status": "llm_error"}

def validate_neo4j_node(state: GraphState) -> GraphState:
    print("-> Executing: Neo4j Validation Node (Syntax, Type Rules & Runtime)")
    driver = GraphDatabase.driver("bolt://localhost:8083", auth=None)
    data = state["generated_json"]
    errors = []
    
    try:
        with driver.session() as session:
            for label, properties in tqdm(data.items(), desc="Validating Node Labels"):
                label_check = session.run("CALL db.labels() YIELD label WHERE label = $lbl RETURN count(label) AS c", lbl=label).single()["c"]
                if label_check == 0:
                    errors.append(f"Label {label} not found in database.")
                    continue
                    
                for prop, details in properties.items():
                    prop_check = session.run("MATCH (n:`" + label + "`) WHERE n." + prop + " IS NOT NULL RETURN count(n) AS c").single()["c"]
                    if prop_check == 0:
                        errors.append(f"Property {prop} not found for label {label}.")
                        continue
                        
                    cypher_query = details["cypher"]
                    
                    if prop.endswith('s') and re.search(r'(replace|split|toLower|toUpper)\(\s*[a-zA-Z0-9_]+\.' + prop + r'\s*,', cypher_query):
                        errors.append(
                            f"SYNTAX REJECTION for {label}.{prop}: You wrote `{cypher_query}`. "
                            f"Because '{prop}' is a plural Array property, you CANNOT use `replace(n.{prop}, ...)`. "
                            f"You MUST rewrite it as `SET n.{prop} = [x IN n.{prop} | replace(x, ...)]`"
                        )
                        continue
                    
                    try:
                        session.run("EXPLAIN " + cypher_query)
                    except Exception as ce:
                        errors.append(f"Invalid Cypher syntax for {label}.{prop}: {str(ce)}")
                        continue
                        
                    if " SET " in cypher_query:
                        dry_run_query = cypher_query.replace(" SET ", " WITH n LIMIT 1 SET ")
                    else:
                        dry_run_query = cypher_query + " LIMIT 1"
                        
                    tx = session.begin_transaction()
                    try:
                        tx.run(dry_run_query)
                    except Exception as runtime_error:
                        err_msg = str(runtime_error)
                        errors.append(
                            f"Runtime Execution Error for {label}.{prop}: {err_msg}. "
                            f"REWRITE REQUIREMENT: SET n.{prop} = [x IN n.{prop} | replace(x, ...)]"
                        )
                    finally:
                        tx.rollback()
                        
    finally:
        driver.close()
        
    if errors:
        print(f"Validation failed with {len(errors)} errors. Routing back to LLM for correction.")
        return {"errors": errors, "retry_count": state["retry_count"] + 1, "status": "validation_failed"}
        
    print("Validation finished successfully. All queries are syntactically and type-safe.")
    return {"status": "validated"}

def router(state: GraphState) -> str:
    print(f"-> Routing from status: {state['status']}")
    if state["status"] == "read":
        return "generate"
    if state["status"] in ["llm_error", "validation_failed"]:
        if state["retry_count"] <= 3:
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
workflow.add_conditional_edges(
    "validate", 
    router, 
    {"generate": "generate", "end": END}
)

app = workflow.compile()

if __name__ == "__main__":
    print("=== Starting Self-Correcting LangGraph Execution ===")
    initial_state = {"retry_count": 0, "errors": []}
    result = app.invoke(initial_state)
    
    if "generated_json" in result and result["status"] == "validated":
        with open("generated_queries.json", "w") as f:
            json.dump(result["generated_json"], f, indent=2)
        print("Successfully saved validated queries to generated_queries.json")
    else:
        print("Failed to generate valid queries after maximum retries.")
            
    print("=== Execution Complete ===")
    if result.get("errors"):
        print("Final Unresolved Errors:")
        for e in result.get("errors", []):
            print(f" - {e}")