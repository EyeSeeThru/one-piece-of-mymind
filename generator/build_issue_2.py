#!/usr/bin/env python3
"""Build 'One Piece of MyMind' Issue 2 — dark gallery, curated themes, no dumps/dupes/placeholders."""
import json, os, re, subprocess, html as htmlmod
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request

HOME = os.path.expanduser("~")
VAULT = f"{HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/EyeOS/Second Brain/Bookmarks/One-Piece-of-MyMind"
ASSETS = Path(VAULT) / "assets"
MYMIND = f"{HOME}/bin/mymind"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML_PATH = Path(VAULT) / "one-piece-of-mymind-issue-2-gallery.html"
PDF_PATH = Path(VAULT) / "one-piece-of-mymind-issue-2-gallery.pdf"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
BOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

ASSETS.mkdir(parents=True, exist_ok=True)
objs = json.load(open("/tmp/pom2_week.json"))
by_id = {o.get("id"): o for o in objs}

def esc(s): return htmlmod.escape(s or "", quote=True)

def norm(u):
    p = urlsplit(u); h = (p.hostname or "").lower()
    if h.startswith("www."): h = h[4:]
    path = re.sub(r"/+$", "", p.path)
    if h in ("youtube.com", "m.youtube.com", "youtu.be"):
        vid = p.path.strip("/") if h == "youtu.be" else None
        if not vid:
            m = re.search(r"[?&]v=([\w-]+)", u)
            vid = m.group(1) if m else None
        if vid: return f"youtube.com/watch/{vid}"
    if h == "instagram.com":
        m = re.match(r"/(p|reel|reels|tv)/([\w-]+)", p.path)
        if m: return f"instagram.com/{m.group(1)}/{m.group(2)}"
    if h in ("x.com", "twitter.com"):
        m = re.match(r"/\w+/status/(\d+)", p.path)
        if m: return f"x.com/status/{m.group(1)}"
    return h + path

def domain(u):
    h = urlsplit(u).hostname or ""
    return h[4:] if h.startswith("www.") else h

def clean(s): return re.sub(r"\[\[([^\]]+)\]\]", r"\1", re.sub(r"\s+", " ", s or "")).strip()

def trim(s, n=220):
    s = clean(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def mm_link(oid): return f"https://access.mymind.com/everything#{oid}"

def existing_image(oid):
    for ext in ("webp", "jpg"):
        p = ASSETS / f"{oid}.{ext}"
        if p.exists() and p.stat().st_size > 3000:
            return f"assets/{oid}.{ext}"
    return None

def mymind_thumb(oid, dest):
    r = subprocess.run([MYMIND, "objects", "thumbnail", oid, "--size", "640x640", "--output", dest],
                       capture_output=True, text=True, timeout=90)
    return r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 3000

def dl(url, dest, referer=None, ua=UA):
    try:
        h = {"User-Agent": ua}
        if referer: h["Referer"] = referer
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=20) as r:
            b = r.read()
        if len(b) < 3000: return False
        open(dest, "wb").write(b)
        return True
    except Exception:
        return False

def og_image(page_url):
    for ua in (UA, BOT):
        try:
            req = urllib.request.Request(page_url, headers={"User-Agent": ua, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=20) as r:
                page = r.read(2500000).decode("utf-8", "ignore")
        except Exception:
            continue
        for p in (re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', re.I),
                  re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
                  re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)', re.I)):
            m = p.search(page)
            if m: return m.group(1).replace("&amp;", "&")
    return None

def embed_shot(embed_url, oid, crop):
    shot = f"/tmp/embed2_{oid}.png"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--window-size=720,900",
                    f"--screenshot={shot}", embed_url], capture_output=True, timeout=90)
    if not os.path.exists(shot): return None
    from PIL import Image
    im = Image.open(shot)
    im.crop(crop).convert("RGB").save(f"{ASSETS}/{oid}.jpg", "JPEG", quality=88)
    return f"assets/{oid}.jpg"

def resolve_image(o):
    oid = o["id"]
    have = existing_image(oid)
    if have: return have
    url = o.get("source", {}).get("url", "") or ""
    dest_webp = ASSETS / f"{oid}.webp"
    if mymind_thumb(oid, str(dest_webp)):
        return f"assets/{oid}.webp"
    me = o.get("mainEntity")
    etype = me.get("@type") if isinstance(me, dict) else None
    etype = "/".join(etype) if isinstance(etype, list) else (etype or "")
    m = re.search(r"instagram\.com/(p|reel|tv)/([\w-]+)", url)
    if m and etype in ("InstagramPost", "InstagramReel"):
        img = embed_shot(f"https://www.instagram.com/{m.group(1)}/{m.group(2)}/embed/captioned/", oid, (0, 50, 720, 900))
        if img: return img
    m = re.search(r"threads\.(?:com|net)/(@[\w.]+)/post/(\w+)", url)
    if m:
        img = embed_shot(f"https://www.threads.net/{m.group(1)}/post/{m.group(2)}/embed", oid, (22, 142, 281, 600))
        if img: return img
    og = og_image(url) if url else None
    if og:
        dest_jpg = ASSETS / f"{oid}.jpg"
        if dl(og, str(dest_jpg), referer=url): return f"assets/{oid}.jpg"
        if dl(og, str(dest_webp), referer=url): return f"assets/{oid}.webp"
    return None

def get_object(oid):
    r = subprocess.run([MYMIND, "objects", "get", oid, "--json"], capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None

def card_html(o, img, extra_note=None):
    oid = o.get("id", "")
    url = o.get("source", {}).get("url", "") or ""
    href = url if url else mm_link(oid)
    title = clean(o.get("title")) or "(untitled)"
    summ = trim(o.get("summary"))
    dom = domain(url) if url else "mymind"
    created = (o.get("created", "") or "")[:10]
    if extra_note:
        summ = f"Saved {created}. {summ} {extra_note}".strip()
    img_tag = f'<img src="{img}" alt="" loading="lazy">' if img else ""
    cls = "card" + ("" if img else " noimg")
    return (f'<figure class="{cls}">{img_tag}<div class="cap">'
            f'<a class="t" href="{esc(href)}" target="_blank" rel="noopener">{esc(title)}</a>'
            f'<span class="s">{esc(summ)}</span><span class="d">{esc(dom)}</span></div></figure>')

SECTIONS = [
    dict(eyebrow="Pictures · one", title="The mask", count_label="7 pictures",
         ids=["00000001To00O4T8Dlpv5C", "00000001To00O4T8DbicgM", "00000001To00O4T8CZ7iKY", "00000001To00O4RZC0bnFe"],
         extra_ids=["00000001To00O2BpiaDofm", "00000001To00O4nazPQTF6", "00000001To00O4nazu9pmg"],
         read_along="00000001To00O4S02aU0yA",
         intro=("Four masks from this week. Three come from one couture series: a profile in a black rhinestone head mask, "
                "a beaded mask on a mannequin bust in a lace jacket, and a model in a fully crystal-covered mask over a cream "
                "blazer with raw seams. The fourth is a carved wooden mask with curled horns, shot on black. Three saves from "
                "earlier months join them: an ancient clay mask from last November, a Dogon ceremonial mask wearer from August, "
                "and a museum plate of African masks. The couture masks hide a face to make a new one; the carved masks were "
                "made to become someone else entirely. Read alongside: the Vatican's Anima Mundi collection and the debate over "
                "sacred objects gifted to it.")),
    dict(eyebrow="Pictures · two", title="Drawing the universe", count_label="9 pictures",
         ids=["00000001To00O4RfFClIqI", "00000001To00O4RfFswyQ0", "00000001To00O4RfFekCkM", "00000001To00O4RfEYmxK8",
              "00000001To00O4SxpQwtxK", "00000001To00O4S6Pf9wMo"],
         extra_ids=["00000001To00O2VqGE4hvq", "00000001To00O30npmAtI4", "00000001To00O3eBjH8T3q"],
         read_along=None,
         intro=("Four vintage diagrams from one save: Earth and Moon orbiting the Sun month by month, a sectional view of the "
                "Sun with the inner planets, the whole system with orbital circles and grid lines, and the Sun, Jupiter, Earth, "
                "and Moon compared by diameter. Two animated astronauts drift beside them: one floating near a glowing black "
                "hole, one lying on a night beach while a red planet rises. Three earlier saves extend the lineage: a solar "
                "system diagram from January, a vintage palmistry chart, and a solar anatomy chart from March. Palmistry and "
                "astronomy in one row is the point: they are both attempts to draw systems too big to see.")),
    dict(eyebrow="Pictures · three", title="Paper and cloth", count_label="5 pictures",
         ids=["00000001To00O4SuWVGs8w", "00000001To00O4RIB97vlS", "00000001To00O4T5V7FTm8", "00000001To00O4RHeWBeEw",
              "00000001To00O4S130MFkA"],
         extra_ids=[], read_along="00000001To00O4RE3KzqvK",
         intro=("Figures built from scraps. An artist assembling a collage from vintage photos and red botanical cutouts. A "
                "collage layering two people grooming their hair over an antique map and blue fabric. Tschabalala Self's studio, "
                "where bodies are constructed on the floor from recycled cloth. Three fabric flowers with human faces standing "
                "in a pot. A mixed-media painting of figures on a pink sofa, pencil lines loose, paint dripping. Read alongside: "
                "Paul Éluard and Max Ernst's 1922 book, the proto-surrealist collaboration that helped make collage a language.")),
    dict(eyebrow="Pictures · four", title="Building a world", count_label="6 pictures",
         ids=["00000001To00O4RbX9BRkc", "00000001To00O4RbX8YBAQ", "00000001To00O4RbX8wYb6", "00000001To00O4RbX85SRq",
              "00000001To00O4SQkphZPG"],
         extra_ids=["00000001To00O41QHoEdCU"], read_along="00000001To00O4SN2As9qM",
         intro=("Children of Blood and Bone exists twice this week: as a Hollywood trailer and as handmade-looking pages. Three "
                "saves show the Maji clan symbols, emblems with dot patterns, deities, and descriptions. One shows the Opisa realm "
                "mapped in blue ink with red-labeled cities. The trailer post ties them to the screen version, opening January 15. "
                "One same-vibe save reaches back to July: the boxed set of the source novels, sitting under the maps it explains. "
                "Read alongside: the trailer breakdown covering Gina Prince-Bythewood's adaptation.")),
    dict(eyebrow="Pictures · five", title="Costume on the shore", count_label="3 pictures",
         ids=["00000001To00O4Szs8k2wo", "00000001To00O4SzrUeq8U", "00000001To00O4SxdZOKCQ"],
         extra_ids=[], read_along=None,
         intro=("Two photographs from the same beach shoot: a figure in a flowing black pleated robe with a circular cutout "
                "walking the shoreline, and a model in white feathers with peacock and pheasant plumes against turquoise water. "
                "A behind-the-scenes clip shows how the white look came together in the studio before it ever touched sand.")),
    dict(eyebrow="Pictures · six", title="How abstraction is taught", count_label="4 pictures",
         ids=["00000001To00O4RHgaEUmI", "00000001To00O4RaEbHRQY"],
         extra_ids=["00000001To00O4kRQNpI5i", "00000001To00O2Ar4253UI"], read_along=None,
         intro=("An eight-panel grid where a cow is drawn progressively into geometric forms until it becomes a Mondrian. Next "
                "to it, ten abstract artists on camera explaining what abstraction does. Two same-vibe saves from earlier months "
                "supply the lineage: Ellsworth Kelly's 1954 sketchbook and the appendix drawings from Kandinsky's Point and Line "
                "to Plane, the 1926 textbook that tried to turn abstraction into grammar.")),
]

STORIES = [
    dict(eyebrow="Reading · top story", title="Who made this?", count_label="6 items",
         ids=["00000001To00O4S8n7ORd6", "00000001To00O4S8boEOdO", "00000001To00O4RFSHwad2", "00000001To00O4S4UCAWAw",
              "00000001To00O4RfImBO9i", "00000001To00O4Rvq6au64"],
         intro=("The week's central argument, and it is about authorship. Authors facing false AI accusations now defend "
                "themselves with paper trail tools, and the piece asks whether that is enough. The biggest AI literature "
                "scandal of the year, a Prix Goncourt disqualification, gets a second look through the Black writers it echoes. "
                "An office regulator calls AI misuse close to impossible to assess in university coursework. AI agents curated "
                "and printed their own art magazine, B-SIDE, at Paris Photo. One artist, limited by disability from making new "
                "work, released all his project files under Creative Commons for humans and machines to remix. And a developer "
                "shows Claude quietly figuring out that tldraw copies shapes as compressed JSON, writing its own Python encoder, "
                "and drawing a 1,410-shape watercolor map no human touched.")),
    dict(eyebrow="Reading · theme one", title="The Jensen shock", count_label="3 items",
         ids=["00000001To00O4RJngd4qI", "00000001To00O4SpzZccmI", "00000001To00O4SOBlpKk8"],
         intro=("Jensen Huang resigned as NVIDIA's CEO, effective immediately, after reports of extramarital relationships "
                "including one with a suspected intelligence operative. NVIDIA announced the transition itself. The coverage "
                "turns to whether the AI boom keeps its momentum in the post-Jensen era, with rival chips waiting. The week "
                "watched the person who was the face of the boom leave the stage.")),
    dict(eyebrow="Reading · theme two", title="Black creative legacy", count_label="7 items",
         ids=["00000001To00O4SSByXp60", "00000001To00O4RJawvUn6", "00000001To00O4SSgPG7Hq", "00000001To00O4S0Jp2yHK",
              "00000001To00O4QOlyHgWc", "00000001To00O4QKpYhm4o", "00000001To00O4Ru1V2JVu"],
         intro=("The Basquiat documentary, already a Tribeca winner, lands a Netflix release date. Soul Patrol tells the story "
                "of the army's first all-Black Long-Range Reconnaissance Patrol in Vietnam, teenage soldiers in six-man teams. "
                "Scott Colom becomes Mississippi's next US senator, the state's first Black senator since Reconstruction, in the "
                "same newsletter that records a major donation to Morris Brown. Arthur Jafa, winning at the Art Basel Awards, "
                "talks about art's job in volatile times. Zanele Muholi sits for a one-on-one on photographing Black LGBTQIA+ "
                "life. Reggie Burrows Hodges, who came to painting in his forties from tennis coaching and reggae, gets a "
                "profile. Mildred Thompson, rejected by New York dealers in the sixties, rebuilt her career in Germany and "
                "painted the invisible.")),
    dict(eyebrow="Reading · theme three", title="Who pays for art?", count_label="5 items",
         ids=["00000001To00O4SSAW8PjW", "00000001To00O4S4Z5bWEg", "00000001To00O4RukOHs9q", "00000001To00O4RFyXkU2k",
              "00000001To00O4RJ64yI8M"],
         intro=("The Phillips Collection gets its largest individual gift ever, ten million dollars. Ted Turner's Western art "
                "heads to Christie's, twenty million, with Bierstadt's Yosemite as the crown. The Art Basel survey finds "
                "collectors split between showing and hiding what they own. Art schools are closing while tuition climbs, and "
                "the piece on their impossible economics names the structural cause. And an MBA course at USC will teach the "
                "business of Beyoncé for sixteen weeks.")),
]

pics, textcards, used = 0, 0, set()

def place(o, extra_note=None):
    global pics, textcards
    oid = o.get("id")
    if oid in used: return None
    used.add(oid)
    img = resolve_image(o)
    if img: pics += 1
    else: textcards += 1
    return card_html(o, img, extra_note)

sections_html = []
for sec in SECTIONS:
    parts = []
    for oid in sec["ids"]:
        o = by_id.get(oid) or get_object(oid)
        if o is None: continue
        c = place(o)
        if c: parts.append(c)
    for oid in sec["extra_ids"]:
        o = get_object(oid)
        if o is None: continue
        c = place(o, "Found by same-vibe from this week.")
        if c: parts.append(c)
    ra = ""
    if sec.get("read_along"):
        o = by_id.get(sec["read_along"]) or get_object(sec["read_along"])
        if o:
            url = o.get("source", {}).get("url", "") or mm_link(o.get("id",""))
            ra = (f'<div class="readalong">Read alongside: '
                  f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(clean(o.get("title")))}</a></div>')
    sections_html.append(f'''
<section class="story">
  <div class="eyebrow">{esc(sec["eyebrow"])} · {esc(sec["count_label"])}</div>
  <h2>{esc(sec["title"])}</h2>
  <p class="intro">{esc(sec["intro"])}</p>
  <div class="grid">{"".join(parts)}</div>
  {ra}
</section>''')

stories_html = []
for sec in STORIES:
    parts = []
    for oid in sec["ids"]:
        o = by_id.get(oid) or get_object(oid)
        if o is None: continue
        c = place(o)
        if c: parts.append(c)
    stories_html.append(f'''
<section class="story">
  <div class="eyebrow">{esc(sec["eyebrow"])} · {esc(sec["count_label"])}</div>
  <h2>{esc(sec["title"])}</h2>
  <p class="intro">{esc(sec["intro"])}</p>
  <div class="grid">{"".join(parts)}</div>
</section>''')

placed = len(used)
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>One Piece of MyMind · Issue 2</title>
<style>
  :root {{ --bg:#060505; --red:#e5322d; --red-deep:#cf2d27; --red-dim:#9c201b; --red-line:#571311; }}
  * {{ box-sizing:border-box; print-color-adjust:exact; -webkit-print-color-adjust:exact; }}
  html {{ background:var(--bg); }}
  body {{ margin:0; background:var(--bg); color:var(--red);
         font-family:Georgia,'Times New Roman',serif; line-height:1.5; }}
  .page {{ max-width:1240px; margin:0 auto; padding:46px 36px 90px; }}
  header.masthead {{ border-bottom:1px solid var(--red-line); padding:10px 0 30px; }}
  .kicker {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:11px; letter-spacing:3px;
             text-transform:uppercase; color:var(--red-dim); margin:0 0 16px; }}
  h1 {{ font-size:72px; line-height:1.0; margin:0 0 14px; font-weight:700; letter-spacing:-1px; color:var(--red); }}
  .deck {{ font-size:18px; color:var(--red-deep); margin:0; font-style:italic; }}
  section.story {{ margin-top:80px; }}
  .eyebrow {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:11px; letter-spacing:2.6px;
              text-transform:uppercase; color:var(--red-dim); font-weight:700; }}
  h2 {{ font-size:42px; line-height:1.05; margin:10px 0 20px; color:var(--red); }}
  .intro {{ font-size:18px; max-width:80ch; margin:0 0 32px; color:var(--red); }}
  .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:36px 26px; }}
  @media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
  @media (max-width:600px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ margin:0; display:flex; flex-direction:column; }}
  .card img {{ width:100%; aspect-ratio:4/3; object-fit:cover; display:block;
               filter:grayscale(14%) contrast(1.04); border:1px solid var(--red-line); }}
  .card .cap {{ display:flex; flex-direction:column; gap:7px; padding-top:12px; }}
  .card.noimg {{ border-left:2px solid var(--red-line); padding:2px 0 2px 16px; justify-content:center; }}
  .cap .t {{ font-size:16px; font-weight:700; color:var(--red); text-decoration:none; line-height:1.3; }}
  .cap .t:hover {{ text-decoration:underline; }}
  .cap .s {{ font-size:13.5px; color:var(--red-deep); }}
  .cap .d {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:10.5px;
             letter-spacing:1.6px; text-transform:uppercase; color:var(--red-dim); }}
  .readalong {{ margin-top:18px; font-size:14.5px; color:var(--red-deep); border-top:1px solid var(--red-line);
                padding-top:12px; }}
  .readalong a {{ color:var(--red); font-weight:700; }}
  a {{ color:var(--red); }}
  ::selection {{ background:var(--red); color:#000; }}
  footer {{ margin-top:90px; border-top:1px solid var(--red-line); padding-top:18px;
            font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; color:var(--red-dim);
            letter-spacing:0.4px; }}
  @media print {{
    html, body {{ background:#000; }}
    .page {{ max-width:none; padding:0 8mm; }}
    .card {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <p class="kicker">Issue No. 2 &nbsp;·&nbsp; Week of November 7 – 14, 2026 &nbsp;·&nbsp; From your MyMind saves</p>
    <h1>One Piece of MyMind</h1>
    <p class="deck">One week of your saves, arranged into six picture themes and four reading stories. Nothing repeats, and nothing is here by accident.</p>
  </header>
  {"".join(sections_html)}

  <section class="story">
    <div class="eyebrow">The reading · four stories</div>
    <h2>The reading</h2>
    <p class="intro">The written side of the week: the articles and videos, grouped by what they share.</p>
    {"".join(stories_html)}
  </section>

  <footer>
    Built from {len(objs)} MyMind saves for the week &nbsp;·&nbsp; {pics} pictures and {textcards} text entries across six picture
    themes and four reading stories, {placed} saves placed &nbsp;·&nbsp; pictures come from MyMind's own stored images, each page's
    own preview, and same-vibe saves from earlier months &nbsp;·&nbsp; <a href="/" style="color:var(--red-dim)">Issue 1</a> lives here too.
  </footer>
</div>
</body>
</html>'''

HTML_PATH.write_text(html, encoding="utf-8")
print(f"HTML written: {HTML_PATH} ({HTML_PATH.stat().st_size} bytes)")
print(f"pictures: {pics} | text entries: {textcards} | placed saves: {placed} of {len(objs)}")
