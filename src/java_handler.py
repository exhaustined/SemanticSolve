# java_handler.py

import os
import re
import subprocess
import contextlib
import glob

JAVA_23_HOME = "C:/Program Files/Java/jdk-24"
JAVA_13_HOME = "C:/Program Files/Java/jdk-13.0.2"

JAVA_23_EXECUTABLE = os.path.join(JAVA_23_HOME, 'bin', 'java.exe')
JAVA_13_EXECUTABLE = os.path.join(JAVA_13_HOME, 'bin', 'java.exe')

def rename_class(code: str, old_class: str, new_class: str) -> str:
    decl_pattern = r'(\b(?:public\s+|final\s+|abstract\s+)?class\s+)' + re.escape(old_class) + r'(\b)'
    code = re.sub(decl_pattern, r'\1' + new_class + r'\2', code)
    ctor_pattern = r'(\b)' + re.escape(old_class) + r'(\s*\()'
    code = re.sub(ctor_pattern, r'\1' + new_class + r'\2', code)
    new_pattern = r'(\bnew\s+)' + re.escape(old_class) + r'(\b)'
    code = re.sub(new_pattern, r'\1' + new_class + r'\2', code)
    type_pattern = r'(\b)' + re.escape(old_class) + r'(\s+[a-zA-Z_]\w*\s*[=;,\)])'
    code = re.sub(type_pattern, r'\1' + new_class + r'\2', code)
    return code

def save_code_to_folder(run_dir: str, class_name: str, suffix: str, code: str):
    folder_name = f"{class_name}_{suffix}"
    base_folder_path = os.path.join(run_dir, folder_name)
    
    # NEW: Detect package declaration in the Java code
    package_match = re.search(r'^\s*package\s+([\w\.]+)\s*;', code, re.MULTILINE)
    
    if package_match:
        package_name = package_match.group(1)
        # Convert package.name to package\name structure
        package_path = package_name.replace('.', os.sep)
        full_folder_path = os.path.join(base_folder_path, package_path)
    else:
        full_folder_path = base_folder_path

    # Create the full directory tree
    os.makedirs(full_folder_path, exist_ok=True)
    
    file_path = os.path.join(full_folder_path, f"{class_name}_{suffix}.java")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Saved {file_path}")

def process_and_save_run(run_dir: str, class_name: str, base_code: str, a_code: str, b_code: str, merge_candidate_code: str):
    versions = {
        "Base": rename_class(base_code, class_name, f"{class_name}_Base"),
        "A": rename_class(a_code, class_name, f"{class_name}_A"),
        "B": rename_class(b_code, class_name, f"{class_name}_B"),
        "M": rename_class(merge_candidate_code, class_name, f"{class_name}_M"),
    }
    for suffix, code in versions.items():
        save_code_to_folder(run_dir, class_name, suffix, code)
    print("--- Files saved. Starting analysis tooling. ---")


@contextlib.contextmanager
def change_dir(path):
    """A context manager to safely change the current working directory."""
    original_dir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_dir)

def run_tooling_and_compile(run_directory: str, class_name: str, spoonrace_dir: str):
    """
    Runs SpoonRace.jar and then compiles the resulting Java files.
    """
    print(f"🔧 Running SpoonRace.jar on {os.path.basename(run_directory)} using Java 23...")
    
    with change_dir(spoonrace_dir):
        command = [JAVA_23_EXECUTABLE, "-jar", "SpoonRace.jar", run_directory, class_name]
        subprocess.run(
            command, 
            check=True,
            capture_output=True,
            text=True
        )
    print(f"   ... SpoonRace.jar completed successfully.")

    # print(f"⚙️  Compiling generated source files...")
    # JAVAC_23_EXECUTABLE = os.path.join(JAVA_13_HOME, 'bin', 'javac.exe')
    
    # suffixes = ["A", "B", "Base", "M"]
    # for suffix in suffixes:
    #     spooned_folder = os.path.join(run_directory, f"{class_name}_{suffix}_Spooned")
        
    #     if not os.path.exists(spooned_folder):
    #         raise FileNotFoundError(f"Expected folder not found: {spooned_folder}")

    #     # NEW: Dynamically find the .java file recursively, regardless of package nesting
    #     search_pattern = os.path.join(spooned_folder, "**", f"{class_name}_{suffix}.java")
    #     found_files = glob.glob(search_pattern, recursive=True)
        
    #     if not found_files:
    #         raise FileNotFoundError(f"Could not find {class_name}_{suffix}.java inside {spooned_folder}")
            
    #     java_file_path = found_files[0] # Grab the actual path to the nested file

    #     with change_dir(spooned_folder):
    #         # Pass the dynamically found file path to javac
    #         compile_command = [JAVAC_23_EXECUTABLE, java_file_path]
    #         subprocess.run(
    #             compile_command,
    #             check=True,
    #             capture_output=True,
    #             text=True
    #         )
    #         print(f"   ✅ Compiled {os.path.basename(java_file_path)}")


def run_legacy_jar(path_to_jar: str):
    """
    Example function to run the other JAR file that requires Java 13.
    """
    print(f"🔧 Running legacy JAR {os.path.basename(path_to_jar)} using Java 13...")

    command = [JAVA_13_EXECUTABLE, "-jar", path_to_jar, "some_argument", "another_argument"]
    
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        print("   ... Legacy JAR completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR running legacy JAR: {e.stderr}")
