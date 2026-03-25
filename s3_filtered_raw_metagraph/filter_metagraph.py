import json
from neo4j import GraphDatabase

def run_migration(source_driver, target_driver):
    with open("config/s3_filtered_raw_metagraph/interesting_properties.json", 'r') as f:
        allowed_props = json.load(f)

    with source_driver.session() as s_session, target_driver.session() as t_session:
        t_session.run("MATCH (n) DETACH DELETE n")
        nodes_result = s_session.run("MATCH (n) WHERE NOT 'Property' IN labels(n) RETURN n, elementId(n) AS eid")
        
        for record in nodes_result:
            node = record["n"]
            eid = record["eid"]
            labels = list(node.labels)
            props = dict(node)
            
            filtered_props = {}
            is_mapped = False
            allowed_keys = set()
            
            for lbl in labels:
                if lbl in allowed_props:
                    is_mapped = True
                    allowed_keys.update(list(allowed_props[lbl].keys()))
            
            if is_mapped:
                filtered_props = {k: v for k, v in props.items() if k in allowed_keys}
            else:
                filtered_props = props
            
            filtered_props["_migration_id"] = eid
            label_str = ":".join(labels)
            
            t_session.run(f"CREATE (n:{label_str}) SET n = $props", props=filtered_props)

        valid_props_query = """
        MATCH (labelNode)-[]-(p:Property)
        WHERE NOT 'Property' IN labels(labelNode)
        RETURN labelNode, p, elementId(p) AS eid
        """
        valid_props_result = s_session.run(valid_props_query)
        
        migrated_prop_ids = set()
        
        for record in valid_props_result:
            label_node = record["labelNode"]
            prop_node = record["p"]
            eid = record["eid"]
            
            if eid in migrated_prop_ids:
                continue
            
            l_labels = list(label_node.labels)
            p_key = prop_node.get("key")
            
            is_allowed = False
            for lbl in l_labels:
                if lbl in allowed_props and p_key in allowed_props[lbl]:
                    is_allowed = True
                    break
                    
            if is_allowed:
                migrated_prop_ids.add(eid)
                p_labels = ":".join(list(prop_node.labels))
                p_props = dict(prop_node)
                p_props["_migration_id"] = eid
                
                t_session.run(f"CREATE (p:{p_labels}) SET p = $props", props=p_props)

        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN elementId(a) AS a_eid, labels(a) AS a_labels, a.key AS a_key,
               elementId(b) AS b_eid, labels(b) AS b_labels, b.key AS b_key,
               type(r) AS rel_type, properties(r) AS rel_props
        """
        rels_result = s_session.run(rels_query)
        
        for record in rels_result:
            a_eid = record["a_eid"]
            b_eid = record["b_eid"]
            a_labels = record["a_labels"]
            b_labels = record["b_labels"]
            a_key = record["a_key"]
            b_key = record["b_key"]
            rel_type = record["rel_type"]
            rel_props = record["rel_props"]
            
            is_a_prop = "Property" in a_labels
            is_b_prop = "Property" in b_labels
            
            if is_b_prop and not is_a_prop:
                valid = False
                for lbl in a_labels:
                    if lbl in allowed_props and b_key in allowed_props[lbl]:
                        valid = True
                        break
                if not valid:
                    continue
                    
            elif is_a_prop and not is_b_prop:
                valid = False
                for lbl in b_labels:
                    if lbl in allowed_props and a_key in allowed_props[lbl]:
                        valid = True
                        break
                if not valid:
                    continue

            t_session.run(
                f"""
                MATCH (a {{ _migration_id: $a_eid }}), (b {{ _migration_id: $b_eid }})
                CREATE (a)-[r:`{rel_type}`]->(b)
                SET r = $rel_props
                """,
                a_eid=a_eid, b_eid=b_eid, rel_props=rel_props
            )

        t_session.run("MATCH (n) REMOVE n._migration_id")

    source_driver.close()
    target_driver.close()

if __name__ == "__main__":
    source_uri = 'bolt://localhost:7688'
    source_user = 'neo4j'
    source_pass = 'neo4j'
    target_uri = 'bolt://localhost:7689'
    target_user = 'neo4j'
    target_pass = ''

    source_driver = GraphDatabase.driver(source_uri, auth=(source_user, source_pass))
    target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_pass))
    run_migration(source_driver, target_driver)