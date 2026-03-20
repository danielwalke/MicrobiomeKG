# Metagraph Setup Log

## 2026-03-10

0. **Requirements**: Need to provide .env with BASE_URL and API_KEY 
1.  **Initialized raw_metagraph directory**: Confirmed location at `/Users/danielwalke/git/microbiomeprocheck/step_4_filtered_metaconcept_graph`.
2.  **Created Docker Compose**: Defined `docker-compose.yml` for the target Neo4j instance (Port 7477 for HTTP, 7690 for Bolt).
3. **Property filtering**: Identifying intresting properties for each meta node (identify_relevant_properties.py) based on the node label, properties and example property values (get_properties_markdown.py):
`python -m step_4_filtered_metaconcept_graph.identify_relevant_properties`
4. **Filter concept metagraph based on properties**: `python -m step_4_filtered_metaconcept_graph.filter_metagraph`



 