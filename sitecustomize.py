import sys, os
root = os.path.dirname(__file__)
if root not in sys.path:
    sys.path.insert(0, root)
sub_repo = os.path.join(root, "kai-decisionos")
if os.path.isdir(sub_repo) and sub_repo not in sys.path:
    sys.path.insert(0, sub_repo)
