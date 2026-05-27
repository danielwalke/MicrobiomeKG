import random
import json
from typing import Dict, Any, List, Optional
from neo4j import Driver

from .schema import PropertyMetadata, AnalyzerOutput, JudgeOutput, EvaluationResult
from .database import (
    get_node_labels,
    get_properties_for_label,
    get_property_metadata,
    execute_cypher_query
)
from .search import web_search
from .agents import AnalyzerAgent, ResearchAgent, JudgeAgent, get_openai_client, get_model_name


class EvaluationPipeline:
    """
    Orchestrates the 6-Step Escalation & Evaluation Pipeline for a Neo4j KG.
    """
    def __init__(
        self,
        driver: Driver,
        confidence_threshold: float = 75.0,
        judge_sanity_check_rate: float = 0.10, # 10% sanity check
        llm_client: Optional[Any] = None,
        model: Optional[str] = None
    ):
        self.driver = driver
        self.confidence_threshold = confidence_threshold
        self.judge_sanity_check_rate = judge_sanity_check_rate
        
        # Initialize agents
        client = llm_client or get_openai_client()
        model_name = model or get_model_name()
        
        self.analyzer = AnalyzerAgent(client=client, model=model_name)
        self.judge = JudgeAgent(client=client, model=model_name)
        
        # We pass search and cypher query tools to the Research agent
        def search_tool(q: str):
            return web_search(q)
            
        def cypher_tool(q: str):
            return execute_cypher_query(self.driver, q)
            
        self.research_agent = ResearchAgent(
            web_search_tool=search_tool,
            db_query_tool=cypher_tool,
            client=client,
            model=model_name
        )

    def run(self) -> Dict[str, Any]:
        """
        Executes the evaluation pipeline on all labels and properties in the database.
        Returns a dictionary mapping label -> property_name -> {importance_score, rationale}.
        """
        print("[Pipeline] Step 1: Gathering node labels and schema...")
        labels = get_node_labels(self.driver)
        print(f"[Pipeline] Found {len(labels)} labels: {labels}")
        
        all_results: List[EvaluationResult] = []
        
        for label in labels:
            properties = get_properties_for_label(self.driver, label)
            print(f"[Pipeline] Label '{label}' properties: {properties}")
            
            for prop in properties:
                # Gather property metadata
                metadata = get_property_metadata(self.driver, label, prop)
                
                # Step 1 & 2: Fast Path (Analyzer)
                print(f"[Pipeline] Running Analyzer on {label}.{prop}...")
                analyzer_out: AnalyzerOutput = self.analyzer.evaluate(metadata)
                print(f"  -> Score: {analyzer_out.importance_score}, Confidence: {analyzer_out.confidence_score}%")
                
                # Step 3 & 4: Confidence Threshold / Escalation to Research Agent
                escalated = False
                res_score = None
                res_reasoning = None
                
                final_before_judge_score = analyzer_out.importance_score
                final_before_judge_reasoning = analyzer_out.reasoning
                
                if analyzer_out.confidence_score < self.confidence_threshold:
                    print(f"  -> Low confidence ({analyzer_out.confidence_score}% < {self.confidence_threshold}%). Escalating to Research Agent...")
                    escalated = True
                    research_out = self.research_agent.research(metadata, analyzer_out)
                    
                    res_score = research_out.get("importance_score")
                    res_reasoning = research_out.get("reasoning")
                    
                    if res_score is not None:
                        final_before_judge_score = res_score
                    if res_reasoning is not None:
                        final_before_judge_reasoning = res_reasoning
                        
                    print(f"  -> Research Result: Score: {final_before_judge_score}")
                
                # Step 5: Targeted Judge (Quality Assurance)
                # Gray Area Trigger: score between 3 and 6 inclusive
                is_gray_area = 3 <= final_before_judge_score <= 6
                # Sanity Check Trigger: 5-10% of obvious scores (0-2 and 7-10)
                is_obvious = final_before_judge_score <= 2 or final_before_judge_score >= 7
                is_sanity_checked = is_obvious and (random.random() < self.judge_sanity_check_rate)
                
                judged = False
                judge_justified = None
                judge_correction_reason = None
                final_score = final_before_judge_score
                final_rationale = final_before_judge_reasoning
                
                if is_gray_area or is_sanity_checked:
                    trigger_type = "Gray Area (3-6)" if is_gray_area else "Sanity Check (0-2, 7-10)"
                    print(f"  -> Routing to Judge via {trigger_type} trigger...")
                    
                    judged = True
                    judge_out: JudgeOutput = self.judge.audit(metadata, final_before_judge_score, final_before_judge_reasoning)
                    judge_justified = judge_out.is_justified
                    judge_correction_reason = judge_out.correction_reason
                    
                    if not judge_justified:
                        if judge_out.revised_score is not None:
                            final_score = judge_out.revised_score
                        final_rationale = f"{final_before_judge_reasoning} | Corrected by Judge: {judge_correction_reason}"
                        print(f"  -> Judge verdict: UNJUSTIFIED. Revised score: {final_score}")
                    else:
                        print("  -> Judge verdict: JUSTIFIED.")
                        
                # Create final result record
                result = EvaluationResult(
                    property_metadata=metadata,
                    analyzer_score=analyzer_out.importance_score,
                    analyzer_confidence=analyzer_out.confidence_score,
                    analyzer_reasoning=analyzer_out.reasoning,
                    escalated_to_research=escalated,
                    research_score=res_score,
                    research_reasoning=res_reasoning,
                    final_before_judge_score=final_before_judge_score,
                    final_before_judge_reasoning=final_before_judge_reasoning,
                    judged=judged,
                    judge_justified=judge_justified,
                    judge_correction_reason=judge_correction_reason,
                    final_importance_score=final_score,
                    final_rationale=final_rationale
                )
                all_results.append(result)
                
        # Step 6: Deterministic JSON Storage (The Final Export)
        # Structure the data as requested: NodeLabel -> property_name -> {final_importance_score, final_rationale}
        print("[Pipeline] Step 6: Aggregating final evaluations...")
        export_data = {}
        for res in all_results:
            label = res.property_metadata.node_label
            prop = res.property_metadata.property_name
            
            if label not in export_data:
                export_data[label] = {}
                
            export_data[label][prop] = {
                "importance_score": res.final_importance_score,
                "rationale": res.final_rationale
            }
            
        return export_data
