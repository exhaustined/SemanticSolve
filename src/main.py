import os, time
from git_utils import get_merge_base, get_file_from_commit
from prompt_builder import build_prompt
from llm_api import get_merge_candidates

# === Config ===
repo_path = "C:/Users/DELL/Desktop/Sample Conflict"
file_path = "src/TransactionService.java"
branch_a = "FraudCheck"
branch_b = "LargeOrders"
output_path = "candidates/merge_result.java"

os.makedirs("candidates", exist_ok=True)

# === Step 1: Get base commit ===
base_commit = get_merge_base(repo_path, branch_a, branch_b)
print(f"📘 Base commit (O): {base_commit}")

# === Step 2: Load code ===
base_code = get_file_from_commit(repo_path, base_commit, file_path)
a_code = get_file_from_commit(repo_path, branch_a, file_path)

b_code = get_file_from_commit(repo_path, branch_b, file_path)
if not all([base_code, a_code, b_code]):
    print("[❌] Could not load all code versions. Aborting.")
    exit()
else:
    print("Got code from both branches")

# === Step 3: Create prompt ===
prompt = build_prompt(base_code, a_code, b_code)

# === Step 4: Call LLM ===
print("Calling R1")
start = time.time()
result = get_merge_candidates(prompt)

if result:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"[✅] Merge candidate(s) saved to {output_path}")
else:
    print("[❌] Merge candidates could not be generated.")
print("Completed in ",time.time()-start," s")