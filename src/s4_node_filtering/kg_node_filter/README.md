# 6-Step Escalation & Evaluation Pipeline

A robust, multi-agent evaluation pipeline to analyze, filter, and score the importance of properties in a Neo4j Knowledge Graph. The pipeline uses an OpenAI-compatible LLM endpoint to evaluate properties through sequential stages.

## Features

1. **The Fast Path (Deterministic)**: Toolless Analyzer Agent evaluates node properties using metadata and schema relationships.
2. **Confidence Threshold**: Analyzer assigns an importance score (0-10) and a confidence score (0-100%).
3. **Escalation**: Low confidence evaluations (< 75%) are automatically escalated to a Research Agent.
4. **Research Agent (ReAct Loop)**: Equips the agent with Web Search (via DuckDuckGo) and Database Query tools to run Cypher queries and look up industry terminology online.
5. **Targeted Judge**: Borderline scores (3-6) and a random sample (10%) of obvious scores are routed to a strict QA Judge Agent for verdict validation.
6. **Deterministic JSON Storage**: Final aggregated results are exported to a structured JSON file organized by node label.

---

## Installation

1. Make sure you are in the project root directory.
2. Set up the virtual environment (completed):
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install openai pydantic python-dotenv neo4j duckduckgo-search pytest pytest-mock
   ```

---

## Configuration (`.env`)

Before running the pipeline, create a `.env` file in the root directory. It should define the following environment variables:

```ini
# OpenAI-compatible LLM Configuration
API_KEY=your_llm_api_key
BASE_URL=https://api.your-provider.com/v1
MODEL_NAME=qwen3.5-397b-a17b

# Neo4j Database Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

---

## Running the Pipeline

To run the property evaluation pipeline:

```bash
# Using the root wrapper script:
.venv/bin/python run.py --output results.json

# Or run the module directly:
PYTHONPATH=. .venv/bin/python -m kg_node_filter.main --output results.json
```

### CLI Arguments

- `--uri`: Neo4j instance URI (default: read from `NEO4J_URI` or `bolt://bolt://localhost:7687`)
- `--user`: Username (default: read from `NEO4J_USERNAME` or `neo4j`)
- `--password`: Password (default: read from `NEO4J_PASSWORD` or `""`)
- `--output`: Filepath to export the final JSON (default: `kg_node_filter_output.json`)
- `--sanity-rate`: Rate of sanity check selection for obvious scores (default: `0.10` / 10%)

---

## Running Tests

To execute the test suite (all mocks included; no internet or active database connection required):

```bash
PYTHONPATH=. .venv/bin/pytest tests/
```
