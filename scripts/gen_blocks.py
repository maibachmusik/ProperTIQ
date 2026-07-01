"""Generate docs/blocks.md from propertiq.registry at build time (mkdocs-gen-files).

Same single source of truth as the engine and the config app — the docs cannot
drift from behavior. Implements spec 005 FR-D2.
"""

from __future__ import annotations

import mkdocs_gen_files

from propertiq import registry

lines: list[str] = [
    "# Blocks reference",
    "",
    "Every filter and scoring criterion ProperTIQ ships, generated directly from "
    "`propertiq.registry` — the same metadata the no-code app renders as tooltips. "
    "Add a block to the library and it appears here automatically.",
    "",
]


def _params_table(block) -> list[str]:
    if not block.params:
        return ["_No parameters._", ""]
    out = ["| Parameter | Type | Required | What it does |", "|---|---|---|---|"]
    for p in block.params:
        req = "yes" if p.required else "no"
        out.append(f"| `{p.name}` | {p.type} | {req} | {p.help} |")
    out.append("")
    return out


for category in registry.categories():
    lines.append(f"## {category}")
    lines.append("")
    for block in (b for b in registry.REGISTRY if b.category == category):
        kind = "filter" if block.kind == "filter" else "criterion"
        lines.append(f"### {block.label} — `{block.key}` ({kind})")
        lines.append("")
        lines.append(block.description)
        lines.append("")
        lines.extend(_params_table(block))

with mkdocs_gen_files.open("blocks.md", "w") as fh:
    fh.write("\n".join(lines))
