import os
import json
import argparse
from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv

from .pipeline import EvaluationPipeline

def main():
    # Load env variables from .env file if it exists
    load_dotenv(find_dotenv())
    
    parser = argparse.ArgumentParser(description="6-Step Escalation & Evaluation Pipeline for Neo4j KG Properties")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
    parser.add_argument("--user", default=os.getenv("NEO4J_USERNAME", "neo4j"), help="Neo4j username")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", ""), help="Neo4j password")
    parser.add_argument("--output", default="kg_node_filter_output.json", help="Path to export the final validated data")
    parser.add_argument("--sanity-rate", type=float, default=0.10, help="Sanity check selection rate (0.0 to 1.0)")
    
    args = parser.parse_args()
    
    # Check OpenAI compatible variables
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    model_name = os.getenv("MODEL_NAME", "qwen3.5-397b-a17b")
    
    print("=" * 60)
    print(" 6-Step Escalation & Evaluation Pipeline ")
    print("=" * 60)
    print(f"Neo4j Connection details:")
    print(f"  URI: {args.uri}")
    print(f"  User: {args.user}")
    print(f"LLM Endpoint Configuration:")
    print(f"  Model: {model_name}")
    print(f"  Base URL: {base_url or 'OpenAI Default'}")
    print(f"  API Key: {'configured' if api_key else 'NOT set'}")
    print("=" * 60)
    
    if not api_key:
        print("[Warning] API_KEY environment variable is not set. LLM calls will fail unless your endpoint does not require one.")
        
    print("Connecting to Neo4j database...")
    try:
        driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
        driver.verify_connectivity()
        print("Connected successfully to Neo4j.")
    except Exception as e:
        print(f"\n[Error] Could not connect to Neo4j: {e}")
        print("Please check your database status and credentials in your .env file or command arguments.")
        return
        
    try:
        pipeline = EvaluationPipeline(
            driver=driver,
            judge_sanity_check_rate=args.sanity_rate
        )
        
        print("\nStarting pipeline evaluation...\n")
        results = pipeline.run()
        
        # Save output deterministically
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        print("\n" + "=" * 60)
        print(f"[Success] Evaluation complete. Output saved to '{args.output}'")
        print("=" * 60)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as run_err:
        print(f"\n[Error] Pipeline execution failed: {run_err}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
