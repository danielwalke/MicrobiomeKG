from typing import List, Optional, Any
from pydantic import BaseModel, Field

class PropertyMetadata(BaseModel):
    """
    Holds metadata about a Neo4j property, including sample values and local schema connections.
    """
    node_label: str = Field(..., description="The label of the Neo4j node.")
    property_name: str = Field(..., description="The name of the property key.")
    data_type: str = Field("Unknown", description="The data type of the property values.")
    sample_values: List[Any] = Field(default_factory=list, description="A few sample values of the property from the database.")
    relationships: List[str] = Field(default_factory=list, description="Local schema connections (relationships and adjacent node labels).")

class AnalyzerOutput(BaseModel):
    """
    Output structure for the Fast Path Analyzer Agent.
    """
    importance_score: int = Field(..., ge=0, le=10, description="Importance of this property to the domain model (0 to 10).")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Confidence in the assigned importance score (0% to 100%).")
    reasoning: str = Field(..., description="Detailed explanation of the assigned scores.")

class JudgeOutput(BaseModel):
    """
    Output structure for the Targeted Judge QA step.
    """
    is_justified: bool = Field(..., description="Whether the reasoning justifies the assigned score.")
    revised_score: Optional[int] = Field(None, ge=0, le=10, description="A revised score if the original score was not justified.")
    correction_reason: str = Field(..., description="A one-sentence explanation for the verdict/correction.")

class EvaluationResult(BaseModel):
    """
    Combines the results of the entire evaluation pipeline for a single property.
    """
    property_metadata: PropertyMetadata
    
    # Analyzer Agent
    analyzer_score: int
    analyzer_confidence: float
    analyzer_reasoning: str
    
    # Escalation to Research Agent
    escalated_to_research: bool = False
    research_score: Optional[int] = None
    research_reasoning: Optional[str] = None
    
    # Intermediary evaluation (before the Judge)
    final_before_judge_score: int
    final_before_judge_reasoning: str
    
    # Judge Agent (QA Audit)
    judged: bool = False
    judge_justified: Optional[bool] = None
    judge_correction_reason: Optional[str] = None
    
    # Final Outcome
    final_importance_score: int
    final_rationale: str
