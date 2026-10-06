"""Render a text template whose numbers are provenance keys ({{key}}) into final Markdown.
usage: python src/render_text.py analysis/<run_id> <template.md> <output.md>
Unknown keys raise an error, so no number in the output can be typed by hand.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provenance import Prov  # noqa: E402

if __name__ == "__main__":
    ad, tpl, out = sys.argv[1:4]
    P = Prov(ad)
    text = open(tpl).read()
    open(out, "w").write(P.render(text))
    print(f"{out}: {len(P.used)} provenance-resolved numbers")
