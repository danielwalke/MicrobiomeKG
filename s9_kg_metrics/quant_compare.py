import os
import matplotlib.pyplot as plt
from neo4j import GraphDatabase

class GraphComparator:
    def __init__(self, uri_8083, uri_7693, user, password):
        self.driver_8083 = GraphDatabase.driver(uri_8083, auth=(user, password))
        self.driver_7693 = GraphDatabase.driver(uri_7693, auth=(user, password))

    def get_node_ids(self, session, query):
        res = session.run(query)
        return [record["id"] for record in res]

    def get_metrics(self, driver, db_label):
        print(f"\nGathering metrics for {db_label}...")
        metrics = {}
        batch_size = 1000

        with driver.session(fetch_size=1000) as session:
            q_nodes = """
            MATCH (n)
            WITH n, all(l IN labels(n) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/) AS is_concept
            RETURN coalesce(sum(CASE WHEN is_concept THEN 1 ELSE 0 END), 0) AS concept_nodes,
                   coalesce(sum(CASE WHEN NOT is_concept THEN 1 ELSE 0 END), 0) AS db_nodes
            """
            res = session.run(q_nodes).single()
            metrics['concept_nodes'] = res['concept_nodes']
            metrics['db_nodes'] = res['db_nodes']
            print(f"  - concept_nodes: {metrics['concept_nodes']}")
            print(f"  - db_nodes: {metrics['db_nodes']}")

            q_concept_ids = "MATCH (n) WHERE all(l IN labels(n) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/) RETURN elementId(n) AS id"
            concept_ids = self.get_node_ids(session, q_concept_ids)

            total_concept_degree = 0
            total_concept_props = 0
            concept_concept_edges = 0
            
            metrics['edge_distribution'] = {}
            metrics['degree_distributions'] = {}
            metrics['concept_degree_distributions'] = {}

            for i in range(0, len(concept_ids), batch_size):
                batch_ids = concept_ids[i:i + batch_size]
                
                q_deg_props = """
                MATCH (n) WHERE elementId(n) IN $batch_ids
                RETURN sum(COUNT { (n)--() }) AS total_deg, sum(size(keys(n))) AS total_props
                """
                res = session.run(q_deg_props, batch_ids=batch_ids).single()
                total_concept_degree += res['total_deg'] if res['total_deg'] is not None else 0
                total_concept_props += res['total_props'] if res['total_props'] is not None else 0

                q_cc_edges = """
                MATCH (n)-[r]-(m)
                WHERE elementId(n) IN $batch_ids AND all(l IN labels(m) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/)
                RETURN count(r) AS cc_edges
                """
                res = session.run(q_cc_edges, batch_ids=batch_ids).single()
                concept_concept_edges += res['cc_edges'] if res['cc_edges'] is not None else 0

                q_cdd = """
                MATCH (n) WHERE elementId(n) IN $batch_ids
                WITH coalesce(labels(n)[0], 'UNKNOWN') AS concept_type, COUNT { (n)--() } AS degree
                RETURN concept_type, degree, count(*) AS num_nodes
                """
                res_cdd = session.run(q_cdd, batch_ids=batch_ids)
                for record in res_cdd:
                    ctype = record['concept_type']
                    deg = record['degree']
                    cnt = record['num_nodes']
                    if ctype not in metrics['concept_degree_distributions']:
                        metrics['concept_degree_distributions'][ctype] = {}
                    if deg not in metrics['concept_degree_distributions'][ctype]:
                        metrics['concept_degree_distributions'][ctype][deg] = 0
                    metrics['concept_degree_distributions'][ctype][deg] += cnt

                q_ed = """
                MATCH (a)-[r]->(b)
                WHERE elementId(a) IN $batch_ids AND all(l IN labels(b) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/)
                WITH coalesce(labels(a)[0], 'UNKNOWN') AS source, type(r) AS rel, coalesce(labels(b)[0], 'UNKNOWN') AS target
                RETURN source + '-[' + rel + ']->' + target AS edge_type, count(*) AS count
                """
                res_ed = session.run(q_ed, batch_ids=batch_ids)
                for record in res_ed:
                    etype = record['edge_type']
                    metrics['edge_distribution'][etype] = metrics['edge_distribution'].get(etype, 0) + record['count']

                q_dd = """
                MATCH (a)-[r]->(b)
                WHERE elementId(a) IN $batch_ids AND all(l IN labels(b) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/)
                WITH coalesce(labels(a)[0], 'UNKNOWN') AS source, type(r) AS rel, coalesce(labels(b)[0], 'UNKNOWN') AS target, elementId(a) AS a_id
                WITH source + '-[' + rel + ']->' + target AS edge_type, a_id, count(*) AS degree
                RETURN edge_type, degree, count(a_id) AS num_nodes
                """
                res_dd = session.run(q_dd, batch_ids=batch_ids)
                for record in res_dd:
                    etype = record['edge_type']
                    deg = record['degree']
                    cnt = record['num_nodes']
                    if etype not in metrics['degree_distributions']:
                        metrics['degree_distributions'][etype] = {}
                    if deg not in metrics['degree_distributions'][etype]:
                        metrics['degree_distributions'][etype][deg] = 0
                    metrics['degree_distributions'][etype][deg] += cnt

            if len(concept_ids) > 0:
                metrics['avg_concept_degree'] = total_concept_degree / len(concept_ids)
                metrics['avg_props_concept'] = total_concept_props / len(concept_ids)
                metrics['concept_concept_edges'] = concept_concept_edges / 2
            else:
                metrics['avg_concept_degree'] = 0
                metrics['avg_props_concept'] = 0
                metrics['concept_concept_edges'] = 0

            print(f"  - avg_concept_degree: {metrics['avg_concept_degree']:.4f}")
            print(f"  - concept_concept_edges: {metrics['concept_concept_edges']}")
            print(f"  - avg_props_concept: {metrics['avg_props_concept']:.4f}")
            print(f"  - edge_distribution: {len(metrics['edge_distribution'])} concept-to-concept connections found")
            print(f"  - degree_distributions: extracted for {len(metrics['degree_distributions'])} concept-to-concept connection types")

            q_volume = """
            CALL {
                MATCH (n)
                RETURN count(n) AS nodes, sum(size(keys(n))) AS node_props
            }
            CALL {
                MATCH ()-[r]->()
                RETURN count(r) AS edges, sum(size(keys(r))) AS edge_props
            }
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
            WHERE all(l IN labels(a) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/)
            WITH a ORDER BY rand() LIMIT 20
            MATCH (a)-[*1..4]-(b)
            WHERE all(l IN labels(b) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/) AND elementId(a) < elementId(b)
            WITH DISTINCT a, b LIMIT 200
            MATCH p = shortestPath((a)-[*1..4]-(b))
            RETURN coalesce(avg(length(p)), 0) AS avg_path_length
            """
            res = session.run(q_path).single()
            metrics['avg_path_length'] = res['avg_path_length']
            print(f"  - avg_path_length: {metrics['avg_path_length']:.4f}")

        return metrics

    def compare_and_plot(self):
        metrics_8083 = self.get_metrics(self.driver_8083, "Port 8083")
        metrics_7693 = self.get_metrics(self.driver_7693, "Port 7693")

        print("\nGenerating plots...")
        output_dir = os.path.expanduser("~/git/MicrobiomeKG/config/s9_kg_metrics/figures")
        os.makedirs(output_dir, exist_ok=True)

        concept_deg_dists_8083 = metrics_8083.pop('concept_degree_distributions')
        concept_deg_dists_7693 = metrics_7693.pop('concept_degree_distributions')

        all_concept_types = set(concept_deg_dists_8083.keys()).union(set(concept_deg_dists_7693.keys()))
        for ctype in all_concept_types:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            d8 = concept_deg_dists_8083.get(ctype, {})
            x8 = sorted(d8.keys())
            y8 = [d8[k] for k in x8]

            d7 = concept_deg_dists_7693.get(ctype, {})
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

            ax2.set_title(f'Concept Node Degree Distribution: {ctype} - Port 7693 (Refined)')
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
        deg_dists_7693 = metrics_7693.pop('degree_distributions')

        all_edge_types = set(deg_dists_8083.keys()).union(set(deg_dists_7693.keys()))
        for etype in all_edge_types:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            d8 = deg_dists_8083.get(etype, {})
            x8 = sorted(d8.keys())
            y8 = [d8[k] for k in x8]

            d7 = deg_dists_7693.get(etype, {})
            x7 = sorted(d7.keys())
            y7 = [d7[k] for k in x7]

            ax1.set_title(f'Concept-to-Concept Edge Distribution: {etype} - Port 8083 (Original)')
            ax1.set_ylabel('Node Count (log)')
            if x8:
                ax1.bar(x8, y8, color='salmon', alpha=0.8)
                ax1.set_yscale('log')
                ax1.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax1.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax1.transAxes)

            ax2.set_title(f'Concept-to-Concept Edge Distribution: {etype} - Port 7693 (Refined)')
            ax2.set_ylabel('Node Count (log)')
            ax2.set_xlabel('Degree (Number of Outgoing Edges to Concepts)')
            if x7:
                ax2.bar(x7, y7, color='skyblue', alpha=0.8)
                ax2.set_yscale('log')
                ax2.grid(True, which="both", linestyle='--', alpha=0.5)
            else:
                ax2.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax2.transAxes)

            plt.tight_layout()
            safe_name = etype.replace('-[', '_').replace(']->', '_')
            deg_filepath = os.path.join(output_dir, f"concept_edge_deg_dist_{safe_name}.png")
            plt.savefig(deg_filepath, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved plot to {deg_filepath}")

        edge_dist_8083 = metrics_8083.pop('edge_distribution')
        edge_dist_7693 = metrics_7693.pop('edge_distribution')

        all_edges = set(edge_dist_8083.keys()).union(set(edge_dist_7693.keys()))
        all_edges = sorted(list(all_edges))

        counts_8083 = [edge_dist_8083.get(e, 0) for e in all_edges]
        counts_7693 = [edge_dist_7693.get(e, 0) for e in all_edges]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
        x_pos = range(len(all_edges))

        ax1.bar(x_pos, counts_8083, color='salmon')
        ax1.set_title('Concept-to-Concept Edge Types Distribution - Port 8083 (Original)')
        ax1.set_ylabel('Edge Count (log)')
        if any(counts_8083):
            ax1.set_yscale('log')
        ax1.grid(axis='y', linestyle='--', alpha=0.7)

        ax2.bar(x_pos, counts_7693, color='skyblue')
        ax2.set_title('Concept-to-Concept Edge Types Distribution - Port 7693 (Refined)')
        ax2.set_ylabel('Edge Count (log)')
        if any(counts_7693):
            ax2.set_yscale('log')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)

        plt.xticks(x_pos, all_edges, rotation=90)
        plt.tight_layout()

        edge_filepath = os.path.join(output_dir, "concept_edge_totals.png")
        plt.savefig(edge_filepath, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot to {edge_filepath}")

        keys = list(metrics_8083.keys())
        for key in keys:
            fig, ax = plt.subplots(figsize=(8, 5))
            values = [metrics_8083[key], metrics_7693[key]]
            labels = ['Port 8083 (Original)', 'Port 7693 (Refined)']
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
        self.driver_7693.close()

if __name__ == "__main__":
    comparator = GraphComparator("bolt://localhost:8083", "bolt://localhost:7693", "neo4j", "password")
    comparator.compare_and_plot()
    comparator.close()