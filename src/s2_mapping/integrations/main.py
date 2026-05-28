from src.s2_mapping.integrations.integrator import NodeIntegrator
from src.s2_mapping.integrations.protein_domain import MergedProteinDomain
from src.s2_mapping.integrations.entity_resolver import EntityResolver
from src.s2_mapping.integrations.connector import Neo4jConnector
from src.s2_mapping.integrations.term import MergedTerm
from src.s2_mapping.integrations.disease import MergedDisease
from src.s2_mapping.integrations.tissue import MergedTissue
from src.s2_mapping.integrations.ptm import MergedPTM
from src.s2_mapping.integrations.kegg_merged import MergedModule, MergedReaction, MergedPathway, MergedEnzyme

def delete_label_in_batches(session, label, batch_size):
    query = f"""
    MATCH (n:{label})
    CALL {{
        WITH n
        DETACH DELETE n
    }} IN TRANSACTIONS OF {batch_size} ROWS
    """
    session.run(query)

def run_integrations():
    connector = Neo4jConnector()

    # 1. Resolve matching nodes purely using the Blueprint configuration
    ##TODO change merged back to all uppercase letter filter and MAERGEND INTO TO MAPPED_TO
    for blue_print_class in [ MergedProteinDomain, MergedTerm, MergedDisease, MergedTissue, MergedPTM, MergedModule, MergedReaction, MergedPathway, MergedEnzyme]:  # Add more Blueprint classes as needed
        with connector.driver.session() as session:
            delete_label_in_batches(session, blue_print_class.__label__, 10000)

        resolver = EntityResolver(connector)
        resolver.process_graph(blueprint_class=blue_print_class)

        # 2. Run the Pydantic preprocessing and integrate them into Neo4j
        integrator = NodeIntegrator(connector)
        integrator.integrate(
            blueprint_class=blue_print_class, 
            universal_id_to_neo4j_ids=resolver.universal_id_to_neo4j_ids
        )
    connector.close()

if __name__ == "__main__":
    run_integrations()