import pytest
from unittest.mock import MagicMock, patch
import json

from kg_node_filter.schema import PropertyMetadata, AnalyzerOutput, JudgeOutput
from kg_node_filter.database import sanitize_identifier, get_property_metadata
from kg_node_filter.agents import AnalyzerAgent, ResearchAgent, JudgeAgent, extract_json
from kg_node_filter.pipeline import EvaluationPipeline

# 1. Test JSON Extraction utility
def test_extract_json():
    # Standard JSON
    assert extract_json('{"a": 1}') == {"a": 1}
    # Markdown wrapped
    assert extract_json('some text\n```json\n{"a": 2}\n```\nmore text') == {"a": 2}
    # Outermost braces
    assert extract_json('random text {"a": 3} extra text') == {"a": 3}

# 2. Test Sanitization
def test_sanitize_identifier():
    assert sanitize_identifier("User") == "User"
    assert sanitize_identifier("User`Label") == "User``Label"

# 3. Test AnalyzerAgent
@patch("kg_node_filter.agents.OpenAI")
def test_analyzer_agent(mock_openai_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"importance_score": 8, "confidence_score": 90.0, "reasoning": "Core attribute"}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = AnalyzerAgent(client=mock_client, model="test-model")
    metadata = PropertyMetadata(
        node_label="User",
        property_name="email",
        data_type="String",
        sample_values=["a@b.com"],
        relationships=[]
    )
    
    res = agent.evaluate(metadata)
    assert res.importance_score == 8
    assert res.confidence_score == 90.0
    assert res.reasoning == "Core attribute"

# 4. Test ResearchAgent ReAct Loop
@patch("kg_node_filter.agents.OpenAI")
def test_research_agent_react_loop(mock_openai_class):
    mock_client = MagicMock()
    
    # We simulate a 2-step loop:
    # Step 1: Agent calls web_search
    # Step 2: Agent gives Final Answer
    mock_resp1 = MagicMock()
    mock_resp1.choices = [
        MagicMock(message=MagicMock(content='Thought: Let\'s query DDG.\nAction: web_search("user email importance")'))
    ]
    mock_resp2 = MagicMock()
    mock_resp2.choices = [
        MagicMock(message=MagicMock(content='Thought: Got the result.\nFinal Answer:\n{"importance_score": 9, "reasoning": "Emails are verified identifiers."}'))
    ]
    
    mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]
    
    # Mock tools
    mock_web_search = MagicMock(return_value=[{"title": "Email Info", "url": "http://email.com", "snippet": "Crucial key"}])
    mock_db_query = MagicMock(return_value=[])
    
    agent = ResearchAgent(
        web_search_tool=mock_web_search,
        db_query_tool=mock_db_query,
        client=mock_client,
        model="test-model",
        max_steps=5
    )
    
    metadata = PropertyMetadata(
        node_label="User",
        property_name="email",
        data_type="String",
        sample_values=[],
        relationships=[]
    )
    analyzer_out = AnalyzerOutput(importance_score=5, confidence_score=40.0, reasoning="Unknown")
    
    res = agent.research(metadata, analyzer_out)
    
    # Assert tool was called with correct argument
    mock_web_search.assert_called_once_with("user email importance")
    assert res["importance_score"] == 9
    assert "Emails are verified identifiers" in res["reasoning"]

# 5. Test JudgeAgent
@patch("kg_node_filter.agents.OpenAI")
def test_judge_agent(mock_openai_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"is_justified": false, "revised_score": 2, "correction_reason": "It is an internal ID."}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = JudgeAgent(client=mock_client, model="test-model")
    metadata = PropertyMetadata(
        node_label="User",
        property_name="userId",
        data_type="String",
        sample_values=["usr_123"],
        relationships=[]
    )
    
    res = agent.audit(metadata, 8, "Very important database key")
    assert res.is_justified is False
    assert res.revised_score == 2
    assert res.correction_reason == "It is an internal ID."

# 6. Test overall EvaluationPipeline orchestration
@patch("kg_node_filter.pipeline.get_node_labels")
@patch("kg_node_filter.pipeline.get_properties_for_label")
@patch("kg_node_filter.pipeline.get_property_metadata")
def test_pipeline_orchestration(mock_get_metadata, mock_get_props, mock_get_labels):
    # Mock Neo4j driver
    mock_driver = MagicMock()
    
    # Mock database schema fetches
    mock_get_labels.return_value = ["User"]
    mock_get_props.return_value = ["email", "age"]
    
    email_meta = PropertyMetadata(node_label="User", property_name="email", data_type="String", sample_values=["a@b.com"])
    age_meta = PropertyMetadata(node_label="User", property_name="age", data_type="Integer", sample_values=[25])
    mock_get_metadata.side_effect = [email_meta, age_meta]
    
    # Mock LLM Client
    mock_client = MagicMock()
    
    # Mock Analyzer responses:
    # 1. email: score 9, confidence 95% -> Obvious high, no research
    # 2. age: score 5, confidence 40% -> Gray area, low confidence -> Research and Judge
    mock_analyzer_email = MagicMock()
    mock_analyzer_email.choices = [
        MagicMock(message=MagicMock(content='{"importance_score": 9, "confidence_score": 95.0, "reasoning": "Essential"}'))
    ]
    mock_analyzer_age = MagicMock()
    mock_analyzer_age.choices = [
        MagicMock(message=MagicMock(content='{"importance_score": 5, "confidence_score": 40.0, "reasoning": "Maybe important"}'))
    ]
    
    # Mock Research response for age: returns score 6, reasoning "Actually secondary attribute"
    mock_research_age = MagicMock()
    mock_research_age.choices = [
        MagicMock(message=MagicMock(content='Thought: check database\nFinal Answer:\n{"importance_score": 6, "reasoning": "Actually secondary attribute"}'))
    ]
    
    # Mock Judge response:
    # age score is 6, which triggers Gray Area (3-6). Let's mock Judge saying justified=true.
    mock_judge_resp = MagicMock()
    mock_judge_resp.choices = [
        MagicMock(message=MagicMock(content='{"is_justified": true, "revised_score": null, "correction_reason": "Verified"}'))
    ]
    
    # Combine client side effects
    mock_client.chat.completions.create.side_effect = [
        mock_analyzer_email[0] if isinstance(mock_analyzer_email, list) else mock_analyzer_email, # email analyzer
        mock_analyzer_age[0] if isinstance(mock_analyzer_age, list) else mock_analyzer_age,       # age analyzer
        mock_research_age[0] if isinstance(mock_research_age, list) else mock_research_age,       # age research loop
        mock_judge_resp[0] if isinstance(mock_judge_resp, list) else mock_judge_resp             # age judge audit
    ]
    
    # Run pipeline. Set sanity check rate to 0.0 to prevent email from randomly triggering sanity check.
    pipeline = EvaluationPipeline(
        driver=mock_driver,
        confidence_threshold=75.0,
        judge_sanity_check_rate=0.0,
        llm_client=mock_client,
        model="test-model"
    )
    
    results = pipeline.run()
    
    # Verify final aggregation structure
    assert "User" in results
    assert "email" in results["User"]
    assert "age" in results["User"]
    
    # Check email details (no research, score 9)
    assert results["User"]["email"]["importance_score"] == 9
    assert results["User"]["email"]["rationale"] == "Essential"
    
    # Check age details (researched, score 6)
    assert results["User"]["age"]["importance_score"] == 6
    assert results["User"]["age"]["rationale"] == "Actually secondary attribute"
