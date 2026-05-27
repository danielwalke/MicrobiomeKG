import re
from typing import List, Dict, Any, Set
from neo4j import Driver
from .schema import PropertyMetadata

def sanitize_identifier(name: str) -> str:
    """
    Sanitize identifier names (labels, properties) to prevent injection,
    by escaping backticks.
    """
    return name.replace("`", "``")

def get_node_labels(driver: Driver) -> List[str]:
    """
    Retrieves all unique node labels from the Neo4j database.
    """
    query = "CALL db.labels() YIELD label RETURN label"
    try:
        with driver.session() as session:
            result = session.run(query)
            return [record["label"] for record in result]
    except Exception as e:
        # Fallback if db.labels() is not available/supported
        fallback_query = "MATCH (n) RETURN DISTINCT labels(n) AS labels"
        try:
            with driver.session() as session:
                result = session.run(fallback_query)
                labels = set()
                for r in result:
                    for label in r["labels"]:
                        labels.add(label)
                return list(labels)
        except Exception as fallback_err:
            print(f"Error fetching node labels: {e} | Fallback error: {fallback_err}")
            return []

def get_properties_for_label(driver: Driver, label: str) -> List[str]:
    """
    Retrieves all property keys present on nodes with the given label.
    """
    safe_label = sanitize_identifier(label)
    query = f"""
    MATCH (n:`{safe_label}`)
    WITH keys(n) AS keys
    UNWIND keys AS key
    RETURN DISTINCT key
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            return [record["key"] for record in result]
    except Exception as e:
        print(f"Error fetching properties for label {label}: {e}")
        return []

def get_property_samples(driver: Driver, label: str, property_name: str, limit: int = 5) -> List[Any]:
    """
    Retrieves sample values for a specific property under a node label.
    """
    safe_label = sanitize_identifier(label)
    safe_prop = sanitize_identifier(property_name)
    query = f"""
    MATCH (n:`{safe_label}`)
    WHERE n.`{safe_prop}` IS NOT NULL
    RETURN n.`{safe_prop}` AS val
    LIMIT {limit}
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            return [record["val"] for record in result]
    except Exception as e:
        print(f"Error fetching samples for property {label}.{property_name}: {e}")
        return []

def get_local_connections(driver: Driver, label: str) -> List[str]:
    """
    Retrieves the local schema connections (outgoing and incoming relationships)
    for a given node label.
    """
    safe_label = sanitize_identifier(label)
    connections = []
    
    # Outgoing relationships
    outgoing_query = f"""
    MATCH (n:`{safe_label}`)-[r]->(m)
    WITH type(r) AS rel_type, labels(m) AS target_labels
    UNWIND target_labels AS target_label
    RETURN DISTINCT rel_type, target_label
    LIMIT 30
    """
    try:
        with driver.session() as session:
            res = session.run(outgoing_query)
            for record in res:
                connections.append(f"(:`{label}`)-[:`{record['rel_type']}`]->(:`{record['target_label']}`)")
    except Exception as e:
        print(f"Error fetching outgoing relationships for {label}: {e}")

    # Incoming relationships
    incoming_query = f"""
    MATCH (n:`{safe_label}`)<-[r]-(m)
    WITH type(r) AS rel_type, labels(m) AS source_labels
    UNWIND source_labels AS source_label
    RETURN DISTINCT rel_type, source_label
    LIMIT 30
    """
    try:
        with driver.session() as session:
            res = session.run(incoming_query)
            for record in res:
                connections.append(f"(:`{record['source_label']}`)-[:`{record['rel_type']}`]->(:`{label}`)")
    except Exception as e:
        print(f"Error fetching incoming relationships for {label}: {e}")

    return connections

def get_property_metadata(driver: Driver, label: str, property_name: str) -> PropertyMetadata:
    """
    Gathers schema metadata, sample values, and data type for a property.
    """
    samples = get_property_samples(driver, label, property_name, limit=5)
    
    # Infer type from sample values
    data_type = "Unknown"
    if samples:
        # Simple inference of the first non-None value type
        val = samples[0]
        if isinstance(val, bool):
            data_type = "Boolean"
        elif isinstance(val, int):
            data_type = "Integer"
        elif isinstance(val, float):
            data_type = "Float"
        elif isinstance(val, str):
            data_type = "String"
        elif isinstance(val, list):
            data_type = "List"
        elif isinstance(val, dict):
            data_type = "Map"
        else:
            data_type = type(val).__name__

    relationships = get_local_connections(driver, label)
    
    return PropertyMetadata(
        node_label=label,
        property_name=property_name,
        data_type=data_type,
        sample_values=samples,
        relationships=relationships
    )

def execute_cypher_query(driver: Driver, query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Executes a Cypher query (read-only) and returns the results as a list of dicts.
    Used by the Research Agent as a tool.
    """
    # Quick regex block of mutating queries for safety
    mutating_keywords = ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DETACH", "DROP"]
    normalized_query = query.upper()
    for kw in mutating_keywords:
        # Match keyword as whole word to avoid sub-word false positives
        if re.search(r'\b' + kw + r'\b', normalized_query):
            raise ValueError(f"Mutation operation '{kw}' is not allowed in this read-only query tool.")
            
    try:
        with driver.session() as session:
            # execute_read ensures read transactions
            def _work(tx):
                res = tx.run(query)
                records = []
                for record in res:
                    records.append(dict(record))
                    if len(records) >= limit:
                        break
                return records
            return session.execute_read(_work)
    except Exception as e:
        return [{"error": str(e)}]
