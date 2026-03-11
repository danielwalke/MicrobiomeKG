import os
import shutil
import sys

def clone_biodwh2_neo4j(source_data_dir, target_project_dir):
    if os.geteuid() != 0:
        print("Run with sudo")
        sys.exit(1)

    os.makedirs(target_project_dir, exist_ok=True)
    target_data_dir = os.path.join(target_project_dir, 'data')

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)

    shutil.copytree(source_data_dir, target_data_dir)

    os.chown(target_data_dir, 7474, 7474)
    for root, dirs, files in os.walk(target_data_dir):
        for d in dirs:
            os.chown(os.path.join(root, d), 7474, 7474)
        for f in files:
            os.chown(os.path.join(root, f), 7474, 7474)

if __name__ == "__main__":
    clone_biodwh2_neo4j(sys.argv[1], sys.argv[2])