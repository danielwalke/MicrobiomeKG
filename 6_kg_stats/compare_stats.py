import json
import pandas as pd
import matplotlib.pyplot as plt
import sys

def load_node_counts(filepath, file_id):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    node_counts = []
    for stat in data['stats']:
        if stat['stat_id'] == 'node_count_per_type':
            for item in stat['data']:
                node_type = item['type'][0] if isinstance(item['type'], list) else item['type']
                node_counts.append({'Type': node_type, file_id: item['count']})
    
    return pd.DataFrame(node_counts)

def main(file1, file2):
    df1 = load_node_counts(file1, 'File 1')
    df2 = load_node_counts(file2, 'File 2')
    
    df = pd.merge(df1, df2, on='Type', how='outer').fillna(0)
    df = df.sort_values(by=['File 1', 'File 2'], ascending=False).head(20)
    
    df.set_index('Type').plot(kind='bar', figsize=(14, 7), width=0.8)
    
    plt.title('Top 20 Node Types Comparison')
    plt.ylabel('Count')
    plt.xlabel('Node Type')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('node_comparison.png')

if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python script.py <file1.json> <file2.json>")