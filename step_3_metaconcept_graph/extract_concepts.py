import argparse
from neo4j import GraphDatabase


def is_all_upper(label: str) -> bool:
    return label == label.upper() and any(c.isalpha() for c in label)


def get_extra_labels(label: str) -> list[str]:
    if is_all_upper(label):
        return ["Concept"]
    if "_" in label:
        return [part for part in label.split("_") if part]
    return []


def fetch_all_nodes(session):
    result = session.run("MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props")
    return [{"id": r["id"], "labels": r["labels"], "props": dict(r["props"])} for r in result]


def fetch_all_relationships(session):
    result = session.run(
        "MATCH (a)-[r]->(b) "
        "RETURN id(a) AS src_id, id(b) AS tgt_id, type(r) AS rtype, properties(r) AS props"
    )
    return [{"src_id": r["src_id"], "tgt_id": r["tgt_id"], "rtype": r["rtype"], "props": dict(r["props"])} for r in result]


def migrate(source_driver, target_driver):
    print("Reading source graph …")
    with source_driver.session() as s_sess:
        nodes = fetch_all_nodes(s_sess)
        rels  = fetch_all_relationships(s_sess)

    print(f"  {len(nodes)} nodes, {len(rels)} relationships found.")

    with target_driver.session() as t_sess:

        print("Creating nodes in target …")
        for node in nodes:
            base_labels = node["labels"]
            extra: set[str] = set()

            for lbl in base_labels:
                for el in get_extra_labels(lbl):
                    extra.add(el)

            all_labels = list(dict.fromkeys(base_labels + list(extra)))

            label_str = ":".join(f"`{l}`" for l in all_labels)

            props = dict(node["props"])
            props["__src_id__"] = node["id"]

            t_sess.run(
                f"CREATE (n:{label_str}) SET n = $props",
                props=props,
            )

        print("Creating relationships in target …")
        for rel in rels:
            t_sess.run(
                f"""
                MATCH (a {{__src_id__: $src_id}})
                MATCH (b {{__src_id__: $tgt_id}})
                CREATE (a)-[r:`{rel['rtype']}`]->(b)
                SET r = $props
                """,
                src_id=rel["src_id"],
                tgt_id=rel["tgt_id"],
                props=rel["props"],
            )

        print("Cleaning up temporary __src_id__ property …")
        t_sess.run("MATCH (n) REMOVE n.__src_id__")

    print("Migration complete ✓")


def run_migration():
    parser = argparse.ArgumentParser(description="Migrate a Neo4j graph and enrich node labels.")
    parser.add_argument("--suri",   default="bolt://localhost:7688", help="Source Bolt URI")
    parser.add_argument("--suser",  default="neo4j",                 help="Source username")
    parser.add_argument("--spass",  default="neo4j",                 help="Source password")
    parser.add_argument("--turi",   default="bolt://localhost:7689", help="Target Bolt URI")
    parser.add_argument("--tuser",  default="neo4j",                 help="Target username")
    parser.add_argument("--tpass",  default="",                      help="Target password")
    args = parser.parse_args()

    source_driver = GraphDatabase.driver(args.suri,  auth=(args.suser, args.spass))
    target_driver = GraphDatabase.driver(args.turi,  auth=(args.tuser, args.tpass))

    try:
        migrate(source_driver, target_driver)
    finally:
        source_driver.close()
        target_driver.close()


if __name__ == "__main__":
    run_migration()