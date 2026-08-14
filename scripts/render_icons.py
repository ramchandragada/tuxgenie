#!/usr/bin/env python3
"""Render assets/tuxgenie.svg into hicolor PNG sizes + docs favicons."""
from __future__ import annotations

import os
import sys

try:
    import cairosvg
except ImportError:
    sys.exit("cairosvg required: pip install cairosvg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG = os.path.join(ROOT, "assets", "tuxgenie.svg")
SIZES = (16, 32, 48, 64, 128, 256)


def render(out_path: str, size: int) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cairosvg.svg2png(
        url=SVG,
        write_to=out_path,
        output_width=size,
        output_height=size,
    )


def main() -> None:
    if not os.path.isfile(SVG):
        sys.exit(f"missing {SVG}")
    for sz in SIZES:
        out = os.path.join(ROOT, "assets", f"tuxgenie-{sz}.png")
        render(out, sz)
        print(f"  {out}")
    docs = os.path.join(ROOT, "docs")
    import shutil
    shutil.copy2(SVG, os.path.join(docs, "tuxgenie.svg"))
    render(os.path.join(docs, "favicon-64.png"), 64)
    render(os.path.join(docs, "tuxgenie-256.png"), 256)
    print("done")


if __name__ == "__main__":
    main()
