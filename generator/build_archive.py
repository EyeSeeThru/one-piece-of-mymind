#!/usr/bin/env python3
"""Build the One Piece of MyMind archive (repo root index.html).
Reads every issue-*/index.html, extracts metadata, writes a searchable archive page.
Search activates automatically at 4+ issues; below that it shows a stub."""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # generator/ lives in repo root
SEARCH_AT = 4

issues = []
for d in sorted(ROOT.glob("issue-*")):
    idx = d / "index.html"
    if not idx.exists():
        continue
    html = idx.read_text(encoding="utf-8")
    n = int(d.name.split("-")[1])
    kick = re.search(r'<p class="kicker">(.*?)</p>', html, re.S)
    kicker = re.sub(r"<[^>]+>", "", kick.group(1)).replace("&nbsp;", " ").strip() if kick else ""
    week = re.search(r"Week of (.*?)(?:\s*·|\s*</)", kicker, re.S)
    week = week.group(1).strip() if week else kicker
    themes = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<h2>([^<]+)</h2>", html)]
    themes = [t for t in themes if t not in ("The reading",)]
    img = re.search(r'src="(assets/[^"]+)"', html)
    cover = f"{d.name}/{img.group(1)}" if img else ""
    cards = re.findall(r'<a class="t"[^>]*>(.*?)</a><span class="s">(.*?)</span>', html, re.S)
    strip = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
    issues.append(dict(n=n, url=f"{d.name}/", week=week, themes=themes, cover=cover,
                       cards=[dict(t=strip(t), s=strip(s)) for t, s in cards]))

issues.sort(key=lambda i: i["n"])
data = json.dumps(issues, ensure_ascii=False)
count = len(issues)
search_on = count >= SEARCH_AT

def issue_card(i):
    theme_line = " · ".join(i["themes"][:6]) + ("…" if len(i["themes"]) > 6 else "")
    return (f'<a class="issuecard" href="{i["url"]}">'
            f'<img src="{i["cover"]}" alt="Issue {i["n"]} cover">'
            f'<span class="inum">Issue No. {i["n"]}</span>'
            f'<span class="iweek">{i["week"]}</span>'
            f'<span class="ithemes">{theme_line}</span></a>')

stub = (f'<input id="q" type="text" disabled placeholder="Search arrives at Issue {SEARCH_AT} — '
        f'{count} of {SEARCH_AT} issues so far">')
live = '<input id="q" type="text" placeholder="Search issues, themes, and cards">'

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>One Piece of MyMind · The Archive</title>
<style>
  :root {{ --bg:#060505; --red:#e5322d; --red-deep:#cf2d27; --red-dim:#9c201b; --red-line:#571311; }}
  * {{ box-sizing:border-box; }}
  html {{ background:var(--bg); }}
  body {{ margin:0; background:var(--bg); color:var(--red); font-family:Georgia,'Times New Roman',serif; line-height:1.5; }}
  .page {{ max-width:1100px; margin:0 auto; padding:46px 36px 90px; }}
  header.masthead {{ border-bottom:1px solid var(--red-line); padding:10px 0 30px; }}
  .kicker {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:11px; letter-spacing:3px;
             text-transform:uppercase; color:var(--red-dim); margin:0 0 16px; }}
  h1 {{ font-size:64px; line-height:1.0; margin:0 0 14px; font-weight:700; letter-spacing:-1px; color:var(--red); }}
  .deck {{ font-size:18px; color:var(--red-deep); margin:0; font-style:italic; }}
  .searchbar {{ margin:34px 0 40px; }}
  #q {{ width:100%; max-width:560px; background:#0d0b0b; color:var(--red); border:1px solid var(--red-line);
        padding:12px 16px; font-size:15px; font-family:Georgia,serif; outline:none; }}
  #q:disabled {{ color:var(--red-dim); }}
  #q::placeholder {{ color:var(--red-dim); }}
  .issues {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:36px 26px; }}
  .issuecard {{ display:flex; flex-direction:column; text-decoration:none; }}
  .issuecard img {{ width:100%; aspect-ratio:4/3; object-fit:cover; border:1px solid var(--red-line);
                    filter:grayscale(14%) contrast(1.04); }}
  .issuecard .inum {{ font-size:20px; font-weight:700; color:var(--red); margin-top:12px; }}
  .issuecard .iweek {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:10.5px; letter-spacing:1.6px;
                       text-transform:uppercase; color:var(--red-dim); margin-top:4px; }}
  .issuecard .ithemes {{ font-size:13.5px; color:var(--red-deep); margin-top:8px; }}
  .noresults {{ display:none; margin-top:8px; color:var(--red-deep); font-style:italic; }}
  footer {{ margin-top:90px; border-top:1px solid var(--red-line); padding-top:18px;
            font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; color:var(--red-dim); }}
  ::selection {{ background:var(--red); color:#000; }}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <p class="kicker">The Archive &nbsp;·&nbsp; {count} issue{'s' if count != 1 else ''}</p>
    <h1>One Piece of MyMind</h1>
    <p class="deck">Every issue of the weekly zine built from your MyMind saves.</p>
  </header>
  <div class="searchbar">{live if search_on else stub}</div>
  <div class="issues" id="issues">
    {"".join(issue_card(i) for i in issues)}
  </div>
  <p class="noresults" id="noresults">Nothing matches that.</p>
  <footer>Weekly issues are added as they ship. Search activates at Issue {SEARCH_AT}.</footer>
</div>
<script>
const ISSUES = {data};
const q = document.getElementById('q');
if (q && !q.disabled) {{
  q.addEventListener('input', () => {{
    const query = q.value.trim().toLowerCase();
    let any = false;
    document.querySelectorAll('.issuecard').forEach((el, idx) => {{
      const i = ISSUES[idx];
      if (!query) {{ el.style.display = ''; return; }}
      const hay = (i.week + ' ' + i.themes.join(' ') + ' ' +
        i.cards.map(c => c.t + ' ' + c.s).join(' ')).toLowerCase();
      const hit = hay.includes(query);
      el.style.display = hit ? '' : 'none';
      if (hit) any = true;
    }});
    document.getElementById('noresults').style.display = any ? 'none' : 'block';
  }});
}}
</script>
</body>
</html>'''
(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"archive written: {count} issues, search {'ON' if search_on else 'stub (activates at ' + str(SEARCH_AT) + ')'}")
