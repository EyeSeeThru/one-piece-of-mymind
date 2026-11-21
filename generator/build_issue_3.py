#!/usr/bin/env python3
"""Build 'One Piece of MyMind' Issue 3 — dark gallery, curated themes, no dumps/dupes/placeholders."""
import json, os, re, subprocess, html as htmlmod
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request

HOME = os.path.expanduser("~")
VAULT = f"{HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/EyeOS/Second Brain/Bookmarks/One-Piece-of-MyMind"
ASSETS = Path(VAULT) / "assets"
MYMIND = f"{HOME}/bin/mymind"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML_PATH = Path(VAULT) / "one-piece-of-mymind-issue-3-gallery.html"
PDF_PATH = Path(VAULT) / "one-piece-of-mymind-issue-3-gallery.pdf"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
BOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

ASSETS.mkdir(parents=True, exist_ok=True)
objs = json.load(open(os.path.expanduser("~/.hermes/cache/scratch/opomm-build/week.json")))
# TAG EXCLUSIONS (EST 2026-11-14): private/noshare/mine/nsfw never featured or named
BAD_TAGS = {"private", "noshare", "mine", "nsfw"}
def flagged(o):
    t = o.get("tags") or []
    names = {str((x.get("name") if isinstance(x, dict) else x) or "").lower() for x in t}
    return bool(names & BAD_TAGS)
objs = [o for o in objs if not flagged(o)]

# Never repeat an item already shipped in issue 1 or 2
used_before = {l.strip() for l in open(os.path.expanduser("~/.hermes/cache/scratch/opomm-build/used_ids.txt")) if l.strip()}
objs = [o for o in objs if o.get("id") not in used_before]

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

# Multi-photo saves from one x.com post are distinct images (photo/1, /2, ...) and
# stay as separate cards, matching issue 2. Duplicate page saves collapse in place().
by_id = {o.get("id"): o for o in objs}

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
    shot = f"/tmp/embed3_{oid}.png"
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
    dict(eyebrow="Pictures · one", title="Words on paper", count_label="6 pictures",
         ids=["00000001To00O4VlnaLDyw", "00000001To00O4VlnzyaAw", "00000001To00O4VlnLJKIU",
              "00000001To00O4VlnXcIFO", "00000001To00O4VbcZpNmw", "00000001To00O4USA4R6KI"],
         extra_ids=[], read_along=None,
         intro=("Four pages of Brecht poems photographed from one post: a warning about judging art by the man who "
                "made it, instructions on working with particular gestures, a war poem out of Altona, and a satire "
                "of an abstemious chancellor. Beside them, a line from Martha Gellhorn's letters about no longer "
                "having it in her to struggle, and a two-panel quote from Rohmer's A Summer's Tale, spoken on a "
                "harbor bench. These are the week's saves that are mostly printed words.")),
    dict(eyebrow="Pictures · two", title="Strange objects", count_label="6 pictures",
         ids=["00000001To00O4VbbUTcha", "00000001To00O4UeE843gQ", "00000001To00O4UxJHYYeY",
              "00000001To00O4UJB7sESs", "00000001To00O4VD5CuPWo", "00000001To00O4TYWKprC8"],
         extra_ids=[], read_along=None,
         intro=("The week's strangest visuals. A sofa shaped like a snake in front of a floral still life, parked "
                "in a dark paneled room. A 3D figure under a sky of orbiting eyes. A child's crayon drawing of "
                "Carnage towering over Spider-Man. A Spanish shirt maker folding shirts into faces for its "
                "campaign. A layered collage of a Bulls dunk over Knicks defenders. And the cardboard model behind "
                "an animated short, shown mid-build.")),
    dict(eyebrow="Pictures · three", title="Great advice for shitty people", count_label="3 pictures",
         ids=["00000001To00O4U4oc4OaI", "00000001To00O4VzBvtXqw", "00000001To00O4VLMb9twA"],
         extra_ids=[], read_along=None,
         intro=("The same satirical advice series, saved three separate times in one week. Handwritten cards "
                "proposing terrible etiquette for gatherings, conversation, and the writing of thank-you notes. "
                "The series keeps resurfacing because each joke lands on a real manner someone actually has.")),
    dict(eyebrow="Pictures · four", title="What they wore", count_label="4 pictures",
         ids=["00000001To00O4U7qd6E9i", "00000001To00O4UxQK55Ty", "00000001To00O4UPPLKKe4",
              "00000001To00O4T8LRZdfy"],
         extra_ids=[], read_along="00000001To00O4UPMBOehG",
         intro=("Clothes from four directions. Albert's fall/winter 2026 menswear, all belted shawl-collar coats "
                "and cable knits. E.N.D. Design Lab's lookbook for its workman's jacket and rugby shirt. Peggy's "
                "Gilded Age wedding gown, lace with a tiered ruffled skirt, worn for the TV wedding that jumped "
                "the broom on HBO. And a sixteen-second tutorial on the perfect windsor knot, saved from X. Read "
                "alongside: the piece on why viewers are still not over Peggy's wedding.")),
    dict(eyebrow="Pictures · five", title="Instructions", count_label="3 pictures",
         ids=["00000001To00O4U4oUJBCw", "00000001To00O4U0tWyrUk", "00000001To00O4VgBLx1Sw"],
         extra_ids=[], read_along=None,
         intro=("How-to images saved without a word of commentary. A drawing lesson on training your hand to know "
                "the body's proportions. A small orange diagram on shifting focus between past, present, and "
                "future. And a comic about overwatering a daisy, which is the same lesson from the other "
                "direction: too much care kills.")),
]

STORIES = [
    dict(eyebrow="Reading · top story", title="The local AI stack grows up", count_label="6 items",
         ids=["00000001To00O4T8Gdv0oo", "00000001To00O4U0UbK7zG", "00000001To00O4UfE5lX2M",
              "00000001To00O4UT7vayRy", "00000001To00O4U4bwkAqA", "00000001To00O4UQ2rr31u"],
         intro=("The biggest week in months for the tools you run yourself. llama.cpp and ggml both shipped "
                "version 1.0.0, almost three and a half years in, a stability promise for the local model "
                "ecosystem. Qwen 4 arrived the same week. Around them the practice matured: a pattern for "
                "running coding agents against external sandboxes, so the boundary is enforced by the machine "
                "rather than the model's judgment. A report of one software factory that built thirty C# "
                "libraries, about 1.9 million lines, in six weeks. A review of Fable 5.2, the most expensive "
                "model per token, and what agent teams do beyond the model. And a warning that token fraud, "
                "from resold free trials to laundered promo codes, is already costing AI providers real money.")),
    dict(eyebrow="Reading · theme one", title="Records at the auction house", count_label="5 items",
         ids=["00000001To00O4UpYiabCg", "00000001To00O4VktmbWWA", "00000001To00O4Vkt51ySY",
              "00000001To00O4UsykIbxS", "00000001To00O4UpWl5Vks"],
         intro=("Two records in one week at Sotheby's. Yayoi Kusama's Infinity Net painting brought 15.1 million "
                "dollars. A 1945 Aaron Douglas painting of Harriet Tubman with broken shackles sold for a record "
                "14.5 million, consigned by Bennett College, and Sotheby's shared the canvas itself. Christie's "
                "follows with rare Louis Vuitton artist collaboration bags by Murakami, Kusama, and Gehry. Under "
                "all of it, the Guardian retraces Peggy Guggenheim's scheme of buying a painting a day, the "
                "spending habit that built a collection the auction market still echoes.")),
    dict(eyebrow="Reading · theme two", title="Black creativity, on the record", count_label="5 items",
         ids=["00000001To00O4VhJTLL4Q", "00000001To00O4UOFGrTgs", "00000001To00O4USJHAcqk",
              "00000001To00O4UwNbXJHG", "00000001To00O4UqlOFW1y"],
         intro=("We're Still Here gathers quilts by fifteen contemporary Black artists, curated by Carolyn "
                "Mazloomi, quilts that carry social issues in fabric. James Barnor's studio portraits, split "
                "between Accra and London, get a show that reframes the history of modern photography. Kwame "
                "Dawes talks about chronicling the sentiment of his time, poetry as the record itself. Beyoncé "
                "reaches her 100th Grammy nomination, more than any artist. And Maryland gets sued for six "
                "billion dollars over the underfunding of its historically Black university, the bill for the "
                "other side of the ledger.")),
    dict(eyebrow="Reading · theme three", title="Your data, their rules", count_label="5 items",
         ids=["00000001To00O4UvV8TDFe", "00000001To00O4UpT7sLdK", "00000001To00O4Vl0OpZoA",
              "00000001To00O4VkDb1BBK", "00000001To00O4UxDLmUuY"],
         intro=("A week of quiet policy changes and loud failures. Google will keep Gemini chats for two months "
                "instead of 72 hours, even with history turned off. A massive website malware attack targeted "
                "iPhones and iPads. Hackers leaked customer data claimed to come from Visa, Mastercard, and "
                "JPMorgan. The FCC approved a rule letting prisons jam cellphone signals. And one roundup chart "
                "counts the major IT outages of six straight days: airlines, banks, and agencies, all in a "
                "single stretch.")),
    dict(eyebrow="Reading · theme four", title="Around DC", count_label="5 items",
         ids=["00000001To00O4UsAqzfYQ", "00000001To00O4UwUNeFYQ", "00000001To00O4Vho8vj5S",
              "00000001To00O4Vz0FSXJe", "00000001To00O4VCG6bMqI"],
         intro=("The local list. Winternational brings the embassies to one hall at the Ronald Reagan Building "
                "on December 8. East City Art's roundup covers gallery openings and exhibitions through November "
                "29. A Native American heritage lineup brings indigenous films and an art market to the city and "
                "online. Ten bars with live music, jazz included. And Step Back, Doors Closing, a drama set on "
                "the DC subway about commuting and social distance, joins the watchlist.")),
    dict(eyebrow="Reading · theme five", title="Franchises fight back", count_label="4 items",
         ids=["00000001To00O4UsxVCBSo", "00000001To00O4VhxCSSIM", "00000001To00O4Uy7ThAVq",
              "00000001To00O4UQIifH4Q"],
         intro=("Star Wars turns 50 and the merchandise machine runs at full power: LEGO anniversary sets on one "
                "side, Kith and Hasbro teasing a Sith collection of figures and apparel on the other. Open "
                "Culture looks back at the gloriously cheap 1970s Italian knockoffs that Star Wars inspired, "
                "unofficial space operas on real film stocks. And the Wachowskis move to reclaim The Matrix "
                "itself, exercising copyright termination against the studio. Ownership of a franchise, it "
                "turns out, is always being renegotiated.")),
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
        if o is None:
            print(f"MISSING id in section '{sec['title']}': {oid}")
            continue
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
        if o is None:
            print(f"MISSING id in story '{sec['title']}': {oid}")
            continue
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
<title>One Piece of MyMind · Issue 3</title>
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
    <p class="kicker">Issue No. 3 &nbsp;·&nbsp; Week of November 14 – 20, 2026 &nbsp;·&nbsp; From your MyMind saves</p>
    <h1>One Piece of MyMind</h1>
    <p class="deck">One week of your saves, arranged into five picture themes and six reading stories. Nothing repeats, and nothing is here by accident.</p>
  </header>
  {"".join(sections_html)}

  <section class="story">
    <div class="eyebrow">The reading · six stories</div>
    <h2>The reading</h2>
    <p class="intro">The written side of the week: the articles and videos, grouped by what they share.</p>
    {"".join(stories_html)}
  </section>

  <footer>
    Built from {len(objs)} MyMind saves for the week &nbsp;·&nbsp; {pics} pictures and {textcards} text entries across five picture
    themes and six reading stories, {placed} saves placed &nbsp;·&nbsp; pictures come from MyMind's own stored images and each page's
    own preview &nbsp;·&nbsp; <a href="/" style="color:var(--red-dim)">the archive</a> holds every issue.
  </footer>
</div>
</body>
</html>'''

HTML_PATH.write_text(html, encoding="utf-8")
print(f"HTML written: {HTML_PATH} ({HTML_PATH.stat().st_size} bytes)")
print(f"pictures: {pics} | text entries: {textcards} | placed saves: {placed} of {len(objs)}")

subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={PDF_PATH}", f"file://{HTML_PATH}"], capture_output=True, timeout=180)
print(f"PDF: {PDF_PATH} ({PDF_PATH.stat().st_size if PDF_PATH.exists() else 0} bytes)")
