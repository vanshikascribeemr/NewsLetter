
import os
import shutil

SOURCE_DIR = os.getcwd()
DEST_DIR = os.path.join(SOURCE_DIR, "deployment_package")
SRC_CODE_DIR = os.path.join(SOURCE_DIR, "src")
DEST_SRC_DIR = os.path.join(DEST_DIR, "src")

def update_package():
    print(f"Updating deployment package at: {DEST_DIR}")
    
    # 1. Update src directory
    if os.path.exists(DEST_SRC_DIR):
        shutil.rmtree(DEST_SRC_DIR)
    
    # Invoke copytree ignoring pycache
    shutil.copytree(SRC_CODE_DIR, DEST_SRC_DIR, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    print(f"[OK] Synced src/ directory ({len(os.listdir(DEST_SRC_DIR))} files)")
    
    # 2. Update root files
    files_to_copy = [
        "requirements.txt",
        "README.md",
        "setup_cron.sh",
        ".env",
        "get_token.py",
        "inspect_db.py",
        "newsletter.db"
    ]
    
    for filename in files_to_copy:
        src_file = os.path.join(SOURCE_DIR, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, DEST_DIR)
            print(f"[OK] Updated {filename}")
        else:
            print(f"[WARN] Use file {filename} not found in root")
            
    print("\nDeployment package updated successfully!")

if __name__ == "__main__":
    update_package()
