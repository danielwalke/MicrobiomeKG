# BioDWH2 Setup Log

## Actions taken

1. **Found desired databases list**: `InterPro`, `Gene Ontology (GO)`, `Expasy ENZYME`, `Mass Spectrometry Ontology` at `desired_dbs.csv`.
2. **Downloaded JAR files**:
   - `BioDWH2-v0.6.8.jar` downloaded from BioDWH2 releases. (https://github.com/BioDWH2/BioDWH2/releases)
   - `BioDWH2-Neo4j-Server-v1.3.2.jar` downloaded from BioDWH2-Neo4j-Server releases. (https://github.com/BioDWH2/BioDWH2-Neo4j-Server/releases)   
3. **Identified precise data source IDs** from the BioDWH2 documentation:
   - `InterPro` (InterPro)
   - `GeneOntology` (Gene Ontology (GO))
   - `ENZYME` (Expasy ENZYME)
   - `MassSpectrometryOntology` (Mass Spectrometry Ontology)
4. **Created workspace**: Running `java -jar BioDWH2-v0.6.8.jar -c /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace`
5. **Added data sources to workspace**:
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace InterPro`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace GeneOntology`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace ENZYME`
   - `java -jar BioDWH2-v0.6.8.jar --add-data-source /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace MassSpectrometryOntology`
6. **Updating workspace (generating graph)**: `java -jar BioDWH2-v0.6.8.jar -u /Users/danielwalke/git/microbiomeprocheck/knowledge_graph/raw_knowledge_graph/workspace`
