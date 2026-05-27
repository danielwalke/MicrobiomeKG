import os

def direct_relationship_roll_up(t_session):
    t_session.run(
        f"""
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
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}
        )
        """
    ).consume()

def bridge_node_roll_up(t_session):
    ## I doubt the existence of this edge case but its better to keep rn
    t_session.run(
        f"""
        CALL apoc.periodic.iterate(
            "MATCH (c1)<-[:MAPPED_TO]-(dbN)-[:MAPPED_TO]->(c2)
             WHERE id(c1) < id(c2)
             RETURN c1, c2, labels(dbN) AS dbLabels, properties(dbN) AS dbProps",
            "CALL apoc.create.relationship(c1, 'SHARED_ENTITY', dbProps, c2) YIELD rel AS new_r
             SET new_r.source_labels = dbLabels",
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}   
        )
        """
    ).consume()

def edge_roll_up(t_session):
    query = f"""
    MATCH (n:UniProt_Protein)-[]-(r:UniProt_Reference)-[]-(c:UniProt_Citation)
    CALL {{
        WITH n, r, c
        CREATE (n)-[rel:HAS_REFERENCE]->(c)
        SET rel = properties(r)
    }} IN TRANSACTIONS OF {os.getenv("BATCH_SIZE")} ROWS
    """
    t_session.run(query).consume()

def indirect_relationship_roll_up(t_session):
    t_session.run(
        f"""
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
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}
        )
        """
    ).consume()

def propagate_edges(t_session):
    direct_relationship_roll_up(t_session)
    bridge_node_roll_up(t_session)
    edge_roll_up(t_session)
    indirect_relationship_roll_up(t_session)