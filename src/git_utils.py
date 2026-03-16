from git import Repo

def get_merge_base(repo_path, branch_a, branch_b):
    repo = Repo(repo_path)
    merge_base = repo.git.merge_base(branch_a, branch_b)
    return merge_base.strip()

def get_file_from_commit(repo_path, commit_hash_or_branch, file_path):
    repo = Repo(repo_path)
    try:
        content = repo.git.show(f"{commit_hash_or_branch}:{file_path}")
        return content
    except Exception as e:
        print(f"[❌] Error fetching file from {commit_hash_or_branch}: {e}")
        return None
