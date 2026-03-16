import os
import platform
import shutil
import sys
import glob

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

def clone_biodwh2_neo4j(source_data_dir, target_project_dir):
    # On Unix, require root for chown; on Windows, not needed
    if not IS_WINDOWS and os.geteuid() != 0:
        print("Run with sudo (required on Linux/macOS to set file ownership)")
        sys.exit(1)

    os.makedirs(target_project_dir, exist_ok=True)
    target_data_dir = os.path.join(target_project_dir, 'data')

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)

    shutil.copytree(source_data_dir, target_data_dir)

    # Remove stale lock and temp files from the source database.
    # The source DB stays running, so these locks are always present
    # and must be removed for the cloned DB to start cleanly.
    for pattern in ['**/database_lock', '**/store_lock', '**/*.tmp.*', '**/*.tmp']:
        for f in glob.glob(os.path.join(target_data_dir, pattern), recursive=True):
            os.remove(f)
            print(f"Removed stale file: {f}")

    # Fix file ownership/permissions (Unix only).
    # - Linux: chown to neo4j user (UID 7474) is sufficient
    # - macOS: also needs chmod because Docker Desktop's VirtioFS
    #          doesn't properly honor UID-based permissions
    # - Windows: Docker Desktop uses WSL2, no host-side fix needed
    if not IS_WINDOWS:
        for root, dirs, files in os.walk(target_data_dir):
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

if __name__ == "__main__":
    clone_biodwh2_neo4j(sys.argv[1], sys.argv[2])