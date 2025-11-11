import json, os

PATH = os.environ.get("GROUP_WEIGHTS_PATH", "var/cards/group_weights.json")

def load_group_weights() -> dict:
    if os.path.exists(PATH):
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # ENV fallback (기존)
    try:
        return json.loads(os.environ.get("REASON_GROUP_WEIGHTS", "{}"))
    except Exception:
        return {}
