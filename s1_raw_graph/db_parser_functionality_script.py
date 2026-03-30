import json
import os
import subprocess
import shutil

available_dbs_file_path = os.path.expanduser('~/git/MicrobiomeKG/config/s0_access/availableDatabases.json')
dbs_with_errors_json = os.path.expanduser('~/git/MicrobiomeKG/config/s0_access/dbs_with_errors.json')
dbs_without_errors_json = os.path.expanduser('~/git/MicrobiomeKG/config/s0_access/dbs_without_errors.json')

dbs_with_errors = dict()
dbs_without_errors = []
if os.path.exists(dbs_with_errors_json):
    print(f"Warning: The file {dbs_with_errors_json} already exists. Please review the contents before proceeding.")
    with open(dbs_with_errors_json, 'r') as f:
        dbs_with_errors = json.load(f)
    input("Press Enter to continue...")
if os.path.exists(dbs_without_errors_json):
    print(f"Warning: The file {dbs_without_errors_json} already exists. Please review the contents before proceeding.")
    with open(dbs_without_errors_json, 'r') as f:
        dbs_without_errors = json.load(f)
    input("Press Enter to continue...")

def open_available_dbs_file():
    with open(available_dbs_file_path, 'r') as f:
        return json.load(f)

def remove_existing_workspace(workspace_path=os.path.expanduser('~/git/MicrobiomeKG/s1_raw_graph/workspace')):
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)

def create_new_workspace():
    workspace_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace")
    shell_command = ["java", "-jar", "BioDWH2-v0.6.8.jar", "-c", workspace_path]
    subprocess.run(shell_command, check=True, capture_output=True, text=True)

def update_workspace_with_db(db_name):
    workspace_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace")
    shell_command = ["java", "-jar", "BioDWH2-v0.6.8.jar", "--add-data-source", workspace_path, db_name]
    subprocess.run(shell_command, check=True, capture_output=True, text=True)
    shell_command = ["java", "-jar", "BioDWH2-v0.6.8.jar", "-u", workspace_path]
    subprocess.run(shell_command, check=True, capture_output=True, text=True)

def rm_db_from_workspace(db_name):
    workspace_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace")
    shell_command = ["java", "-jar", "BioDWH2-v0.6.8.jar", "--remove-data-source", workspace_path, db_name]
    subprocess.run(shell_command, check=True, capture_output=True, text=True)

def create_graph_db():
    workspace_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace")
    shell_command = ["java", "-jar", "BioDWH2-Neo4j-Server-v1.3.2.jar", "--create", workspace_path]
    subprocess.run(shell_command, check=True, capture_output=True, text=True)

def start_graph_db():
    workspace_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace")
    shell_command = ["java", "-jar", "BioDWH2-Neo4j-Server-v1.3.2.jar", "--start", workspace_path]
    
    process = subprocess.Popen(
        shell_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    success = False
    output_log = []
    
    try:
        for line in process.stdout:
            output_log.append(line)
            if "bolt://0.0.0.0:8083" in line:
                success = True
                break
    finally:
        process.terminate()
        process.wait()
        
    if not success:
        full_output = "".join(output_log)
        raise subprocess.CalledProcessError(
            returncode=process.returncode or 1,
            cmd=shell_command,
            output=full_output,
            stderr=full_output
        )

def main():
    available_dbs = open_available_dbs_file()
    
    
    remove_existing_workspace()
    create_new_workspace()
    
    for db in available_dbs:
        if db in dbs_with_errors or db in dbs_without_errors:
            print(f"Skipping {db} as it has already been processed. Check the error/success logs for details.")
            continue
        current_step = ""
        print(f"Running BioDWH2 for database: {db}")
        try:
            current_step = "Updating workspace"
            update_workspace_with_db(db)
            
            current_step = "Creating graph DB"
            create_graph_db()
            
            print(f"Successfully created graph DB for database: {db}")

            current_step = "Starting graph DB"
            start_graph_db()
            print(f"Successfully processed database: {db}")

            current_step = "Removing DB from workspace"
            rm_db_from_workspace(db)
            print(f"Removed {db} from workspace after successful processing.")
            
        except subprocess.CalledProcessError as e:
            error_details = e.stderr.strip() if e.stderr else str(e)
            full_error = f"Failed during '{current_step}'. Details: {error_details}"
            print(f"Command line error processing {db}:\n{full_error}")
            dbs_with_errors[db] = full_error
            
        except Exception as e:
            full_error = f"Python error during '{current_step}'. Details: {e}"
            print(f"Python error processing database {db}: {full_error}")
            dbs_with_errors[db] = full_error
            
        else:
            dbs_without_errors.append(db)
            
        with open(dbs_with_errors_json, 'w') as f:
            json.dump(dbs_with_errors, f, indent=4)

        with open(dbs_without_errors_json, 'w') as f:
            json.dump(dbs_without_errors, f, indent=4)

if __name__ == "__main__":
    main()