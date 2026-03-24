from utils.Neo4jDbConnection import Neo4jDbConnection

def run_migration(source_driver, target_driver):
    with source_driver.session() as session:
        node_props_raw = session.run("CALL db.schema.nodeTypeProperties()").data()
        rel_props_raw  = session.run("CALL db.schema.relTypeProperties()").data()
        
        edges_raw = session.run("""
            MATCH (a)-[r]->(b)
            UNWIND labels(a) AS start_label
            UNWIND labels(b) AS end_label
            RETURN DISTINCT start_label, type(r) AS rel_type, end_label
        """).data()

    node_props_map = {}
    for row in node_props_raw:
        for label in row["nodeLabels"]:
            prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'String'
            node_props_map.setdefault(label, {})[row['propertyName']] = prop_type

    rel_props_map = {}
    for row in rel_props_raw:
        rel_type  = row["relType"].strip(":`")
        prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'String'
        rel_props_map.setdefault(rel_type, {})[row['propertyName']] = prop_type

    property_usage = {}
    for label, props in node_props_map.items():
        for prop_key, prop_type in props.items():
            entry = property_usage.setdefault(prop_key, {"type": prop_type, "labels": set()})
            entry["labels"].add(label)

    with target_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        for label, props in node_props_map.items():
            session.run(
                "MERGE (n:`" + label + "`) SET n += $props",
                props=props,
            )

        for edge in edges_raw:
            start_label = edge["start_label"]
            end_label = edge["end_label"]
            rel_type = edge["rel_type"]
            
            if not start_label or not end_label or not rel_type:
                continue
                
            props = rel_props_map.get(rel_type, {})
            
            session.run(
                "MERGE (s:`" + start_label + "`) "
                "MERGE (t:`" + end_label + "`) "
                "MERGE (s)-[r:`" + rel_type + "`]->(t) "
                "SET r += $props",
                props=props,
            )

        for prop_key, info in property_usage.items():
            for label in info["labels"]:
                session.run(
                    "MATCH (n:`" + label + "`) "
                    "MERGE (n)-[:HAS_PROPERTY]->(p:Property {key: $key}) "
                    "SET p.propertyType = $prop_type",
                    key=prop_key,
                    prop_type=info["type"],
                )

    source_driver.close()
    target_driver.close()
    print("✅  Metagraph migration complete.")

def main():
    source_uri = 'bolt://localhost:8083'
    source_user = 'neo4j'
    source_pass = 'neo4j'
    target_uri = 'bolt://localhost:7688'
    target_user = 'neo4j'
    target_pass = ''
    source_driver = Neo4jDbConnection(source_uri, source_user, source_pass).get_driver()
    target_driver = Neo4jDbConnection(target_uri, target_user, target_pass).get_driver()
    run_migration(source_driver, target_driver)

if __name__ == "__main__":
    main()