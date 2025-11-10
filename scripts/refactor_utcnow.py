from __future__ import annotations

import pathlib
import re

SKIP_DIRS = {".git", ".venv", "vendor", "__pycache__"}
TARGET = "datetime." + "utc" + "now()"


def should_skip(path: pathlib.Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def main() -> None:
    root = pathlib.Path(".")
    for py_file in root.rglob("*.py"):
        if should_skip(py_file):
            continue
        text = py_file.read_text(encoding="utf-8")
        if TARGET not in text:
            continue
        new_text = text.replace(TARGET, "datetime.now(UTC)")
        if new_text != text:
            if "from datetime import" in new_text and "UTC" not in new_text.split("from datetime import", 1)[1].splitlines()[0]:
                new_text = new_text.replace("from datetime import datetime", "from datetime import datetime, UTC", 1)
            elif "import datetime" in new_text and "from datetime import UTC" not in new_text:
                new_text = new_text.replace("import datetime", "import datetime\nfrom datetime import UTC", 1)
            py_file.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    main()
