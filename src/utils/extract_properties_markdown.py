import argparse
from neo4j import GraphDatabase

def extract_schema_with_samples_md(port = 8083, user = "neo4j", password = "neo4j", only_concept_nodes = False, properties_list = None):
    user = user
    password = password
    port = port

    driver = GraphDatabase.driver(f"bolt://localhost:{port}", auth=(user, password))
    
    markdown_output_label_map = {}

    with driver.session() as session:
        schema_info = session.run("CALL db.schema.nodeTypeProperties()").data()
        
        label_map = {}
        for row in schema_info:
            prop_name = row['propertyName']
            
            for label in row['nodeLabels']:
                is_concept_node = label.isupper() 
                if only_concept_nodes and not is_concept_node:
                    continue

                label_map.setdefault(label, []).append({
                    "property": prop_name,
                    "type": row['propertyTypes'][0] if row['propertyTypes'] else "Unknown"
                })

        for label, props in label_map.items():
            markdown_rows = [
                f"## Label: `{label}`",
                "| Property Key | Type | Sample Values (Max 5) |",
                "| --- | --- | --- |"
            ]
            
            for p in props:
                if properties_list is not None and p['property'] not in properties_list: continue
                prop_name = p['property']
                prop_type = p['type']
                
                query = f"MATCH (n:`{label}`) WHERE n.`{prop_name}` IS NOT NULL RETURN n.`{prop_name}` AS val LIMIT 5"
                
                try:
                    records = session.run(query).data()
                    samples = []
                    for r in records:
                        val = r["val"]
                        if isinstance(val, list):
                            samples.append(f"{str(val[:5])[:-1]}, ...]" if len(val) > 5 else str(val))
                        else:
                            samples.append(str(val))
                    
                    sample_str = ", ".join(samples) if samples else "*No values*"
                except Exception as e:
                    sample_str = f"*Error: {str(e)}*"
                
                markdown_rows.append(f"| `{prop_name}` | {prop_type} | {sample_str} |")
            
            markdown_output_label_map[label] = "\n".join(markdown_rows)

    driver.close()
    return markdown_output_label_map



if __name__ == "__main__":
    schema_dict = extract_schema_with_samples_md()
    
    print("\n")
    i = 0
    
    for label, md in schema_dict.items():
        if "disease" in label.lower():
            print(md)
        # if i == 4:
        #     break
        # i = i+1