from mapping.integrations.integrator import NodeIntegrator
from mapping.integrations.protein_domain import MergedProteinDomain
from mapping.integrations.entity_resolver import EntityResolver
from mapping.integrations.connector import Neo4jConnector
from mapping.integrations.term import MergedTerm
from mapping.integrations.disease import MergedDisease
from mapping.integrations.tissue import MergedTissue
from mapping.integrations.ptm import MergedPTM


def delete_label_in_batches(session, label, batch_size):
    query = f"""
    MATCH (n:{label})
    CALL {{
        WITH n
        DETACH DELETE n
    }} IN TRANSACTIONS OF {batch_size} ROWS
    """
    session.run(query)
connector = Neo4jConnector()

# 1. Resolve matching nodes purely using the Blueprint configuration
##TODO change merged back to all uppercase letter filter and MAERGEND INTO TO MAPPED_TO
for blue_print_class in [ MergedProteinDomain, MergedTerm, MergedDisease, MergedTissue, MergedPTM]:  # Add more Blueprint classes as needed
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

## TODO: New connections within data -> missing Mapping connections or linkings in the data? Need to check the properties and their values