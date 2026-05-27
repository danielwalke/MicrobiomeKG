import os


def delete_db_nodes(t_session):
    t_session.run(
        f"""
        CALL apoc.periodic.iterate(
            "MATCH (n)
            WHERE all(l IN labels(n) WHERE l <> toUpper(l)) 
             RETURN DISTINCT n",
            "DETACH DELETE n",
            {{batchSize: {os.getenv("BATCH_SIZE")}, parallel: false}}
        )
        """
    ).consume()