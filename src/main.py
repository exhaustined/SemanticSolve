# main_script.py

import os
import time
import sys
import subprocess # Import subprocess
import itertools
import re
from git_utils import get_merge_base, get_file_from_commit
from llm_api import get_merge_candidates, refine_merge_candidate
# Import the new function
from java_handler import process_and_save_run, run_tooling_and_compile
from ast_utils import find_conflicting_methods, get_method_name, get_method_calls
from prompt_builder import build_prompt, build_method_prompt, build_report_prompt

# === Config ===
repo_path = "C:/Users/jess/Downloads/Sample Conflict/Sample Conflict"
file_path = "src/TransactionService.java"
branch_a = "Priority"
branch_b = "Date"

# We assume this script is in SemanticSolve/src/
# Go up one level to SemanticSolve/, then into SpoonRace/
# SPOONRACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'SpoonRace'))
# SPOONRACE_DIR = os.path.abspath("SpoonRace")

USE_LOCAL_BENCHMARK = True
BENCHMARK_ROOT = r"C:\Users\jess\Downloads\SemanticSolve\SemanticSolve\ConflictBench"

SPOONRACE_DIR = r"C:\Users\jess\Downloads\SemanticSolve\SemanticSolve\SpoonRace"
if os.path.exists(SPOONRACE_DIR):
    print(f"Success: JAR found at {SPOONRACE_DIR}")
else:
    print(f"Error: JAR not found! Check path: {SPOONRACE_DIR}")
OUTPUT_ROOT_PATH = os.path.join(SPOONRACE_DIR, "Root")

output_path = "candidates/merge_result.java" 

if len(sys.argv) > 1:
    class_name = sys.argv[1]
else:
    print("[❌] Please provide a class name as an argument.")
    sys.exit(1)

MERGE_SEPARATOR = "// MERGE_CANDIDATE_SEPARATOR"

# === Step 1 & 2: Get code (No changes) ===
if USE_LOCAL_BENCHMARK:
    print(f"\nExtracting code from local ConflictBench folder...")
    
    def read_local_file(subfolder, filename):
        file_path = os.path.join(BENCHMARK_ROOT, subfolder, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"[❌] Error: Could not find {file_path}")
            return None
            
    target_file = f"{class_name}.java"
    
    base_code = read_local_file("base", target_file)
    a_code = read_local_file("left", target_file)  # 'left' maps to Branch A
    b_code = read_local_file("right", target_file) # 'right' maps to Branch B
    
    if not all([base_code, a_code, b_code]):
        print("[❌] Could not load all local code versions. Aborting.")
        sys.exit(1)
    else:
        print("✅ Got code from local ConflictBench folders (base, left, right).")

else:
    # --- Original Git Extraction Logic ---
    print(f"\nExtracting code from Git repository...")
    base_commit = get_merge_base(repo_path, branch_a, branch_b)
    print(f"📘 Base commit (O): {base_commit}")
    base_code = get_file_from_commit(repo_path, base_commit, file_path)
    a_code = get_file_from_commit(repo_path, branch_a, file_path)
    b_code = get_file_from_commit(repo_path, branch_b, file_path)
    
    if not all([base_code, a_code, b_code]):
        print("[❌] Could not load all code versions from Git. Aborting.")
        sys.exit(1)
    else:
        print("✅ Got code from Git versions (Base, A, B).")

# === Step 3: Decompose and Find Conflicts ===
print("\nDecomposing code using AST to find method-level conflicts...")
conflicting_methods = find_conflicting_methods(base_code, a_code, b_code)

if not conflicting_methods:
    print("[✅] No semantic method-level conflicts found via AST. Exiting.")
    sys.exit(0)

print(f"Found {len(conflicting_methods)} conflicting method(s).")

# === Step 3.5: Interprocedural Call-Graph Clustering (AST-Powered) ===
print("\nBuilding Interprocedural Call-Graph Clusters via AST...")

signatures = list(conflicting_methods.keys())
adj_list = {sig: set() for sig in signatures}

# Build adjacency list based on AST method invocations
for i, sig1 in enumerate(signatures):
    name1 = get_method_name(sig1)
    
    for j, sig2 in enumerate(signatures):
        if i == j: continue
        
        # Combine the code of Base, A, and B for sig2 to check all possible calls
        code2_combined = conflicting_methods[sig2]['base'] + "\n" + conflicting_methods[sig2]['A'] + "\n" + conflicting_methods[sig2]['B']
        
        # Use our new AST function to get all methods called inside sig2
        calls_inside_sig2 = get_method_calls(code2_combined)
        
        # If sig2 calls sig1, they interact! Link them.
        if name1 in calls_inside_sig2:
            adj_list[sig1].add(sig2)
            adj_list[sig2].add(sig1) # Undirected graph for clustering

# Find connected components (Clusters)
visited = set()
clusters = []
for sig in signatures:
    if sig not in visited:
        cluster = []
        queue = [sig]
        while queue:
            curr = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                cluster.append(curr)
                queue.extend(list(adj_list[curr] - visited))
        clusters.append(cluster)

for idx, cluster in enumerate(clusters, 1):
    print(f"  Cluster {idx}: {cluster}")

# === Step 4: Call LLM per CLUSTER (Not per method) ===
cluster_candidates = {} # Format: { cluster_idx: [ {sig1: code, sig2: code}, ... ] }

for cluster_idx, cluster_sigs in enumerate(clusters):
    print(f"\nCalling LLM for Cluster {cluster_idx + 1} ({len(cluster_sigs)} methods)...")
    
    prompt = build_cluster_prompt(cluster_sigs, conflicting_methods, base_code)
    
    start = time.time()
    result = get_merge_candidates(prompt)
    print(f"Completed in {time.time() - start:.2f} seconds.")
    
    if result:
        # Split candidates
        raw_cands = [c.strip() for c in result.split(MERGE_SEPARATOR) if c.strip()]
        parsed_cands = []
        
        for raw_cand in raw_cands:
            cand_dict = {}
            # Parse the XML-like tags the LLM was instructed to use
            for sig in cluster_sigs:
                # Regex to extract code between <method name="sig"> and </method>
                pattern = r'<method\s+name="' + re.escape(sig) + r'">\s*(.*?)\s*</method>'
                match = re.search(pattern, raw_cand, re.DOTALL)
                if match:
                    # Clean up any markdown the LLM might have snuck inside the tags
                    clean_code = match.group(1).replace("```java", "").replace("```", "").strip()
                    cand_dict[sig] = clean_code
                else:
                    print(f"[⚠️] Warning: Could not parse method {sig} from candidate. Skipping this candidate.")
                    break
            
            # Only add if we successfully parsed all methods in the cluster
            if len(cand_dict) == len(cluster_sigs):
                parsed_cands.append(cand_dict)
                
        if not parsed_cands:
            print(f"[❌] Failed to parse any valid candidates for Cluster {cluster_idx + 1}.")
            sys.exit(1)
            
        cluster_candidates[cluster_idx] = parsed_cands
        print(f"  -> Extracted {len(parsed_cands)} valid interprocedural candidates for Cluster {cluster_idx + 1}.")
    else:
        print(f"[❌] Failed to generate candidates for Cluster {cluster_idx + 1}")
        sys.exit(1)

# === Step 5: TRUE Permutation Synthesis Engine (Cluster-Level) ===
print("\nAssembling all valid candidate combinations (Cluster Permutation Engine)...")

lists_of_candidates = [cluster_candidates[i] for i in range(len(clusters))]
all_combinations = list(itertools.product(*lists_of_candidates))

print(f"Generated {len(all_combinations)} unique permutations to test.")

integrated_file_candidates = []
combo_logs = []

for combo_idx, combo in enumerate(all_combinations, 1):
    new_file_code = base_code
    combo_description = {}
    
    # combo is a tuple of dictionaries, one dict per cluster
    for cluster_idx, cluster_dict in enumerate(combo):
        cand_num = cluster_candidates[cluster_idx].index(cluster_dict) + 1
        
        for sig, merged_method in cluster_dict.items():
            original_base_method = conflicting_methods[sig]["base"]
            new_file_code = new_file_code.replace(original_base_method, merged_method)
            combo_description[sig] = f"Cluster {cluster_idx + 1} - Candidate {cand_num}"
            
    integrated_file_candidates.append(new_file_code)
    combo_logs.append({"Permutation_ID": combo_idx, "Composition": combo_description})

# === Step 6: Proceed to Tooling ===
print(f"\nRunning tooling and compilation on {len(integrated_file_candidates)} candidates...")

run_results = []

for i, candidate_code in enumerate(integrated_file_candidates, 1):
    run_num = i
    print(f"\n{'='*20} CANDIDATE #{run_num} {'='*20}")
    
    run_directory = os.path.join(OUTPUT_ROOT_PATH, f"Cand_{run_num}")
    process_and_save_run(run_directory, class_name, base_code, a_code, b_code, candidate_code)
        
    try:
        run_tooling_and_compile(run_directory, class_name, SPOONRACE_DIR)
        print(f"✅ Successfully completed tooling and compilation for Run #{run_num}.")
        run_results.append({
            "Permutation_ID": run_num,
            "Status": "SUCCESS",
            "Message": "Passed all compiler and interprocedural static analysis checks."
        })
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR during tooling for Run #{run_num}: {e}")
        error_msg = e.stderr.strip() if e.stderr else "Unknown compilation/tooling error."
        run_results.append({
            "Permutation_ID": run_num,
            "Status": "FAILED",
            "Error_Log": error_msg
        })
    except FileNotFoundError as e:
        print(f"❌ ERROR: File not found for Run #{run_num}: {e}")
        run_results.append({
            "Permutation_ID": run_num,
            "Status": "FAILED",
            "Error_Log": "Internal System Error: Missing SpoonRace output files."
        })

print("\nSaving successful merge candidates...")
successful_merges = [res for res in run_results if res["Status"] == "SUCCESS"]

if successful_merges:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for success in successful_merges:
            cand_idx = success["Permutation_ID"] - 1
            winning_code = integrated_file_candidates[cand_idx]
            
            f.write(f"// SUCCESSFUL PERMUTATION {success['Permutation_ID']}\n")
            f.write(winning_code)
            f.write(f"\n{MERGE_SEPARATOR}\n")
            
    print(f"✅ Saved {len(successful_merges)} successful merge(s) to {output_path}")
else:
    print(f"No successful permutations found. {output_path} was not updated.")

# === Step 7: Generate Final Developer Report ===

print("\nSynthesizing final report")
start = time.time()
report_prompt = build_report_prompt(class_name, conflicting_methods, combo_logs, run_results)

final_report_text = get_merge_candidates(report_prompt)

if final_report_text:
    report_path = "candidates/Merge_Resolution_Report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report_text)
    print(f"Report generated in {time.time() - start:.2f} seconds.")
    print(f"Saved to: {report_path}")
else:
    print("[❌] Failed to generate the final report.")

print(f"\n{'='*50}\nWorkflow complete. All candidates processed.\n{'='*50}")

