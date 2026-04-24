
from neo4j import GraphDatabase
from mapping.integrations.integrator import NodeIntegrator
from mapping.integrations.publication import MergedPublication
from mapping.integrations.gene import MergedGene
from mapping.integrations.entity_resolver import EntityResolver
from mapping.integrations.connector import Neo4jConnector


connector = Neo4jConnector()

# 1. Resolve matching nodes purely using the Blueprint configuration
resolver = EntityResolver(connector)
for blue_print_class in [ MergedGene, MergedPublication]:  # Add more Blueprint classes as needed
    if blue_print_class.__label__ == "MergedGene" or blue_print_class.__label__ == "MergedPublication": continue
    resolver.process_graph(blueprint_class=blue_print_class)

    # 2. Run the Pydantic preprocessing and integrate them into Neo4j
    integrator = NodeIntegrator(connector)
    integrator.integrate(
        blueprint_class=blue_print_class, 
        universal_id_to_neo4j_ids=resolver.universal_id_to_neo4j_ids
    )
connector.close()