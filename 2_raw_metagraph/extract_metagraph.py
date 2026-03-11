import argparse
from neo4j import GraphDatabase


def run_migration():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suri',   default='bolt://localhost:8083')
    parser.add_argument('--suser',  default='neo4j')
    parser.add_argument('--spass',  default='neo4j')
    parser.add_argument('--turi',   default='bolt://localhost:7688')
    parser.add_argument('--tuser',  default='neo4j')
    parser.add_argument('--tpass',  default='')
    args = parser.parse_args()

    source_driver = GraphDatabase.driver(args.suri, auth=(args.suser, args.spass))
    target_driver = GraphDatabase.driver(args.turi, auth=(args.tuser, args.tpass))

    with source_driver.session() as session:
        node_props_raw = session.run("CALL db.schema.nodeTypeProperties()").data()
        rel_props_raw  = session.run("CALL db.schema.relTypeProperties()").data()
        viz            = session.run("CALL db.schema.visualization()").data()[0]

    node_props_map = {}
    for row in node_props_raw:
        key       = "|".join(sorted(row["nodeLabels"]))
        prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'Unknown'
        node_props_map.setdefault(key, {})[row['propertyName']] = prop_type

    rel_props_map = {}
    for row in rel_props_raw:
        rel_type  = row["relType"].strip(":`")
        prop_type = row['propertyTypes'][0] if row['propertyTypes'] else 'Unknown'
        rel_props_map.setdefault(rel_type, {})[row['propertyName']] = prop_type

    viz_node_names = {n["name"] for n in viz["nodes"]}

    edges_list = []
    for rel in viz["relationships"]:
        start, rel_type, end = rel[0]["name"], rel[1], rel[2]["name"]
        edges_list.append({"start": start, "end": end, "type": rel_type})

    property_usage: dict[str, dict] = {}
    for key, props in node_props_map.items():
        label = key.split("|")[0]
        for prop_key, prop_type in props.items():
            entry = property_usage.setdefault(prop_key, {"type": prop_type, "labels": set()})
            entry["labels"].add(label)

    with target_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        for key, props in node_props_map.items():
            label = key.split("|")[0]
            session.run(
                "MERGE (n:`" + label + "`) SET n += $props",
                props=props,
            )

        for name in viz_node_names:
            if name and name not in node_props_map:
                session.run("MERGE (n:`" + name + "`)")

        for edge in edges_list:
            if not edge["start"] or not edge["end"]:
                continue
            props    = rel_props_map.get(edge["type"], {})
            rel_type = edge["type"]
            session.run(
                "MATCH (s:`" + edge["start"] + "`) "
                "MATCH (t:`" + edge["end"]   + "`) "
                "MERGE (s)-[r:`" + rel_type + "`]->(t) "
                "SET r += $props",
                props=props,
            )

        for prop_key, info in property_usage.items():
            session.run(
                """
                MERGE (p:Property {key: $key})
                SET p.propertyType = $prop_type
                """,
                key=prop_key,
                prop_type=info["type"],
            )

            for label in info["labels"]:
                session.run(
                    "MATCH (n:`" + label + "`) "
                    "MATCH (p:Property {key: $key}) "
                    "MERGE (n)-[:HAS_PROPERTY]->(p)",
                    key=prop_key,
                )

    source_driver.close()
    target_driver.close()
    print("✅  Metagraph migration complete (incl. Property nodes).")


if __name__ == "__main__":
    run_migration()