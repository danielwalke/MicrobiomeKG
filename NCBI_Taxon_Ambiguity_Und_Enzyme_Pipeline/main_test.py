from src.s2_mapping.integrations.integrator import NodeIntegrator
from src.s2_mapping.integrations.entity_resolver import EntityResolver
from src.s2_mapping.integrations.connector import Neo4jConnector

from benjas_shit.enzyme import MergedEnzymeTest
from benjas_shit.term import MergedTerm


#delete the repeated nodes, just to avoid duplicates during testing 
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
    for blue_print_class in [ MergedEnzymeTest]:  # Add more Blueprint classes as needed
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