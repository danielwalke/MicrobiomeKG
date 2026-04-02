import os
import json
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

class GraphState(TypedDict):
    topic: str
    available_databases: List[str]
    selected_databases: List[str]
    error: str

def decide_databases(state: GraphState):
    llm = ChatOpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        model="qwen3-235b-a22b",
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    
    prompt = (
        f"Topic: {state['topic']}\n"
        f"Available Databases: {json.dumps(state['available_databases'])}\n"
        "Select the most relevant databases from the available list based on the topic. "
        "Respond strictly in JSON format with a single key 'selected_databases' containing a list of strings."
    )
    
    if state.get("error"):
        prompt += f"\nPrevious Error to fix: {state['error']}"
        
    response = llm.invoke(prompt)
    
    try:
        parsed_output = json.loads(response.content)
        selected = parsed_output.get("selected_databases", [])
        if not isinstance(selected, list):
            raise ValueError("selected_databases key must contain a list")
        return {"selected_databases": selected, "error": ""}
    except Exception as e:
        return {"selected_databases": [], "error": str(e)}

def validate_output(state: GraphState):
    if state.get("error"):
        return {"error": state["error"]}
        
    selected = state.get("selected_databases", [])
    available = state.get("available_databases", [])
    
    if not selected:
        return {"error": "The list of selected databases is empty."}
        
    invalid_dbs = [db for db in selected if db not in available]
    
    if invalid_dbs:
        return {"error": f"Invalid databases returned: {invalid_dbs}. Only select from the provided available databases."}
        
    return {"error": ""}

def route_validation(state: GraphState):
    if state.get("error"):
        return "decide_databases"
    return "save_output"

def save_output(state: GraphState):
    output_path = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/selectedDatabases.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump({"selected_databases": state["selected_databases"]}, f, indent=4)
        
    return state

def main():
    workflow = StateGraph(GraphState)

    workflow.add_node("decide_databases", decide_databases)
    workflow.add_node("validate_output", validate_output)
    workflow.add_node("save_output", save_output)

    workflow.set_entry_point("decide_databases")
    workflow.add_edge("decide_databases", "validate_output")
    workflow.add_conditional_edges(
        "validate_output",
        route_validation,
        {
            "decide_databases": "decide_databases",
            "save_output": "save_output"
        }
    )
    workflow.add_edge("save_output", END)

    app = workflow.compile()

    available_path = os.path.expanduser("~/git/MicrobiomeKG/config/s0_access/dbs_without_errors.json")
    with open(available_path, "r") as f:
        available_dbs = json.load(f)
        
    topic_path = os.path.expanduser("~/git/MicrobiomeKG/config/s0_access/topicDescription.txt")
    with open(topic_path, "r") as f:
        topic_desc = f.read().strip()
        
    initial_state = {
        "topic": topic_desc,
        "available_databases": available_dbs,
        "selected_databases": [],
        "error": ""
    }
    
    return app.invoke(initial_state)

if __name__ == "__main__":
    main()