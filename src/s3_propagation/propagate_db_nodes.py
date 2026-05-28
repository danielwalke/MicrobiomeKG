
import os

def property_roll_up(t_session):
    t_session.run(
        f"""
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
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}
        )
        """
    ).consume()
    t_session.run(
        f"""
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
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}
        )
        """
    ).consume()

def propagate_db_nodes(t_session):
    property_roll_up(t_session)
