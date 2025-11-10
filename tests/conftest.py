import sys, os
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
sub_repo = os.path.join(repo_root, "kai-decisionos")
if os.path.isdir(sub_repo) and sub_repo not in sys.path:
    sys.path.insert(0, sub_repo)
