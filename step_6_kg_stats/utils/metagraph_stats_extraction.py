def infer_type_py(values):
    # Helper: guess type from Python values
    t = set()
    for v in values:
        if v is None:
            t.add("null")
        elif isinstance(v, bool):
            t.add("bool")
        elif isinstance(v, int):
            t.add("int")
        elif isinstance(v, float):
            t.add("float")
        elif isinstance(v, list):
            t.add("list")
        elif isinstance(v, dict):
            t.add("dict")
        else:
            t.add("str")
    return list(t)

def get_node_types_and_properties(tx):
    query = """
    MATCH (n)
    RETURN DISTINCT labels(n) AS label_set, keys(n) AS prop_names
    """
    result = tx.run(query)
    node_props = {}

    for record in result:
        label_tuple = tuple(sorted(record["label_set"]))
        props = record["prop_names"]
        if label_tuple not in node_props:
            node_props[label_tuple] = set()
        for p in props:
            node_props[label_tuple].add(p)

    node_types = []
    for label_tuple, props in node_props.items():
        label_clause = "".join(f":`{l}`" for l in label_tuple)

        # ✅ count for this exact label combination
        count_query = f"""
        MATCH (n{label_clause})
        RETURN count(n) AS c
        """
        c = tx.run(count_query).single()["c"]

        prop_defs = []
        for prop in props:
            sample_query = f"""
            MATCH (n{label_clause})
            WHERE n.`{prop}` IS NOT NULL
            RETURN n.`{prop}` AS value
            LIMIT 500
            """
            values = [rec["value"] for rec in tx.run(sample_query)]
            types = infer_type_py(values)
            prop_defs.append({"name": prop, "types": types})

        node_types.append({
            "labels": list(label_tuple),
            "labelString": "/".join(label_tuple),
            "count": c,                 # ✅ NEW
            "properties": prop_defs
        })

    return node_types


def get_edge_types_and_properties(tx):
    query = """
    MATCH (a)-[r]->(b)
    RETURN DISTINCT labels(a) AS source_labels,
                    type(r)   AS rel_type,
                    labels(b) AS target_labels,
                    keys(r)   AS prop_names
    """
    result = tx.run(query)
    edge_types_raw = {}

    for record in result:
        key = (
            tuple(sorted(record["source_labels"])),
            record["rel_type"],
            tuple(sorted(record["target_labels"]))
        )
        if key not in edge_types_raw:
            edge_types_raw[key] = set()
        for p in record["prop_names"]:
            edge_types_raw[key].add(p)

    edge_types = []
    for key, prop_names in edge_types_raw.items():
        src_labels, rel_type, tgt_labels = key
        label_clause_src = "".join(f":`{l}`" for l in src_labels)
        label_clause_tgt = "".join(f":`{l}`" for l in tgt_labels)

        # ✅ count for this exact (src labels, rel, tgt labels)
        count_query = f"""
        MATCH (a{label_clause_src})-[r:`{rel_type}`]->(b{label_clause_tgt})
        RETURN count(r) AS c
        """
        c = tx.run(count_query).single()["c"]

        prop_defs = []
        for prop in prop_names:
            sample_query = f"""
            MATCH (a{label_clause_src})-[r:`{rel_type}`]->(b{label_clause_tgt})
            WHERE r.`{prop}` IS NOT NULL
            RETURN r.`{prop}` AS value
            LIMIT 500
            """
            values = [rec["value"] for rec in tx.run(sample_query)]
            types = infer_type_py(values)
            prop_defs.append({"name": prop, "types": types})

        edge_types.append({
            "type": rel_type,
            "sources": [list(src_labels)],
            "targets": [list(tgt_labels)],
            "count": c,                 
            "properties": prop_defs
        })

    return edge_types