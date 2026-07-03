from src.s2_mapping.integrations.connector import Neo4jConnector
from src.s2_mapping.linking.entity_linker import EntityLinker
from src.s2_mapping.linking.references_edge import ReferencesPTMEdge
from src.s2_mapping.linking.has_ontology_edge import HasOntologyEdge


def main():
    connector = Neo4jConnector()
    try:
        linker = EntityLinker(connector)
        
        # List out all the specific edge definitions you want to run
        edges_to_process = [
            ReferencesPTMEdge(),
            HasOntologyEdge(),
            # ProteinToGeneEdge(),
            # MetaboliteToPathwayEdge(),
        ]
        
        for edge in edges_to_process:
            print(f"\n--- Processing Edge: {edge.relationship_label} ---")
            linker.process_edge(edge)
            
    finally:
        connector.close()

if __name__ == "__main__":
    main()