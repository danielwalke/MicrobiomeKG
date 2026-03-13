import json
import subprocess
import datetime
import questionary
import sys
import os

def generate_config(selected_sources):
    config = {
        "version": 1,
        "creationDateTime": datetime.datetime.now().isoformat(),
        "dataSourceIds": selected_sources,
        "outputFormatIds": ["GRAPHML"],
        "skipMetaGraphGeneration": False,
        "globalProperties": {
            "speciesFilter": [9606]
        },
        "dataSourceProperties": {}
    }
    
    for source in selected_sources:
        config["dataSourceProperties"][source] = {"forceExport": True}
        
    with open("~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace/config.json", "w") as f:
        json.dump(config, f, indent=2)

def main():
    ## Config
    print("Fetching and installing requirements")
    subprocess.run(
    """curl -s https://api.github.com/repos/BioDWH2/BioDWH2/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO""",
    shell=True,
    check=True
)

    subprocess.run(
        """curl -s https://api.github.com/repos/BioDWH2/BioDWH2-Neo4j-Server/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO""",
        shell=True,
        check=True
    )
    
    data_sources = [
        "ADReCS", "BasicFormalOntology", "BRENDA", "CanadianNutrientFile",
        "CancerDrugsDB", "ClinicalTrials.gov", "CMAUP", "DGIdb",
        "DiseaseOntology", "DISEASES", "DrugBank", "DrugCentral",
        "EFO", "EMA", "ENZYME", "GenCC", "Gene2Phenotype",
        "GeneOntology", "GuideToPharmacology", "GWASCatalog", "HERB",
        "HGNC", "HPO", "HPRD", "IntAct", "InterPro", "ITIS",
        "KEGG", "MED-RT", "miRBase", "miRDB", "miRTarBase",
        "Mondo", "NCBI", "NDF-RT", "Negatome", "OMIM",
        "OpenTargets", "PathwayCommons", "PharmGKB", "PROSITE", "ReDO-DB",
        "ReDOTrialsDB", "RefSeq", "RNADisease", "RNAInter", "RNALocate",
        "SequenceOntology", "SIDER", "STITCH", "STRING", "T3DB",
        "TarBase", "TISSUES", "TRRUST", "TTD", "UNII",
        "UniProt", "USDA-PLANTS"
    ]

    selected_sources = questionary.checkbox(
        "Select data sources for the Knowledge Graph:",
        choices=data_sources
    ).ask()

    if not selected_sources:
        print("No data sources selected. Exiting.")
        return
    ## Step 1
    print("\n--- Creating workspace ---")
    subprocess.run(['java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace'], shell=True,
        check=True)
    
    print("\n--- Changing config based on user input ---")
    generate_config(selected_sources)
    print("\n--- Updating workspace ---")
    subprocess.run(['java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace'], shell=True,
        check=True)
    print("\n--- Creating raw neo4j database workspace ---")
    subprocess.run(['java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace'], shell=True,
        check=True)
    print("\n--- Starting raw neo4j database workspace ---")
    subprocess.run(['java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace'], shell=True,
        check=True)
    print("\nRaw Knowledge Graph Link: http://localhost:7474/browser. Pick port bolt://localhost:8083 without any username or password.")

    ## Step 2
    print("\n--- Executing Metagraph Creation Script ---")
    subprocess.run(["docker compose -f ~/git/MicrobiomeKG/2_raw_metagraph/docker-compose.yml up -d "],shell=True, check=True)
    subprocess.run(["python -m 2_raw_metagraph.extract_metagraph --suri bolt://localhost:8083 --suser neo4j --spass neo4j --turi bolt://localhost:7688 --tuser neo4j --tpass "],shell=True, check=True)
    print("\n You can access the metagraph here: http://localhost:7475. Pick port bolt://localhost:7688 without any username or password.")


    ## Step 3
    print("\n--- Executing Metaconceptgraph Creation Script ---")
    subprocess.run(["docker compose -f ~/git/MicrobiomeKG/3_metaconcept_graph/docker-compose.yml up -d "], shell=True, check=True)
    subprocess.run(["python -m 3_metaconcept_graph.extract_concepts --suri bolt://localhost:7688 --suser neo4j --spass neo4j --turi bolt://localhost:7689 --tuser neo4j --tpass "],shell=True,
        check=True)
    print("\n You can access the metaconceptgraph here: http://localhost:7476. Pick port bolt://localhost:7689 without any username or password.")


    ## Step 4
    ## TODO topic selection
    print("\n--- Identifying relevant properties from the metagraph based on your topics ---")
    subprocess.run(["python -m 4_filtered_metaconcept_graph.identify_relevant_properties.py"], shell=True, check=True)
    print("\n--- Filtering Metaconceptgraph based on selected intresting properties ---")
    subprocess.run(["docker compose -f ~/git/MicrobiomeKG/4_filtered_metaconcept_graph/docker-compose.yml up -d"], shell=True, check=True)
    subprocess.run(["python -m 4_filtered_metaconcept_graph.filter_metagraph"], shell=True, check=True)
    print("\n You can access the filtered metaconceptgraph here: http://localhost:7477. Pick port bolt://localhost:7690 without any username or password.")

    ## Step 5
    print("\n--- Refining the raw graph based on your metagraph ---")
    subprocess.run(["docker compose -f ~/git/MicrobiomeKG/5_filtered_knowledge_graph/docker-compose.yml up -d"], shell=True, check=True)
    subprocess.run(["python -m 5_filtered_knowledge_graph.filter_knowledge_graph"], shell=True, check=True)
    print("\n You can access the filtered refined knowledge graph here: http://localhost:7478. Pick port bolt://localhost:7691 without any username or password.")
if __name__ == "__main__":
    main()