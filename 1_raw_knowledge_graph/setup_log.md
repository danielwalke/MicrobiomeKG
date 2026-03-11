# BioDWH2 Setup Log

## Actions taken

1. **Found desired databases list**: `InterPro`, `Gene Ontology (GO)`, `Expasy ENZYME`, `Mass Spectrometry Ontology` at `desired_dbs.csv`.
2. **Downloaded JAR files**:
   - `BioDWH2-v0.6.8.jar` downloaded from BioDWH2 releases. (curl -s https://api.github.com/repos/BioDWH2/BioDWH2/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO)
   - `BioDWH2-Neo4j-Server-v1.3.2.jar` downloaded from BioDWH2-Neo4j-Server releases. (curl -s https://api.github.com/repos/BioDWH2/BioDWH2-Neo4j-Server/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO)   
3. **Identified precise data source IDs** from the BioDWH2 documentation:
   - `InterPro` (InterPro)
   - `GeneOntology` (Gene Ontology (GO))
   - `ENZYME` (Expasy ENZYME)
   - `MassSpectrometryOntology` (Mass Spectrometry Ontology)
4. **Created workspace**: Running `java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace`
5. **Added data sources to workspace**:
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace InterPro`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace GeneOntology`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source /~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace ENZYME`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace MassSpectrometryOntology`
6. **Updating workspace (generating graph)**: `java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace`
7. **Creating neo4j database from workspace**: `java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace`
8. **Starting neo4j database from workspace**: `java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/git/MicrobiomeKG/1_raw_knowledge_graph/workspace`