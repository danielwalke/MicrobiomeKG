import os
import matplotlib.pyplot as plt
from neo4j import GraphDatabase

class GraphComparator:
    def __init__(self, uri_8083, uri_7691, user, password):
        self.driver_8083 = GraphDatabase.driver(uri_8083, auth=(user, password))
        self.driver_7691 = GraphDatabase.driver(uri_7691, auth=(user, password))

    def get_metrics(self, driver, db_label):
        print(f"\nGathering metrics for {db_label}...")
        metrics = {}
        with driver.session() as session:
            q_nodes = """
            MATCH (n)
            WITH n, all(l IN labels(n) WHERE l =~ '^[A-Z]+$') AS is_concept
            RETURN coalesce(sum(CASE WHEN is_concept THEN 1 ELSE 0 END), 0) AS concept_nodes,
                   coalesce(sum(CASE WHEN NOT is_concept THEN 1 ELSE 0 END), 0) AS db_nodes
            """
            res = session.run(q_nodes).single()
            metrics['concept_nodes'] = res['concept_nodes']
            metrics['db_nodes'] = res['db_nodes']
            print(f"  - concept_nodes: {metrics['concept_nodes']}")
            print(f"  - db_nodes: {metrics['db_nodes']}")

            q_degree = """
            MATCH (n)
            WHERE all(l IN labels(n) WHERE l =~ '^[A-Z]+$')
            OPTIONAL MATCH (n)-[r]-()
            RETURN coalesce(count(r) * 1.0 / count(DISTINCT n), 0) AS avg_concept_degree
            """
            res = session.run(q_degree).single()
            metrics['avg_concept_degree'] = res['avg_concept_degree']
            print(f"  - avg_concept_degree: {metrics['avg_concept_degree']:.4f}")

            q_cc_edges = """
            MATCH (n)-[r]-(m)
            WHERE all(l IN labels(n) WHERE l =~ '^[A-Z]+$') AND all(l IN labels(m) WHERE l =~ '^[A-Z]+$')
            RETURN coalesce(count(r) / 2, 0) AS concept_concept_edges
            """
            res = session.run(q_cc_edges).single()
            metrics['concept_concept_edges'] = res['concept_concept_edges']
            print(f"  - concept_concept_edges: {metrics['concept_concept_edges']}")

            q_props = """
            MATCH (n)
            WHERE all(l IN labels(n) WHERE l =~ '^[A-Z]+$')
            RETURN coalesce(avg(size(keys(n))), 0) AS avg_props
            """
            res = session.run(q_props).single()
            metrics['avg_props_concept'] = res['avg_props']
            print(f"  - avg_props_concept: {metrics['avg_props_concept']:.4f}")

            q_volume = """
            MATCH (n)
            WITH count(n) AS nodes, sum(size(keys(n))) AS node_props
            MATCH ()-[r]->()
            WITH nodes, node_props, count(r) AS edges, sum(size(keys(r))) AS edge_props
            RETURN coalesce(nodes + edges + node_props + edge_props, 0) AS total_volume
            """
            res = session.run(q_volume).single()
            metrics['total_volume'] = res['total_volume']
            print(f"  - total_volume: {metrics['total_volume']}")

            q_wcc = """
            CALL gds.wcc.stats({
                nodeProjection: '*',
                relationshipProjection: '*'
            }) YIELD componentCount
            RETURN componentCount
            """
            try:
                res = session.run(q_wcc).single()
                metrics['components'] = res['componentCount'] if res else 0
            except Exception:
                metrics['components'] = 0
            print(f"  - components: {metrics['components']}")

            q_path = """
            MATCH (a)
            WHERE all(l IN labels(a) WHERE l =~ '^[A-Z]+$')
            WITH a ORDER BY rand() LIMIT 20
            MATCH (a)-[*1..4]-(b)
            WHERE all(l IN labels(b) WHERE l =~ '^[A-Z]+$') AND elementId(a) < elementId(b)
            WITH DISTINCT a, b LIMIT 200
            MATCH p = shortestPath((a)-[*1..4]-(b))
            RETURN coalesce(avg(length(p)), 0) AS avg_path_length
            """
            res = session.run(q_path).single()
            metrics['avg_path_length'] = res['avg_path_length']
            print(f"  - avg_path_length: {metrics['avg_path_length']:.4f}")

            q_edge_dist = """
            MATCH (a)-[r]->(b)
            WITH coalesce(labels(a)[0], 'UNKNOWN') AS source, type(r) AS rel, coalesce(labels(b)[0], 'UNKNOWN') AS target
            RETURN source + '-[' + rel + ']->' + target AS edge_type, count(*) AS count
            """
            res = session.run(q_edge_dist)
            edge_dist = {}
            for record in res:
                edge_dist[record['edge_type']] = record['count']
            metrics['edge_distribution'] = edge_dist
            print(f"  - edge_distribution: {len(edge_dist)} connection types found")

            q_degree_dist = """
            MATCH (a)-[r]->(b)
            WITH coalesce(labels(a)[0], 'UNKNOWN') AS source, type(r) AS rel, coalesce(labels(b)[0], 'UNKNOWN') AS target, elementId(a) AS a_id
            WITH source + '-[' + rel + ']->' + target AS edge_type, a_id, count(*) AS degree
            WITH edge_type, degree, count(a_id) AS num_nodes
            RETURN edge_type, degree, num_nodes
            """
            res = session.run(q_degree_dist)
            degree_dists = {}
            for record in res:
                etype = record['edge_type']
                deg = record['degree']
                cnt = record['num_nodes']
                if etype not in degree_dists:
                    degree_dists[etype] = {}
                degree_dists[etype][deg] = cnt
            metrics['degree_distributions'] = degree_dists
            print(f"  - degree_distributions: extracted for {len(degree_dists)} connection types")

            q_concept_degree_dist = """
            MATCH (n)
            WHERE all(l IN labels(n) WHERE l =~ '^[A-Z]+$')
            WITH coalesce(labels(n)[0], 'UNKNOWN') AS concept_type, n
            OPTIONAL MATCH (n)-[r]-()
            WITH concept_type, elementId(n) AS n_id, count(r) AS degree
            WITH concept_type, degree, count(n_id) AS num_nodes
            RETURN concept_type, degree, num_nodes
            """
            res = session.run(q_concept_degree_dist)
            concept_degree_dists = {}
            for record in res:
                ctype = record['concept_type']
                deg = record['degree']
                cnt = record['num_nodes']
                if ctype not in concept_degree_dists:
                    concept_degree_dists[ctype] = {}
                concept_degree_dists[ctype][deg] = cnt
            metrics['concept_degree_distributions'] = concept_degree_dists
            print(f"  - concept_degree_distributions: extracted for {len(concept_degree_dists)} concept types")

        return metrics

    def compare_and_plot(self):
        metrics_8083 = self.get_metrics(self.driver_8083, "Port 8083")
        metrics_7691 = self.get_metrics(self.driver_7691, "Port 7691")

        print("\nGenerating plots...")
        output_dir = "kg_stats/figures"
        os.makedirs(output_dir, exist_ok=True)

        concept_deg_dists_8083 = metrics_8083.pop('concept_degree_distributions')
        concept_deg_dists_7691 = metrics_7691.pop('concept_degree_distributions')

        all_concept_types = set(concept_deg_dists_8083.keys()).union(set(concept_deg_dists_7691.keys()))
        for ctype in all_concept_types:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            d8 = concept_deg_dists_8083.get(ctype, {})
            x8 = sorted(d8.keys())
            y8 = [d8[k] for k in x8]

            d7 = concept_deg_dists_7691.get(ctype, {})
            x7 = sorted(d7.keys())
            y7 = [d7[k] for k in x7]

            ax1.set_title(f'Concept Node Degree Distribution: {ctype} - Port 8083 (Original)')
            ax1.set_ylabel('Node Count (log)')
            if x8:
                ax1.bar(x8, y8, color='salmon', alpha=0.8)
                ax1.set_yscale('log')
                ax1.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax1.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax1.transAxes)

            ax2.set_title(f'Concept Node Degree Distribution: {ctype} - Port 7691 (Refined)')
            ax2.set_ylabel('Node Count (log)')
            ax2.set_xlabel('Degree (Total Connections)')
            if x7:
                ax2.bar(x7, y7, color='skyblue', alpha=0.8)
                ax2.set_yscale('log')
                ax2.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax2.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax2.transAxes)

            plt.tight_layout()
            safe_name = ctype.replace(' ', '_')
            cdeg_filepath = os.path.join(output_dir, f"concept_deg_dist_{safe_name}.png")
            plt.savefig(cdeg_filepath, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved plot to {cdeg_filepath}")

        deg_dists_8083 = metrics_8083.pop('degree_distributions')
        deg_dists_7691 = metrics_7691.pop('degree_distributions')

        all_edge_types = set(deg_dists_8083.keys()).union(set(deg_dists_7691.keys()))
        for etype in all_edge_types:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            d8 = deg_dists_8083.get(etype, {})
            x8 = sorted(d8.keys())
            y8 = [d8[k] for k in x8]

            d7 = deg_dists_7691.get(etype, {})
            x7 = sorted(d7.keys())
            y7 = [d7[k] for k in x7]

            ax1.set_title(f'Edge Degree Distribution: {etype} - Port 8083 (Original)')
            ax1.set_ylabel('Node Count (log)')
            if x8:
                ax1.bar(x8, y8, color='salmon', alpha=0.8)
                ax1.set_yscale('log')
                ax1.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax1.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax1.transAxes)

            ax2.set_title(f'Edge Degree Distribution: {etype} - Port 7691 (Refined)')
            ax2.set_ylabel('Node Count (log)')
            ax2.set_xlabel('Degree (Number of Outgoing Edges)')
            if x7:
                ax2.bar(x7, y7, color='skyblue', alpha=0.8)
                ax2.set_yscale('log')
                ax2.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax2.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax2.transAxes)

            plt.tight_layout()
            safe_name = etype.replace('-[', '_').replace(']->', '_')
            deg_filepath = os.path.join(output_dir, f"edge_deg_dist_{safe_name}.png")
            plt.savefig(deg_filepath, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved plot to {deg_filepath}")

        edge_dist_8083 = metrics_8083.pop('edge_distribution')
        edge_dist_7691 = metrics_7691.pop('edge_distribution')

        all_edges = set(edge_dist_8083.keys()).union(set(edge_dist_7691.keys()))
        all_edges = sorted(list(all_edges))

        counts_8083 = [edge_dist_8083.get(e, 0) for e in all_edges]
        counts_7691 = [edge_dist_7691.get(e, 0) for e in all_edges]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
        x_pos = range(len(all_edges))

        ax1.bar(x_pos, counts_8083, color='salmon')
        ax1.set_title('Total Edge Types Distribution - Port 8083 (Original)')
        ax1.set_ylabel('Edge Count (log)')
        if any(counts_8083):
            ax1.set_yscale('log')
        ax1.grid(axis='y', linestyle='--', alpha=0.7)

        ax2.bar(x_pos, counts_7691, color='skyblue')
        ax2.set_title('Total Edge Types Distribution - Port 7691 (Refined)')
        ax2.set_ylabel('Edge Count (log)')
        if any(counts_7691):
            ax2.set_yscale('log')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)

        plt.xticks(x_pos, all_edges, rotation=90)
        plt.tight_layout()

        edge_filepath = os.path.join(output_dir, "edge_totals.png")
        plt.savefig(edge_filepath, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot to {edge_filepath}")

        keys = list(metrics_8083.keys())
        for key in keys:
            fig, ax = plt.subplots(figsize=(8, 5))
            values = [metrics_8083[key], metrics_7691[key]]
            labels = ['Port 8083 (Original)', 'Port 7691 (Refined)']
            colors = ['salmon', 'skyblue']

            bars = ax.bar(labels, values, color=colors)
            ax.set_title(f"Comparison: {key}")
            ax.set_ylabel("Value")

            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:.2f}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom')

            filepath = os.path.join(output_dir, f"{key}.png")
            plt.savefig(filepath, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved plot to {filepath}")

    def close(self):
        self.driver_8083.close()
        self.driver_7691.close()

if __name__ == "__main__":
    comparator = GraphComparator("bolt://localhost:8083", "bolt://localhost:7691", "neo4j", "password")
    comparator.compare_and_plot()
    comparator.close()