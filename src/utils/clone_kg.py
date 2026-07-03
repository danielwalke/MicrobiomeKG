import os
import platform
import glob
import subprocess

def get_dir_size(path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def format_bytes(size):
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024

def clone_kg(source_dir, target_project_dir):
    IS_WINDOWS = platform.system() == "Windows"
    
    abs_source = os.path.abspath(source_dir)
    if not abs_source.endswith('data') and os.path.exists(os.path.join(abs_source, 'data')):
        abs_source = os.path.join(abs_source, 'data')
        
    abs_target = os.path.abspath(target_project_dir)
    target_data_dir = os.path.join(abs_target, 'data')

    if not IS_WINDOWS:
        common_path = os.path.commonpath([abs_source, abs_target])

        def run_docker(cmd):
            subprocess.run([
                "docker", "run", "--rm", "--user", "7474:7474",
                "-v", f"{common_path}:{common_path}", "neo4j:latest",
                "sh", "-c", cmd
            ], check=False)

    if os.path.exists(target_data_dir):
        print(f"Wiping existing target directory: {target_data_dir}")
        if IS_WINDOWS:
            subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', target_data_dir], check=False)
        else:
            run_docker(f"rm -rf '{target_data_dir}'")

    os.makedirs(abs_target, exist_ok=True)
    os.makedirs(target_data_dir, exist_ok=True)

    if not IS_WINDOWS:
        os.chmod(abs_target, 0o777)
        os.chmod(target_data_dir, 0o777)

    print("Copying data...")
    if IS_WINDOWS:
        subprocess.run(['xcopy', abs_source, target_data_dir, '/E', '/H', '/C', '/I', '/Y'], check=False)
    else:
        run_docker(f"cp -r '{abs_source}'/. '{target_data_dir}/'")

    print(f"Total size: {format_bytes(get_dir_size(target_data_dir))}")

    print("Cleaning locks...")
    if IS_WINDOWS:
        for pattern in ['**/database_lock', '**/store_lock', '**/*.tmp.*', '**/*.tmp']:
            for f in glob.glob(os.path.join(target_data_dir, pattern), recursive=True):
                try:
                    os.remove(f)
                except Exception:
                    pass
    else:
        run_docker(f"find '{target_data_dir}' -type f \\( -name 'database_lock' -o -name 'store_lock' -o -name '*.tmp.*' -o -name '*.tmp' \\) -exec rm -f {{}} +")

    directories_to_fix = ['data', 'logs', 'conf', 'import']
    for dir_name in directories_to_fix:
        dir_path = os.path.join(abs_target, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        if not IS_WINDOWS:
            os.chmod(dir_path, 0o777)

    print(f"\nClone successful! Target ready at: {abs_target}")