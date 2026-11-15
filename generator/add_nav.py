#!/usr/bin/env python3
"""Inject a prev · archive · next nav strip into an issue page. Idempotent.
Usage: python3 add_nav.py issue-2/index.html --prev issue-1/ --next ''"""
import re, sys
from pathlib import Path

path = Path(sys.argv[1])
prev = sys.argv[sys.argv.index("--prev") + 1] if "--prev" in sys.argv else ""
nxt = sys.argv[sys.argv.index("--next") + 1] if "--next" in sys.argv else ""

html = path.read_text(encoding="utf-8")
if "issuenav" in html:
    print(f"nav already present: {path.name}")
    sys.exit(0)

links = ['<a href="/">Archive</a>']
if prev: links.append(f'<a href="{prev}">&larr; Previous</a>')
if nxt: links.append(f'<a href="{nxt}">Next &rarr;</a>')
nav = '<nav class="issuenav">' + " &nbsp;·&nbsp; ".join(links) + "</nav>"
css = ('.issuenav { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:11px; letter-spacing:2px; '
       'text-transform:uppercase; color:var(--red-dim); margin:0 0 18px; } '
       '.issuenav a { color:var(--red-deep); text-decoration:none; } .issuenav a:hover { color:var(--red); }')

html = html.replace("</style>", css + "</style>", 1)
html = html.replace('<div class="page">', '<div class="page">\n  ' + nav, 1)
path.write_text(html, encoding="utf-8")
print(f"nav injected: {path.name} (prev={prev or 'none'}, next={nxt or 'none'})")
