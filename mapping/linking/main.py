from mapping.integrations.connector import Neo4jConnector
from mapping.linking.entity_linker import EntityLinker
from mapping.linking.references_edge import ReferencesPTMEdge
from mapping.linking.has_ontology_edge import HasOntologyEdge


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