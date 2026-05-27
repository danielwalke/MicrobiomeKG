import os
import json
import re
import time
from typing import Dict, Any, List, Optional, Callable
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

from .schema import PropertyMetadata, AnalyzerOutput, JudgeOutput

# Load environment variables
load_dotenv(find_dotenv())

def get_openai_client() -> OpenAI:
    """
    Initializes and returns the OpenAI client using environment variables.
    """
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    
    # If BASE_URL is not specified, it will default to OpenAI's public API endpoint.
    return OpenAI(api_key=api_key, base_url=base_url)

def get_model_name() -> str:
    """
    Retrieves the model name from environment variables, defaulting to qwen3.5-397b-a17b.
    """
    return os.getenv("MODEL_NAME", "qwen3.5-397b-a17b")

def extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extracts JSON from LLM response text, handling markdown blocks and surrounding text.
    """
    # 1. Try to find JSON inside a markdown code block
    json_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except Exception:
            pass
            
    # 2. Try to find the outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
            
    # 3. Direct JSON load attempt
    return json.loads(text)


class AnalyzerAgent:
    """
    Fast, toolless agent that evaluates a property's importance and confidence.
    """
    def __init__(self, client: Optional[OpenAI] = None, model: Optional[str] = None):
        self.client = client or get_openai_client()
        self.model = model or get_model_name()

    def evaluate(self, metadata: PropertyMetadata) -> AnalyzerOutput:
        system_prompt = (
            "You are an expert Knowledge Graph data modeler. Your task is to evaluate "
            "the importance of a node property. You must assess the property based only "
            "on the provided metadata, schema, and sample values."
        )
        
        user_prompt = f"""
Analyze the following property and assign an importance score (0-10) and a confidence score (0-100%):

Node Label: {metadata.node_label}
Property Name: {metadata.property_name}
Data Type: {metadata.data_type}
Sample Values: {metadata.sample_values}
Local Schema Connections: {metadata.relationships}

Scoring Rules:
- Importance Score (0 to 10):
  * 0-2: Obvious metadata/junk (e.g. system IDs, temporary fields, timestamps, created_by).
  * 3-6: Secondary fields (e.g. descriptive attributes, optional fields, secondary metrics).
  * 7-10: Core domain properties (e.g. primary labels, identifiers, essential entity attributes, core relationships keys).
- Confidence Score (0% to 100%):
  * Assign a high confidence (>=75%) if the property's name is clear and its meaning/utility is obvious from sample values or local connections.
  * Assign a low confidence (<75%) if the name is ambiguous, abbreviation/jargon is unclear, or sample values are empty/unhelpful.

Output MUST be a valid JSON object in this exact format:
{{
  "importance_score": <integer from 0 to 10>,
  "confidence_score": <float from 0.0 to 100.0>,
  "reasoning": "<detailed explanation of your scoring and confidence assessment>"
}}
Do not include any explanation or formatting outside the JSON block.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            parsed = extract_json(content)
            
            return AnalyzerOutput(
                importance_score=int(parsed["importance_score"]),
                confidence_score=float(parsed["confidence_score"]),
                reasoning=str(parsed["reasoning"])
            )
        except Exception as e:
            # Safe fallback if the model fails or returns malformed response
            print(f"AnalyzerAgent error for {metadata.node_label}.{metadata.property_name}: {e}")
            return AnalyzerOutput(
                importance_score=5,
                confidence_score=50.0,
                reasoning=f"Fallback assignment due to Analyzer error: {str(e)}"
            )


class ResearchAgent:
    """
    Escalated agent utilizing Web Search and Neo4j Database Query tools
    to resolve low-confidence properties.
    """
    def __init__(
        self,
        web_search_tool: Callable[[str], List[Dict[str, str]]],
        db_query_tool: Callable[[str], List[Dict[str, Any]]],
        client: Optional[OpenAI] = None,
        model: Optional[str] = None,
        max_steps: int = 5
    ):
        self.web_search = web_search_tool
        self.db_query = db_query_tool
        self.client = client or get_openai_client()
        self.model = model or get_model_name()
        self.max_steps = max_steps

    def research(self, metadata: PropertyMetadata, analyzer_output: AnalyzerOutput) -> Dict[str, Any]:
        """
        Runs the ReAct loop to investigate the property and output refined score/reasoning.
        """
        system_prompt = (
            "You are a specialized Research Agent investigating ambiguous or confusing "
            "properties in a Neo4j Knowledge Graph. You are equipped with Web Search "
            "and Database Query tools. Use them to investigate the meaning, context, and usage "
            "of the property to determine a definitive importance score."
        )

        history = [
            {"role": "system", "content": system_prompt}
        ]

        user_context = f"""
Entity (Node Label): {metadata.node_label}
Property Name: {metadata.property_name}
Data Type: {metadata.data_type}
Sample Values: {metadata.sample_values}
Local Schema Connections: {metadata.relationships}

Initial Analyzer Assessment:
- Importance Score: {analyzer_output.importance_score}
- Confidence Score: {analyzer_output.confidence_score}%
- Rationale: {analyzer_output.reasoning}

Available Tools:
1. web_search("query"): Queries DuckDuckGo for the term/context.
2. database_query("Cypher query"): Runs a read-only Cypher query on the Neo4j database (e.g. to inspect node count, value frequencies, or distribution).

Goal:
Refine the importance score (0-10) and define the property precisely.

Instructions:
You operate in a loop of Thought, Action, and Observation.
To execute a tool call, output:
Action: tool_name("argument")

For example:
Action: web_search("meaning of field {metadata.property_name} in database")
or:
Action: database_query("MATCH (n:`{metadata.node_label}`) WHERE n.`{metadata.property_name}` IS NOT NULL RETURN count(n)")

After calling a tool, you will be provided with an Observation.
Once you have sufficient information, output:
Final Answer:
{{
  "importance_score": <int 0-10>,
  "reasoning": "<detailed explanation of your final score, defining the property and what you discovered>"
}}

Let's begin! Write your first Thought and Action, or output your Final Answer.
"""
        history.append({"role": "user", "content": user_context})
        
        print(f"\n[ResearchAgent] Starting investigation for {metadata.node_label}.{metadata.property_name}...")

        for step in range(self.max_steps):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=history,
                    temperature=0.0
                )
                response_text = response.choices[0].message.content
                print(f"--- Step {step + 1} Agent Output ---\n{response_text}\n-------------------------")
                
                history.append({"role": "assistant", "content": response_text})

                # Check for Final Answer
                final_match = re.search(r"Final Answer:\s*(\{[\s\S]*\})", response_text)
                if final_match:
                    try:
                        parsed = extract_json(final_match.group(1))
                        return {
                            "importance_score": int(parsed["importance_score"]),
                            "reasoning": str(parsed["reasoning"])
                        }
                    except Exception as json_err:
                        # Attempt to parse response_text itself as JSON if Final Answer block extraction failed
                        try:
                            parsed = extract_json(response_text)
                            return {
                                "importance_score": int(parsed["importance_score"]),
                                "reasoning": str(parsed["reasoning"])
                            }
                        except Exception:
                            print(f"[ResearchAgent] Error parsing final answer JSON: {json_err}")
                
                # Check for Action
                action_match = re.search(r'Action:\s*(\w+)\s*\(\s*["\']([\s\S]*?)["\']\s*\)', response_text)
                if action_match:
                    tool_name = action_match.group(1)
                    tool_arg = action_match.group(2)
                    
                    print(f"[ResearchAgent] Executing tool '{tool_name}' with arg: {tool_arg}")
                    
                    observation = ""
                    if tool_name == "web_search":
                        search_results = self.web_search(tool_arg)
                        # Format list of search results into readable string
                        formatted_results = []
                        for idx, r in enumerate(search_results):
                            if "error" in r:
                                formatted_results.append(f"Error: {r['error']}")
                            else:
                                formatted_results.append(f"[{idx+1}] Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}\n")
                        observation = "\n".join(formatted_results) if formatted_results else "No search results found."
                    elif tool_name == "database_query":
                        try:
                            db_results = self.db_query(tool_arg)
                            observation = json.dumps(db_results, default=str, indent=2)
                        except Exception as db_err:
                            observation = f"Database query error: {str(db_err)}"
                    else:
                        observation = f"Unknown tool: {tool_name}"
                        
                    print(f"[ResearchAgent] Observation: {observation[:200]}...")
                    history.append({"role": "user", "content": f"Observation:\n{observation}"})
                else:
                    # If model didn't call a tool or give final answer, prompt it to decide
                    history.append({
                        "role": "user",
                        "content": "Please select an action (Action: tool_name(\"arg\")) or provide the Final Answer."
                    })
                    
            except Exception as e:
                print(f"[ResearchAgent] Loop error: {e}")
                break

        # Fallback if no final answer is reached
        print(f"[ResearchAgent] Fallback: max steps reached without Final Answer for {metadata.node_label}.{metadata.property_name}")
        return {
            "importance_score": analyzer_output.importance_score,
            "reasoning": f"Escalated research completed with fallback. Initial Analyzer rationale: {analyzer_output.reasoning}"
        }


class JudgeAgent:
    """
    Deterministic QA Judge validating rationale against score.
    """
    def __init__(self, client: Optional[OpenAI] = None, model: Optional[str] = None):
        self.client = client or get_openai_client()
        self.model = model or get_model_name()

    def audit(self, metadata: PropertyMetadata, score: int, rationale: str) -> JudgeOutput:
        system_prompt = (
            "You are a strict QA Judge evaluating Node Property Importance Scores in a Knowledge Graph. "
            "You must ensure that the importance score aligns logically with the provided rationale."
        )

        user_prompt = f"""
Please evaluate the following score and rationale:

Node Label: {metadata.node_label}
Property Name: {metadata.property_name}
Property Metadata: {metadata.sample_values} (type: {metadata.data_type})
Assigned Importance Score: {score}
Rationale: {rationale}

Evaluation Tasks:
1. Is the assigned importance score justified by the reasoning and property metadata?
   - 0-2 (Obvious metadata/junk): system fields, technical IDs, audit timestamps, etc.
   - 3-6 (Secondary attributes): descriptive fields, metadata of business value, optional info.
   - 7-10 (Core keys): identifiers, vital domain definitions, primary attributes.
2. If the rationale indicates the property is secondary but has a score of 8, or if it is core but has a score of 1, it is unjustified.
3. If justified, set 'is_justified' to true.
4. If unjustified, set 'is_justified' to false, propose a corrected 'revised_score' (0-10), and write a one-sentence 'correction_reason'.

Output MUST be a single JSON object in this exact format:
{{
  "is_justified": <true/false>,
  "revised_score": <integer from 0 to 10 or null if justified>,
  "correction_reason": "<one sentence correction explanation>"
}}
Do not include any explanation or formatting outside the JSON block.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            parsed = extract_json(content)
            
            return JudgeOutput(
                is_justified=bool(parsed["is_justified"]),
                revised_score=int(parsed["revised_score"]) if parsed.get("revised_score") is not None else None,
                correction_reason=str(parsed["correction_reason"])
            )
        except Exception as e:
            print(f"JudgeAgent error for {metadata.node_label}.{metadata.property_name}: {e}")
            return JudgeOutput(
                is_justified=True,
                revised_score=None,
                correction_reason=f"Fallback due to Judge error: {str(e)}"
            )
