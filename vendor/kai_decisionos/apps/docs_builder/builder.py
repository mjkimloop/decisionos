from __future__ import annotations

from pathlib import Path
from typing import Dict


def render_template(template_path: Path, context: Dict[str, str], output_path: Path) -> str:
    template_text = template_path.read_text(encoding="utf-8")
    content = template_text.format(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content


def generate_bundle(templates_dir: Path, context: Dict[str, str], output_dir: Path) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for template_path in templates_dir.glob("*.tpl"):
        target = output_dir / template_path.with_suffix(".md").name
        outputs[str(target)] = render_template(template_path, context, target)
    return outputs


__all__ = ["render_template", "generate_bundle"]

