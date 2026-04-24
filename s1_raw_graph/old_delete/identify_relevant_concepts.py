# import os
# import json
# from typing import TypedDict, List
# from dotenv import load_dotenv
# from langgraph.graph import StateGraph, START, END
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# from utils.extract_properties_markdown import extract_schema_with_samples_md
# from tqdm import tqdm

# load_dotenv()

# TOPIC_FILE_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s0_access/topicDescription.txt")
# CONCEPT_LABELS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/concept_labels.json")
# POSSIBLE_CONCEPTS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/possible_concept_labels.json")
# RELEVANT_CONCEPTS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/relevant_additional_concepts.json")
# REMOVED_CONCEPTS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/removed_additional_concepts.json")

# class GraphState(TypedDict):
#     topic: str
#     concept: str
#     schema_info: str
#     retries: int
#     generation: str
#     is_valid: bool
#     included: bool
#     reasoning: str
#     errors: List[str]

# def evaluate_concept(state: GraphState):
#     topic = state["topic"]
#     concept = state["concept"]
#     schema_info = state["schema_info"]
#     errors = state.get("errors", [])
#     retries = state.get("retries", 0)
    
#     llm = ChatOpenAI(
#         api_key=os.getenv("API_KEY"),
#         base_url=os.getenv("BASE_URL"),
#         model="qwen3-235b-a22b",
#         model_kwargs={"response_format": {"type": "json_object"}}
#     )
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", "You are an AI that evaluates if a specific concept applies to a topic. Output ONLY valid JSON."),
#         ("user", "Topic: {topic}\nConcept: {concept}\nSchema: {schema_info}\nPrevious Errors: {errors}\nShould this concept be included based on the topic? Return a JSON object with a boolean 'included' and a string 'reasoning'. Format: {{{{ \"included\": true, \"reasoning\": \"text\" }}}}")
#     ])
    
#     chain = prompt | llm
#     response = chain.invoke({
#         "topic": topic,
#         "concept": concept,
#         "schema_info": schema_info,
#         "errors": json.dumps(errors)
#     })
    
#     return {"generation": response.content, "retries": retries + 1}

# def validate_output(state: GraphState):
#     generation = state["generation"]
#     errors = []
    
#     try:
#         parsed_json = json.loads(generation)
#         if not isinstance(parsed_json, dict):
#             errors.append("Output is not a JSON object")
#         elif "included" not in parsed_json or "reasoning" not in parsed_json:
#             errors.append("JSON missing 'included' or 'reasoning' keys")
#         elif not isinstance(parsed_json["included"], bool):
#             errors.append("'included' must be a boolean")
#         else:
#             return {
#                 "is_valid": True,
#                 "included": parsed_json["included"],
#                 "reasoning": str(parsed_json["reasoning"]),
#                 "errors": []
#             }
#     except json.JSONDecodeError:
#         errors.append("Output is not valid JSON")
        
#     return {"is_valid": False, "errors": errors, "included": False, "reasoning": ""}

# def route_validation(state: GraphState):
#     if state.get("is_valid"):
#         return END
#     if state.get("retries", 0) >= 3:
#         return END
#     return "evaluate_concept"

# def main():
#     workflow = StateGraph(GraphState)
#     workflow.add_node("evaluate_concept", evaluate_concept)
#     workflow.add_node("validate_output", validate_output)

#     workflow.add_edge(START, "evaluate_concept")
#     workflow.add_edge("evaluate_concept", "validate_output")
#     workflow.add_conditional_edges(
#         "validate_output",
#         route_validation,
#         {
#             END: END,
#             "evaluate_concept": "evaluate_concept"
#         }
#     )

#     graph_app = workflow.compile()

#     schema_md_dict = extract_schema_with_samples_md()
#     schema_md_dict = {k: v for k, v in schema_md_dict.items() if not k.isupper()}
#     schema_md_dict = {k.split("_")[-1]: v for k, v in schema_md_dict.items()}

#     with open(TOPIC_FILE_PATH, "r") as f:
#         topic = f.read().strip()

#     final_results = {}
#     removed_results = {}
#     existing_upper_concepts = set()

#     with open(CONCEPT_LABELS_PATH, "r") as f:
#         existing_concepts = json.load(f)
#         for concept in existing_concepts:
#             if concept.isupper():
#                 existing_upper_concepts.add(concept)

#     valid_concepts = []
#     with open(POSSIBLE_CONCEPTS_PATH, "r") as f:
#         possible_concept_labels = json.load(f).keys()
#         for possible_concept in possible_concept_labels:
#             if possible_concept in schema_md_dict and possible_concept.upper() not in existing_upper_concepts:
#                 valid_concepts.append(possible_concept)

#     for concept in tqdm(valid_concepts, desc="Evaluating concepts"):
#         schema_info = schema_md_dict[concept]
        
#         initial_state = {
#             "topic": topic,
#             "concept": concept,
#             "schema_info": schema_info,
#             "retries": 0,
#             "generation": "",
#             "is_valid": False,
#             "included": False,
#             "reasoning": "",
#             "errors": []
#         }
        
#         result = graph_app.invoke(initial_state)
        
#         if result.get("is_valid") and result.get("included"):
#             final_results[concept] = result["reasoning"]
#         else:
#             reason = result.get("reasoning") if result.get("is_valid") else "Failed validation after max retries."
#             removed_results[concept] = reason

#     with open(RELEVANT_CONCEPTS_PATH, "w") as f:
#         json.dump(final_results, f, indent=4)

#     with open(REMOVED_CONCEPTS_PATH, "w") as f:
#         json.dump(removed_results, f, indent=4)

#     print(json.dumps(final_results, indent=4))

# if __name__ == "__main__":
#     main()