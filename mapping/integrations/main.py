
from neo4j import GraphDatabase
from mapping.integrations.integrator import NodeIntegrator
from mapping.integrations.publication import MergedPublication
from mapping.integrations.gene import MergedGene
from mapping.integrations.rna import MergedRna
from mapping.integrations.protein_domain import MergedProteinDomain
from mapping.integrations.entity_resolver import EntityResolver
from mapping.integrations.connector import Neo4jConnector
from mapping.integrations.protein import MergedProtein
from mapping.integrations.taxon import MergedTaxon
from mapping.integrations.term import MergedTerm
from mapping.integrations.disease import MergedDisease
from mapping.integrations.tissue import MergedTissue
from mapping.integrations.ptm import MergedPTM

connector = Neo4jConnector()

# 1. Resolve matching nodes purely using the Blueprint configuration

with connector.driver.session() as session:
    created_merged_labels = session.run("MATCH (n) WHERE labels(n)[0] CONTAINS 'Merged' RETURN apoc.coll.flatten(COLLECT(DISTINCT labels(n))) as mergedLabels").single()["mergedLabels"] 

for blue_print_class in [ MergedProtein, MergedGene, MergedPublication, MergedProteinDomain, MergedRna, MergedTaxon, MergedTerm, MergedDisease, MergedTissue, MergedPTM]:  # Add more Blueprint classes as needed
    resolver = EntityResolver(connector)
    if blue_print_class.__label__ in created_merged_labels: continue
    resolver.process_graph(blueprint_class=blue_print_class)

    # 2. Run the Pydantic preprocessing and integrate them into Neo4j
    integrator = NodeIntegrator(connector)
    integrator.integrate(
        blueprint_class=blue_print_class, 
        universal_id_to_neo4j_ids=resolver.universal_id_to_neo4j_ids
    )
connector.close()

## TODO: Disease and tissue looks weird (some property toll up did not work properly) + pubmed ids connection to HPRD_PTM to Publication -> We need a link specific entity resolver one that creates a link not a new node based on a shared entity