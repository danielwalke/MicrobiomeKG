import json

# ----------- STATISTICS FUNCTIONS -----------
def get_node_counts_multilabel(driver):
    """
    Counts nodes by their *complete label combination* (as a tuple/list).
    Example: [{'type': ['Protein'], 'count': 500}, {'type': ['Protein', 'Enzyme'], 'count': 50}]
    """
    with driver.session() as session:
        query = """
        MATCH (n)
        WITH labels(n) AS labels
        RETURN labels, count(*) AS count
        ORDER BY count DESC
        """
        results = []
        for rec in session.run(query):
            results.append({"type": rec["labels"], "count": rec["count"]})
    return results

def get_node_counts_aggregated(driver):
    """
    Counts nodes using the same aggregation as the Sankey aggregation.
    Each node is mapped to a "primary" label (single or synthetic).
    Returns: [{'type': [aggregated_label], 'count': ...}, ...]
    """
    # Collect aggregation rules, same as in get_sankey_links_aggregated
    with driver.session() as session:
        label_to_ids = {}
        node_labels = []
        result = session.run("MATCH (n) RETURN labels(n) AS labels")
        for rec in result:
            labels = rec["labels"]
            node_labels.append(labels)
            for l in labels:
                label_to_ids.setdefault(l, set()).add(tuple(labels))
        single_primaries = set()
        for labels in node_labels:
            if len(labels) == 1:
                single_primaries.add(labels[0])
        synthetic_primaries = set()
        for l, combos in label_to_ids.items():
            if all(len(combo) > 1 for combo in combos):
                synthetic_primaries.add(l)

        # Now map each node to its aggregated label, then count
        agg_counts = {}
        result = session.run("MATCH (n) RETURN labels(n) AS labels")
        for rec in result:
            labels = rec["labels"]
            # Aggregation logic (as in sankey)
            agg = None
            for l in labels:
                if l in single_primaries:
                    agg = l
                    break
            if agg is None:
                for l in labels:
                    if l in synthetic_primaries:
                        agg = l
                        break
            if agg is None and labels:
                agg = labels[0]
            # Count
            key = (agg,) if agg else tuple(labels)
            agg_counts[key] = agg_counts.get(key, 0) + 1
        # Convert to desired format
        return [{"type": list(key), "count": count} for key, count in agg_counts.items()]
        
def get_out_degree_distribution(driver):
    query = """
    MATCH (n)
    WITH size([(n)-->() | 1]) AS out_degree
    RETURN out_degree AS degree, count(*) AS count
    ORDER BY degree
    """
    with driver.session() as session:
        records = session.run(query)
        return [{"degree": r["degree"], "count": r["count"]} for r in records]


def get_in_degree_distribution(driver):
    query = """
    MATCH (n)
    WITH size([()-->(n) | 1]) AS in_degree
    RETURN in_degree AS degree, count(*) AS count
    ORDER BY degree
    """
    with driver.session() as session:
        records = session.run(query)
        return [{"degree": r["degree"], "count": r["count"]} for r in records]


def get_relationship_counts(driver):
    with driver.session() as session:
        rels = session.run("CALL db.relationshipTypes() YIELD relationshipType AS relType RETURN relType")
        results = []
        for rec in rels:
            rel_type = rec["relType"]
            count = session.run(f"MATCH ()-[:`{rel_type}`]->() RETURN count(*) AS count").single()["count"]
            results.append({"type": rel_type, "count": count})
    return results

def get_out_degree_distribution_by_label(driver):
    results = []
    with driver.session() as session:
        query = """
        MATCH (n)
        WITH labels(n) AS lbls, size([(n)-->() | 1]) AS out_degree
        RETURN lbls AS labels, out_degree AS degree, count(*) AS count
        ORDER BY labels, degree
        """
        combo_dict = {}
        for r in session.run(query):
            key = tuple(r["labels"])
            if key not in combo_dict:
                combo_dict[key] = []
            combo_dict[key].append({"degree": r["degree"], "count": r["count"]})
        for labels, degs in combo_dict.items():
            results.append({"labels": list(labels), "degrees": degs})
    return results


def get_in_degree_distribution_by_label(driver):
    """
    For each label, computes in-degree distribution (direct only).
    Returns: list of {label: str, degrees: [{degree: int, count: int}, ...]}
    """
    results = []
    with driver.session() as session:
        labels = [rec["label"] for rec in session.run("CALL db.labels() YIELD label RETURN label")]
        for label in labels:
            q = f"""
            MATCH (n:`{label}`)
            WITH size([()-->(n) | 1]) AS in_degree
            RETURN in_degree AS degree, count(*) AS count
            ORDER BY degree
            """
            degs = [{"degree": r["degree"], "count": r["count"]} for r in session.run(q)]
            results.append({"label": label, "degrees": degs})
    return results
    
def get_out_degree_distribution_by_label(driver):
    results = []
    with driver.session() as session:
        labels = [rec["label"] for rec in session.run("CALL db.labels() YIELD label RETURN label")]
        for label in labels:
            q = f"""
            MATCH (n:`{label}`)
            WITH size([(n)-->() | 1]) AS out_degree
            RETURN out_degree AS degree, count(*) AS count
            ORDER BY degree
            """
            degs = [{"degree": r["degree"], "count": r["count"]} for r in session.run(q)]
            results.append({"label": label, "degrees": degs})
    return results

def get_out_degree_distribution_by_label_combo(driver):
    results = []
    with driver.session() as session:
        query = """
        MATCH (n)
        WITH labels(n) AS lbls, size([(n)-->() | 1]) AS out_degree
        RETURN lbls AS labels, out_degree AS degree, count(*) AS count
        ORDER BY labels, degree
        """
        combo_dict = {}
        for r in session.run(query):
            key = tuple(r["labels"])
            if key not in combo_dict:
                combo_dict[key] = []
            combo_dict[key].append({"degree": r["degree"], "count": r["count"]})
        for labels, degs in combo_dict.items():
            results.append({"labels": list(labels), "degrees": degs})
    return results

def get_in_degree_distribution_by_label_combo(driver):
    """
    For each multi-label combo, computes in-degree distribution.
    Returns: list of {"labels": [...], "degrees": [{"degree": int, "count": int}, ...]}
    """
    results = []
    with driver.session() as session:
        query = """
        MATCH (n)
        WITH labels(n) AS lbls, size([()-->(n) | 1]) AS in_degree
        RETURN lbls AS labels, in_degree AS degree, count(*) AS count
        ORDER BY labels, degree
        """
        combo_dict = {}
        for r in session.run(query):
            key = tuple(r["labels"])
            if key not in combo_dict:
                combo_dict[key] = []
            combo_dict[key].append({"degree": r["degree"], "count": r["count"]})
        for labels, degs in combo_dict.items():
            results.append({"labels": list(labels), "degrees": degs})
    return results

def get_sankey_links_unaggregated(driver):
    """
    Returns: List of {
        "source": [label, ...],       # labels of source node
        "target": [label, ...],       # labels of target node
        "relationship": str,          # edge type
        "value": int                  # edge count
    }
    """
    results = []
    with driver.session() as session:
        query = """
        MATCH (a)-[r]->(b)
        WITH labels(a) AS src_labels, type(r) AS rel_type, labels(b) AS tgt_labels, count(*) AS value
        RETURN src_labels, rel_type, tgt_labels, value
        ORDER BY value DESC
        """
        for rec in session.run(query):
            results.append({
                "source": rec["src_labels"],
                "relationship": rec["rel_type"],
                "target": rec["tgt_labels"],
                "value": rec["value"]
            })
    return results


def aggregate_label(labels, single_primaries, synthetic_primaries):
    # Try to map to a real single-label
    for l in labels:
        if l in single_primaries:
            return [l]
    # Else, map to a synthetic primary (first one in list)
    for l in labels:
        if l in synthetic_primaries:
            return [l]
    # Fallback: keep all
    return labels

def get_sankey_links_aggregated(driver):
    """
    Aggregates multi-label nodes using same rules as the frontend's buildAutoIdMap().
    """
    # --- First, collect label stats for aggregation logic ---
    with driver.session() as session:
        # Build label to node mapping
        label_to_ids = {}
        node_labels = []
        result = session.run("MATCH (n) RETURN labels(n) AS labels")
        for rec in result:
            labels = rec["labels"]
            node_labels.append(labels)
            for l in labels:
                label_to_ids.setdefault(l, set()).add(tuple(labels))

        # Find single-primaries (labels that occur alone)
        single_primaries = set()
        for labels in node_labels:
            if len(labels) == 1:
                single_primaries.add(labels[0])
        # Synthetic primaries: labels never occurring alone
        synthetic_primaries = set()
        for l, combos in label_to_ids.items():
            if all(len(combo) > 1 for combo in combos):
                synthetic_primaries.add(l)

        # --- Now fetch all edges with labels and aggregate ---
        results = []
        edge_query = """
        MATCH (a)-[r]->(b)
        RETURN labels(a) AS src_labels, type(r) AS rel_type, labels(b) AS tgt_labels, count(*) AS value
        """
        for rec in session.run(edge_query):
            src_labels = aggregate_label(rec["src_labels"], single_primaries, synthetic_primaries)
            tgt_labels = aggregate_label(rec["tgt_labels"], single_primaries, synthetic_primaries)
            results.append({
                "source": src_labels,
                "relationship": rec["rel_type"],
                "target": tgt_labels,
                "value": rec["value"]
            })
    return results

def get_total_degree_distribution(driver):
    query = """
    MATCH (n)
    WITH size([(n)-->() | 1]) + size([()-->(n) | 1]) AS total_degree
    RETURN total_degree AS degree, count(*) AS count
    ORDER BY degree
    """
    with driver.session() as session:
        records = session.run(query)
        return [{"degree": r["degree"], "count": r["count"]} for r in records]

def get_total_degree_distribution_by_label(driver):
    results = []
    with driver.session() as session:
        labels = [rec["label"] for rec in session.run("CALL db.labels() YIELD label RETURN label")]
        for label in labels:
            q = f"""
            MATCH (n:`{label}`)
            WITH size([(n)-->() | 1]) + size([()-->(n) | 1]) AS total_degree
            RETURN total_degree AS degree, count(*) AS count
            ORDER BY degree
            """
            degs = [{"degree": r["degree"], "count": r["count"]} for r in session.run(q)]
            results.append({"label": label, "degrees": degs})
    return results

def get_total_degree_distribution_by_label_combo(driver):
    """
    For each multi-label combo, computes total degree (in + out) distribution.
    Returns: list of {"labels": [...], "degrees": [{"degree": int, "count": int}, ...]}
    """
    results = []
    with driver.session() as session:
        query = """
        MATCH (n)
        WITH labels(n) AS lbls,
             size([(n)-->() | 1]) + size([()-->(n) | 1]) AS total_degree
        RETURN lbls AS labels, total_degree AS degree, count(*) AS count
        ORDER BY labels, degree
        """
        combo_dict = {}
        for r in session.run(query):
            key = tuple(r["labels"])
            if key not in combo_dict:
                combo_dict[key] = []
            combo_dict[key].append({"degree": r["degree"], "count": r["count"]})
        for labels, degs in combo_dict.items():
            results.append({"labels": list(labels), "degrees": degs})
    return results

def get_zero_degree_node_stats(driver):
    with driver.session() as session:
        # Count of zero degree nodes
        zero_query = "MATCH (n) WHERE NOT (n)--() RETURN count(*) AS zero_degree_nodes"
        zero_count = session.run(zero_query).single()["zero_degree_nodes"]
        # Total nodes
        total_query = "MATCH (n) RETURN count(*) AS total_nodes"
        total_count = session.run(total_query).single()["total_nodes"]
        percent = (zero_count / total_count * 100) if total_count > 0 else 0
        return {
            "zero_degree_nodes": zero_count,
            "total_nodes": total_count,
            "percent": percent
        }

# ----------- JSON WRITER -----------

def save_kg_stats_json(
    kg_id,
    kg_name,
    stats_dict,
    out_path="kg_stats.json"
):
    stats = []
    for stat_id, stat in stats_dict.items():
        data = stat["data"]
        stat_entry = {
            "stat_id": stat_id,
            "data": data
        }
        stats.append(stat_entry)

    out = {
                "kg_id": kg_id,
                "kg_name": kg_name,
                "stats": stats
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote statistics to {out_path}")

