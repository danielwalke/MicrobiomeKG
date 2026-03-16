import argparse
from neo4j import GraphDatabase

def filter_properties(m_session, t_session):
    query = """CALL db.schema.nodeTypeProperties()
                    YIELD nodeLabels, propertyName
                    UNWIND nodeLabels AS label
                    RETURN label, collect(DISTINCT propertyName) AS properties"""
    metagraph_label_props_results = m_session.run(query)
    metagraph_schema_dict = {record["label"]: record["properties"] for record in metagraph_label_props_results if record["label"]}

    target_label_props_results = t_session.run(query)
    target_schema_dict = {record["label"]: record["properties"] for record in target_label_props_results if record["label"]}


    for label in target_schema_dict:
        all_props = target_schema_dict[label]
        intresting_props = metagraph_schema_dict[label]
        irrelevant_props = remove_items(all_props, intresting_props)
        if not irrelevant_props:
            continue
            
        props_to_remove = ", ".join([f"n.{prop}" for prop in irrelevant_props])
        batch_query = f"""
        CALL apoc.periodic.iterate(
            "MATCH (n:{label}) RETURN n",
            "REMOVE {props_to_remove}",
            {{batchSize: 10000, parallel: false}}
        )
        """
        t_session.run(batch_query)
def indirect_relationship_roll_up(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (sAgg)<-[:MAPPED_TO]-(s)-[r]-(t)-[:MAPPED_TO]->(tAgg)
            WHERE id(sAgg) <> id(tAgg) AND id(s) <> id(sAgg) AND id(t) <> id(tAgg)
            RETURN
                CASE WHEN id(startNode(r)) = id(s) THEN id(sAgg) ELSE id(tAgg) END AS newStartId,
                CASE WHEN id(endNode(r)) = id(s) THEN id(sAgg) ELSE id(tAgg) END AS newEndId,
                type(r) AS rType,
                properties(r) AS rProps,
                labels(s) AS sLabels,
                labels(t) AS tLabels",
            "MATCH (startN) WHERE id(startN) = newStartId
            MATCH (endN) WHERE id(endN) = newEndId
            CALL apoc.create.relationship(startN, rType, rProps, endN) YIELD rel AS new_r
            SET new_r.source_labels = sLabels
            SET new_r.target_labels = tLabels",
            {batchSize: 100000, parallel: false}
        )
        """
    )

def property_roll_up(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (sAgg)<-[:MAPPED_TO]-(s)
            UNWIND keys(properties(s)) AS key
            WITH id(sAgg) AS sAggId, head(labels(s)) + '__' + key AS newKey, collect(s[key]) AS rawValues
            RETURN sAggId, newKey, apoc.coll.toSet(apoc.coll.flatten(rawValues)) AS propValues",
            "MATCH (sAgg) WHERE id(sAgg) = sAggId
            CALL apoc.create.setProperty(sAgg, newKey, propValues) YIELD node
            RETURN node",
            {batchSize: 100000, parallel: false}
        )
        """
    )

def direct_relationship_roll_up(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (sAgg)<-[:MAPPED_TO]-(s)-[r]-(t)
            WHERE id(sAgg) <> id(t) AND id(s) <> id(sAgg) AND type(r) <> 'MAPPED_TO' AND NOT (t)-[:MAPPED_TO]->()
            RETURN 
                CASE WHEN id(startNode(r)) = id(s) THEN id(sAgg) ELSE id(t) END AS newStartId,
                CASE WHEN id(endNode(r)) = id(s) THEN id(sAgg) ELSE id(t) END AS newEndId,
                type(r) AS rType,
                properties(r) AS rProps,
                labels(s) AS sLabels,
                labels(t) AS tLabels",
            "MATCH (startN) WHERE id(startN) = newStartId
            MATCH (endN) WHERE id(endN) = newEndId
            CALL apoc.create.relationship(startN, rType, rProps, endN) YIELD rel AS new_r
            SET new_r.source_labels = sLabels
            SET new_r.target_labels = tLabels",
            {batchSize: 100000, parallel: false}
        )
        """
    )

def bridge_node_roll_up(t_session):
    ## I doubt the existence of this edge case but its better to keep rn
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (c1)<-[:MAPPED_TO]-(dbN)-[:MAPPED_TO]->(c2)
             WHERE id(c1) < id(c2)
             RETURN c1, c2, labels(dbN) AS dbLabels, properties(dbN) AS dbProps",
            "CALL apoc.create.relationship(c1, 'SHARED_ENTITY', dbProps, c2) YIELD rel AS new_r
             SET new_r.source_labels = dbLabels",
            {batchSize: 100000, parallel: false}
        )
        """
    )

def delete_all_source_nodes_of_mapped_to(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (n)-[:MAPPED_TO]->()
             RETURN DISTINCT n",
            "DETACH DELETE n",
            {batchSize: 100000, parallel: false}
        )
        """
    )

## TODO apoc.coll.toSet(arrayProps)

def remove_items(main_list, items_to_remove):
    remove_set = set(items_to_remove)
    return [item for item in main_list if item not in remove_set]

def run_migration(args):
    metagraph_driver = GraphDatabase.driver(args.muri, auth=(args.muser, args.mpass))
    target_driver = GraphDatabase.driver(args.turi, auth=(args.tuser, args.tpass))

    with target_driver.session() as t_session, metagraph_driver.session() as m_session:
        filter_properties(m_session, t_session)
        property_roll_up(t_session)
        indirect_relationship_roll_up(t_session)
        direct_relationship_roll_up(t_session)
        bridge_node_roll_up(t_session)
        delete_all_source_nodes_of_mapped_to(t_session)

    target_driver.close()
    metagraph_driver.close()

if __name__ == "__main__":
    ## TODO: Bug: MAPPED_TO props sometimes not correctly rolled up? e.g. INTERPRO_DOMAIN -> PROTEIN_DOMAIN
    parser = argparse.ArgumentParser(description="Migrate and filter Neo4j graph")
    parser.add_argument("--muri", default="bolt://localhost:7690", help="Metagraph Bolt URI")
    parser.add_argument("--muser", default="neo4j", help="Metagraph username")
    parser.add_argument("--mpass", default="neo4j", help="Metagraph password")

    parser.add_argument("--turi", default="bolt://localhost:7691", help="Target Bolt URI")
    parser.add_argument("--tuser", default="neo4j", help="Target username")
    parser.add_argument("--tpass", default="", help="Target password")
    
    args = parser.parse_args()
    run_migration(args)