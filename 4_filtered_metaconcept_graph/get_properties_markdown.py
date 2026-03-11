import argparse
from neo4j import GraphDatabase

def extract_schema_with_samples():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suri',   default='bolt://localhost:8083')
    parser.add_argument('--suser',  default='neo4j')
    parser.add_argument('--spass',  default='neo4j')
    args = parser.parse_args()

    driver = GraphDatabase.driver(args.suri, auth=(args.suser, args.spass))
    
    markdown_output_label_map = {}
    unique_properties = set()

    with driver.session() as session:
        schema_info = session.run("CALL db.schema.nodeTypeProperties()").data()
        
        label_map = {}
        for row in schema_info:
            prop_name = row['propertyName']
            unique_properties.add(prop_name)
            
            for label in row['nodeLabels']:
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
    return markdown_output_label_map, sorted(list(unique_properties))



if __name__ == "__main__":
    schema_dict, all_props = extract_schema_with_samples()
    
    print("### Unique Properties In Database ###")
    print(", ".join(all_props))
    print("\n")
    
    for label, md in schema_dict.items():
        print(md)