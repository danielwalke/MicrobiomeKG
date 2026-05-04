import os
import platform
import shutil
import sys
import glob

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


def clone_kg(source_data_dir, target_project_dir):
    IS_WINDOWS = platform.system() == "Windows"
    IS_MACOS = platform.system() == "Darwin"

    os.makedirs(target_project_dir, exist_ok=True)
    target_data_dir = os.path.join(target_project_dir, 'data')

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)

    shutil.copytree(source_data_dir, target_data_dir)
    print(f"Copied data from {source_data_dir} to {target_data_dir}")
    print(os.listdir(target_data_dir))
    print(format_bytes(get_dir_size(target_data_dir)))
    for pattern in ['**/database_lock', '**/store_lock', '**/*.tmp.*', '**/*.tmp']:
        for f in glob.glob(os.path.join(target_data_dir, pattern), recursive=True):
            os.remove(f)
            print(f"Removed stale file: {f}")

    directories_to_fix = ['data', 'logs', 'conf', 'import']

    for dir_name in directories_to_fix:
        print(f"Ensuring directory exists and setting permissions: {dir_name}")
        dir_path = os.path.join(target_project_dir, dir_name)
        os.makedirs(dir_path, exist_ok=True)

        if not IS_WINDOWS:
            for root, dirs, files in os.walk(dir_path):
                if IS_MACOS:
                    os.chmod(root, 0o777)
                for d in dirs:
                    path = os.path.join(root, d)
                    if IS_MACOS:
                        os.chmod(path, 0o777)
                for f in files:
                    path = os.path.join(root, f)
                    if IS_MACOS:
                        os.chmod(path, 0o666)