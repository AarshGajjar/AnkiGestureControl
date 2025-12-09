import zipfile
import os
import sys

def package_addon():
    addon_name = "anki_gesture_control"
    output_filename = f"{addon_name}.ankiaddon"
    
    # Files/Dirs to EXCLUDE
    excludes = [
        "package_addon.py",
        output_filename,
        "__pycache__",
        ".git",
        "python_env",
        ".venv",
    ]
    
    # Get current directory
    source_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Packaging {addon_name} from {source_dir}...")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Filter directories in-place to prevent walking into excluded dirs
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file in excludes or file.endswith(".ankiaddon") or file.endswith(".pyc"):
                    continue
                
                file_path = os.path.join(root, file)
                # Archive name should be relative to source_dir
                arcname = os.path.relpath(file_path, source_dir)
                
                print(f"Adding {arcname}")
                zipf.write(file_path, arcname)
                
    print(f"\nSuccessfully created {output_filename}")
    print(f"Location: {os.path.join(source_dir, output_filename)}")

if __name__ == "__main__":
    package_addon()
