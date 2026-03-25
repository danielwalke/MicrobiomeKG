import os
import platform
import shutil
import sys
import glob


def clone_kg(source_data_dir, target_project_dir):
    IS_WINDOWS = platform.system() == "Windows"
    IS_MACOS = platform.system() == "Darwin"
    if not IS_WINDOWS and os.geteuid() != 0:
        print("Run with sudo (required on Linux/macOS to set file ownership)")
        sys.exit(1)

    os.makedirs(target_project_dir, exist_ok=True)
    target_data_dir = os.path.join(target_project_dir, 'data')

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)

    shutil.copytree(source_data_dir, target_data_dir)

    for pattern in ['**/database_lock', '**/store_lock', '**/*.tmp.*', '**/*.tmp']:
        for f in glob.glob(os.path.join(target_data_dir, pattern), recursive=True):
            os.remove(f)
            print(f"Removed stale file: {f}")

    directories_to_fix = ['data', 'logs', 'conf', 'import']

    for dir_name in directories_to_fix:
        dir_path = os.path.join(target_project_dir, dir_name)
        os.makedirs(dir_path, exist_ok=True)

        if not IS_WINDOWS:
            for root, dirs, files in os.walk(dir_path):
                os.chown(root, 7474, 7474)
                if IS_MACOS:
                    os.chmod(root, 0o777)
                for d in dirs:
                    path = os.path.join(root, d)
                    os.chown(path, 7474, 7474)
                    if IS_MACOS:
                        os.chmod(path, 0o777)
                for f in files:
                    path = os.path.join(root, f)
                    os.chown(path, 7474, 7474)
                    if IS_MACOS:
                        os.chmod(path, 0o666)