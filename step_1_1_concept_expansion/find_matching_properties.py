import os
import time
import itertools
from typing import List, Dict, Any, Tuple, Set
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from step_4_filtered_metaconcept_graph.get_properties_markdown import extract_schema_with_samples_md
from tqdm import tqdm

API_DELAY_SECONDS = 3

class Overlap(BaseModel):
    source_label: str
    source_property: str
    target_label: str
    target_property: str
    reason: str
    sample_evidence: str
    confidence_score: int = Field(ge=1, le=10)

class PairwiseOverlaps(BaseModel):
    thought_process: str = Field(description="Analyze the identifier formats. State explicitly if they are generic internal IDs or specific domain cross-references.")
    overlaps: List[Overlap]

class GraphState(TypedDict):
    schema_dict: Dict[str, str]
    pairs: List[Tuple[str, str]]
    current_index: int
    all_overlaps: List[Dict[str, Any]]
    current_overlaps: List[Dict[str, Any]]
    errors: str
    retries: int

schema_md_dict = extract_schema_with_samples_md()

load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    model="qwen3-235b-a22b",
    temperature=0,
    timeout=30,
    max_retries=1
).with_structured_output(PairwiseOverlaps)

def get_source_prefix(label: str) -> str:
    if '_' in label:
        return label.split('_')[0].lower()
    return label.lower()

def get_cross_database_pairs(labels: List[str]) -> List[Tuple[str, str]]:
    all_pairs = list(itertools.combinations(labels, 2))
    valid_pairs = []
    for a, b in all_pairs:
        if get_source_prefix(a) != get_source_prefix(b):
            valid_pairs.append((a, b))
    return valid_pairs

valid_label_pairs = get_cross_database_pairs(list(schema_md_dict.keys()))
total_pairs = len(valid_label_pairs)
pbar = tqdm(total=total_pairs, desc="Processing Schema Pairs")

def extract_keys(md_str: str) -> Set[str]:
    keys = set()
    lines = md_str.strip().split('\n')
    for line in lines:
        if line.startswith('|') and not line.startswith('| ---') and not line.startswith('| Property Key'):
            parts = line.split('|')
            if len(parts) > 2:
                key = parts[1].strip().replace('`', '')
                keys.add(key)
    return keys

def init_pairs(state: GraphState):
    return {
        "pairs": valid_label_pairs, 
        "current_index": 0, 
        "all_overlaps": [], 
        "current_overlaps": [], 
        "errors": "", 
        "retries": 0
    }

def generate_overlaps(state: GraphState):
    idx = state["current_index"]
    label_a, label_b = state["pairs"][idx]
    md_a = state["schema_dict"][label_a]
    md_b = state["schema_dict"][label_b]
    
    tqdm.write(f"\n[INFO] Starting Pair {idx + 1}/{len(state['pairs'])}: '{label_a}' vs '{label_b}' (Retry: {state['retries']})")
    
    error_context = ""
    if state["errors"] and not state["errors"].startswith("API_"):
        tqdm.write(f"[WARN] Passing previous errors to LLM: {state['errors']}")
        error_context = f"\nCorrect these hallucinated keys: {state['errors']}"
        
    prompt_text = """
    Analyze these schemas to find EXACT identifier mapping across different databases.
    
    CRITICAL INSTRUCTIONS:
    1. YOUR GOAL: Find exact ID matching of the same entity across different databases based on their identifier format.
    2. EXAMINE IDENTIFIER FORMATS: Only match properties if their samples share a highly specific format (e.g., 'GO:XXXXXXX', 'IPRXXXXXX', complex alphanumeric codes).
    3. IGNORE INTERNAL IDs: Do NOT match generic auto-incrementing integers, internal database IDs (like '<id>' or '__id'), versions, or generic names.
    4. BE RESTRICTIVE: 99% of label pairs will have ZERO overlaps.
    
    POSITIVE MATCH EXAMPLE:
    Label A: Interpro_Classification (id: GO:0005576)
    Label B: GeneOntologyTerm (id: GO:0000011)
    thought_process: "Both use the 'GO:XXXXXXX' format for their 'id' properties, representing Gene Ontology terms. This is a valid cross-database entity match."
    overlaps: [{{"source_label": "Interpro_Classification", "source_property": "id", "target_label": "GeneOntologyTerm", "target_property": "id", "reason": "Both use GO:XXXXXXX formats", "sample_evidence": "GO:0005576 matches GO:0000011 format", "confidence_score": 10}}]
    
    NEGATIVE MATCH EXAMPLE:
    Label A: metadata (__id: 1862677168003, version: 1)
    Label B: PUBLICATION (__id: 11087660261771, version: 2)
    thought_process: "Both have '__id' and 'version', but these are generic internal database numbers, not specific domain identifiers linking the same entity."
    overlaps: []
    
    Label A: {label_a}
    {md_a}
    
    Label B: {label_b}
    {md_b}
    {error_context}
    """
    
    prompt = PromptTemplate.from_template(prompt_text)
    chain = prompt | llm
    
    tqdm.write(f"[INFO] Sleeping for {API_DELAY_SECONDS} seconds...")
    time.sleep(API_DELAY_SECONDS)
    
    tqdm.write("[INFO] Awaiting LLM API response...")
    try:
        result = chain.invoke({
            "label_a": label_a,
            "md_a": md_a,
            "label_b": label_b,
            "md_b": md_b,
            "error_context": error_context
        })
        tqdm.write(f"[THOUGHT PROCESS] {result.thought_process}")
        
        overlap_summaries = [f"{o.source_property} <-> {o.target_property} (Conf: {o.confidence_score})" for o in result.overlaps]
        if overlap_summaries:
            tqdm.write(f"[MATCHES FOUND] {len(overlap_summaries)} overlaps: {', '.join(overlap_summaries)}")
        else:
            tqdm.write("[MATCHES FOUND] 0 overlaps detected.")
            
        return {"current_overlaps": [overlap.model_dump() for overlap in result.overlaps], "errors": ""}
    except Exception as e:
        tqdm.write(f"[ERROR] API Call Failed: {str(e)}")
        return {"current_overlaps": [], "errors": f"API_ERROR_{str(e)}"}

def validate_overlaps(state: GraphState):
    idx = state["current_index"]
    label_a, label_b = state["pairs"][idx]
    
    errors = []
    if state.get("errors", "").startswith("API_ERROR"):
        errors.append("API failure.")
    else:
        valid_a = extract_keys(state["schema_dict"][label_a])
        valid_b = extract_keys(state["schema_dict"][label_b])
        
        for overlap in state["current_overlaps"]:
            if overlap["source_property"] not in valid_a:
                errors.append(f"Invalid source_property: {overlap['source_property']}")
            if overlap["target_property"] not in valid_b:
                errors.append(f"Invalid target_property: {overlap['target_property']}")
            
    if errors and state["retries"] < 3:
        tqdm.write(f"[ERROR] Validation failed: {errors}. Retrying...")
        return {"errors": "; ".join(errors), "retries": state["retries"] + 1}
        
    pbar.update(1)
    tqdm.write(f"[SUCCESS] Pair validated.")
    
    return {
        "all_overlaps": state["all_overlaps"] + state["current_overlaps"],
        "current_index": idx + 1,
        "errors": "",
        "retries": 0,
        "current_overlaps": []
    }

def route_workflow(state: GraphState):
    if state["errors"] and state["retries"] < 3:
        return "generate_overlaps"
    if state["current_index"] >= len(state["pairs"]):
        return "end"
    return "generate_overlaps"

def format_final_tsv(overlaps: List[Dict[str, Any]]) -> str:
    tsv_lines = ["Source Label\tSource Property\tTarget Label\tTarget Property\tConfidence\tSample Evidence\tReason"]
    
    overlaps_sorted = sorted(overlaps, key=lambda x: x.get('confidence_score', 0), reverse=True)
    
    for o in overlaps_sorted:
        conf = str(o.get('confidence_score', 'N/A'))
        evidence = str(o.get('sample_evidence', 'N/A')).replace('\t', ' ').replace('\n', ' ')
        reason = str(o['reason']).replace('\t', ' ').replace('\n', ' ')
        tsv_lines.append(f"{o['source_label']}\t{o['source_property']}\t{o['target_label']}\t{o['target_property']}\t{conf}\t{evidence}\t{reason}")
    
    return "\n".join(tsv_lines)

workflow = StateGraph(GraphState)
workflow.add_node("init_pairs", init_pairs)
workflow.add_node("generate_overlaps", generate_overlaps)
workflow.add_node("validate_overlaps", validate_overlaps)

workflow.set_entry_point("init_pairs")
workflow.add_edge("init_pairs", "generate_overlaps")
workflow.add_edge("generate_overlaps", "validate_overlaps")
workflow.add_conditional_edges(
    "validate_overlaps",
    route_workflow,
    {"generate_overlaps": "generate_overlaps", "end": END}
)

app = workflow.compile()

initial_state = {
    "schema_dict": schema_md_dict,
    "pairs": valid_label_pairs,
    "current_index": 0,
    "all_overlaps": [],
    "current_overlaps": [],
    "errors": "",
    "retries": 0
}

result_state = app.invoke(initial_state)

pbar.close()

final_tsv = format_final_tsv(result_state["all_overlaps"])
with open("schema_overlaps.tsv", "w", encoding="utf-8") as file:
    file.write(final_tsv)