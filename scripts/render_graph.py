"""Render the compiled agent graph to assets/graph.png (and .mmd).

Uses LangGraph's Mermaid renderer (PNG via the mermaid.ink API, needs network).
Run after changing the graph topology:

    python scripts/render_graph.py
"""

from __future__ import annotations

from pathlib import Path

from nlp2sql.graph import build_graph

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    graph = build_graph().get_graph()

    (ASSETS / "graph.mmd").write_text(graph.draw_mermaid())
    print(f"wrote {ASSETS / 'graph.mmd'}")

    png = graph.draw_mermaid_png()
    (ASSETS / "graph.png").write_bytes(png)
    print(f"wrote {ASSETS / 'graph.png'} ({len(png):,} bytes)")


if __name__ == "__main__":
    main()
