
from neo4j import GraphDatabase

def filter_properties(m_session, t_session):
    query = """CALL db.schema.nodeTypeProperties()
                    YIELD nodeLabels, propertyName
                    UNWIND nodeLabels AS label
                    RETURN label, collect(DISTINCT propertyName) AS properties
            """

    metagraph_label_props_results = m_session.run(query)
    metagraph_schema_dict = {record["label"]: record["properties"] for record in metagraph_label_props_results if record["label"]}
    target_label_props_results = t_session.run(query)
    target_schema_dict = {record["label"]: record["properties"] for record in target_label_props_results if record["label"]}


    for label in target_schema_dict:
        if label not in metagraph_schema_dict:
            print(f"Label {label} not found in metagraph schema, skipping property filtering for this label (Not in metagraph means no properties in complete graph and therefore irrelevant).")
            continue
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
            {{batchSize: 1000, parallel: false}}
        )
        """
        t_session.run(batch_query).consume()

def edge_roll_up(t_session):
    query = """
    MATCH (n:UniProt_Protein)-[]-(r:UniProt_Reference)-[]-(c:UniProt_Citation)
    apoc.create.relationship(n, 'HAS_REFERENCE', properties(r), c) YIELD rel
    """
    
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
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

def property_roll_up(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (sAgg)
             WHERE ()-[:MAPPED_TO]->(sAgg)
             RETURN id(sAgg) AS sAggId",
            "MATCH (sAgg) WHERE id(sAgg) = sAggId
             MATCH (sAgg)<-[:MAPPED_TO]-(s)
             UNWIND keys(properties(s)) AS key
             WITH sAgg, head(labels(s)) + '__' + key AS newKey, collect(s[key]) AS rawValues
             CALL apoc.create.setProperty(sAgg, newKey, apoc.coll.toSet(apoc.coll.flatten(rawValues))) YIELD node
             RETURN node",
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (sAgg)
             WHERE ()-[:ENZYME_HAS_XREF]->(sAgg)
             RETURN id(sAgg) AS sAggId",
            "MATCH (sAgg) WHERE id(sAgg) = sAggId
             MATCH (sAgg)<-[:ENZYME_HAS_XREF]-(s)
             UNWIND keys(properties(s)) AS key
             WITH sAgg, key AS newKey, collect(s[key]) AS rawValues
             CALL apoc.create.setProperty(sAgg, newKey, apoc.coll.toSet(apoc.coll.flatten(rawValues))) YIELD node
             RETURN node",
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

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
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

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
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

def delete_all_source_nodes_of_MAPPED_TO(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH (n)-[:MAPPED_TO]->()
             RETURN DISTINCT n",
            "DETACH DELETE n",
            {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

## TODO apoc.coll.toSet(arrayProps)

def remove_items(main_list, items_to_remove):
    remove_set = set(items_to_remove)
    return [item for item in main_list if item not in remove_set]

def run_migration(metagraph_driver, target_driver):
    with target_driver.session() as t_session, metagraph_driver.session() as m_session:
        filter_properties(m_session, t_session)
        ##TODO Test this:
        edge_roll_up(t_session)
        property_roll_up(t_session)
        indirect_relationship_roll_up(t_session)
        direct_relationship_roll_up(t_session)
        bridge_node_roll_up(t_session)
        delete_all_source_nodes_of_MAPPED_TO(t_session)

    target_driver.close()
    metagraph_driver.close()

if __name__ == "__main__":
    metagraph_uri = 'bolt://localhost:7689'
    metagraph_user = 'neo4j'
    metagraph_pass = 'neo4j'
    target_uri = 'bolt://localhost:7690'
    target_user = 'neo4j'
    target_pass = ''
    metagraph_driver = GraphDatabase.driver(metagraph_uri, auth=(metagraph_user, metagraph_pass))
    target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_pass))
    
    run_migration(metagraph_driver, target_driver)