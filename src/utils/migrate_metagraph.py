def migrate_metagraph(source_driver, target_driver):
    print("🔄  Starting metagraph migration...")
    with source_driver.session() as session:
        node_props_raw = session.run("CALL db.schema.nodeTypeProperties()").data()
        rel_props_raw  = session.run("CALL db.schema.relTypeProperties()").data()
        
        edges_raw = session.run("""
            MATCH (a)-[r]->(b)
            UNWIND labels(a) AS start_label
            UNWIND labels(b) AS end_label
            RETURN DISTINCT start_label, type(r) AS rel_type, end_label
        """).data()
    print(f"📊  Extracted {len(node_props_raw)} node properties, {len(rel_props_raw)} relationship properties, and {len(edges_raw)} edges from source metagraph.")
    node_props_map = {}
    for row in node_props_raw:
        for label in row["nodeLabels"]:
            if row["propertyName"] is None: continue
            prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'String'
            node_props_map.setdefault(label, {})[row['propertyName']] = prop_type
    print(f"📊  Processed node properties for {len(node_props_map)} labels.")
    rel_props_map = {}
    for row in rel_props_raw:
        if row["propertyName"] is None: continue
        rel_type  = row["relType"].strip(":`")
        prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'String'
        rel_props_map.setdefault(rel_type, {})[row['propertyName']] = prop_type
    print(f"📊  Processed relationship properties for {len(rel_props_map)} relationship types.")
    property_usage = {}
    for label, props in node_props_map.items():
        for prop_key, prop_type in props.items():
            entry = property_usage.setdefault(prop_key, {"type": prop_type, "labels": set()})
            entry["labels"].add(label)
    print(f"📊  Processed property usage for {len(property_usage)} properties.")

    with target_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("🧹  Cleared target metagraph.")
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
        print(f"✅  Migrated {len(node_props_map)} node labels and {len(edges_raw)} edges to target metagraph.")
        for prop_key, info in property_usage.items():
            for label in info["labels"]:
                session.run(
                    "MATCH (n:`" + label + "`) "
                    "MERGE (n)-[:HAS_PROPERTY]->(p:Property {key: $key}) "
                    "SET p.propertyType = $prop_type",
                    key=prop_key,
                    prop_type=info["type"],
                )
        print(f"✅  Migrated property usage for {len(property_usage)} properties to target metagraph.")

    source_driver.close()
    target_driver.close()
    print("✅  Metagraph migration complete.")