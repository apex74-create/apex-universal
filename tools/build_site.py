#!/usr/bin/env python3
"""Build the Apex Universal third set from the fetched depot shelf.

Reads site/catalog.json (the depot's own data) + site/faces/*.html (live
shelf bytes) and produces the complete static site in site/:
- per-face PWA manifests + PWA injection into each face copy
- faces/sw.js + root sw.js (offline containers)
- icons (PIL scope-reticle)
- index.html storefront (cards generated from the catalogue, nothing invented)
- test.html cross-container test protocol + PROTOCOL.md
- CNAME, .nojekyll, README.md
Prints a build summary only.
"""
import json, os, re, sys

ROOT = os.path.expanduser("~/workspace/universal-storefront-build/site")
DOMAIN = "universal.apex-airsolutions.com"
BUILD_DATE = "2026-11-20"

cat = json.load(open(os.path.join(ROOT, "catalog.json")))
faces = cat["faces"]
assert len(faces) == 56, len(faces)

# ---------- icons ----------
from PIL import Image, ImageDraw
def icon(size, path, pad_ratio=0.0):
    S = 1024
    img = Image.new("RGB", (S, S), (5, 12, 8))
    d = ImageDraw.Draw(img)
    pad = int(S * pad_ratio)
    # rounded plate
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=int(S * 0.18), fill=(7, 20, 12))
    cx = cy = S // 2
    green = (57, 255, 106)
    dim = (22, 120, 58)
    R = int(S * 0.30)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=green, width=int(S * 0.035))
    R2 = int(S * 0.19)
    d.ellipse([cx - R2, cy - R2, cx + R2, cy + R2], outline=dim, width=int(S * 0.022))
    L = int(S * 0.40)
    w = int(S * 0.030)
    d.line([cx - L, cy, cx - int(S * 0.10), cy], fill=green, width=w)
    d.line([cx + int(S * 0.10), cy, cx + L, cy], fill=green, width=w)
    d.line([cx, cy - L, cx, cy - int(S * 0.10)], fill=green, width=w)
    d.line([cx, cy + int(S * 0.10), cx, cy + L], fill=green, width=w)
    r = int(S * 0.045)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=green)
    img = img.resize((size, size), Image.LANCZOS)
    img.save(path)
os.makedirs(os.path.join(ROOT, "icons"), exist_ok=True)
icon(192, os.path.join(ROOT, "icons", "icon-192.png"))
icon(512, os.path.join(ROOT, "icons", "icon-512.png"))
icon(512, os.path.join(ROOT, "icons", "icon-maskable-512.png"), pad_ratio=0.10)
icon(180, os.path.join(ROOT, "icons", "apple-touch-icon.png"))

# ---------- service workers ----------
FACES_SW = """// Apex Universal - faces service worker (scope: /faces/)
// Cache-first with background refresh: a face, once opened, relaunches offline.
const CACHE = 'apex-universal-faces-v1';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k.startsWith('apex-universal-faces-') && k !== CACHE).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;
  e.respondWith(
    caches.open(CACHE).then(cache => cache.match(e.request).then(hit => {
      const net = fetch(e.request).then(res => {
        if (res && res.ok) cache.put(e.request, res.clone());
        return res;
      }).catch(() => hit);
      return hit || net;
    }))
  );
});
"""
ROOT_SW = """// Apex Universal - storefront service worker (scope: /)
// Network-first for pages, cache-first for icons: the store shell opens offline.
const CACHE = 'apex-universal-store-v1';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k.startsWith('apex-universal-store-') && k !== CACHE).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/faces/')) return; // the faces worker owns that scope
  e.respondWith(
    fetch(e.request).then(res => {
      if (res && res.ok) { const c = res.clone(); caches.open(CACHE).then(cache => cache.put(e.request, c)); }
      return res;
    }).catch(() => caches.open(CACHE).then(cache => cache.match(e.request)))
  );
});
"""
with open(os.path.join(ROOT, "faces", "sw.js"), "w") as f: f.write(FACES_SW)
with open(os.path.join(ROOT, "sw.js"), "w") as f: f.write(ROOT_SW)

# ---------- per-face manifests + injection ----------
def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

stats = {"injected": 0, "had_manifest": 0, "had_sw": 0, "no_head": 0, "no_body": 0}
for face in faces:
    slug = face["slug"]
    fpath = os.path.join(ROOT, "faces", slug + ".html")
    html = open(fpath, encoding="utf-8", errors="replace").read()
    short = face["name"].replace("Apex Face — ", "").replace("Apex Face - ", "").strip() or slug
    manifest = {
        "name": face["name"] + " · Apex Universal",
        "short_name": short[:24],
        "description": (face.get("note") or "")[:300],
        "start_url": slug + ".html",
        "scope": "./",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#050807",
        "theme_color": "#07130b",
        "icons": [
            {"src": "../icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "../icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "../icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    with open(os.path.join(ROOT, "faces", slug + ".webmanifest"), "w") as f:
        json.dump(manifest, f, indent=1)
    head_bits = []
    if 'rel="manifest"' not in html and "rel='manifest'" not in html:
        head_bits.append('<link rel="manifest" href="%s.webmanifest">' % slug)
    else:
        stats["had_manifest"] += 1
    head_bits += [
        '<meta name="theme-color" content="#07130b">',
        '<meta name="mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">',
        '<meta name="apple-mobile-web-app-title" content="%s">' % esc(short[:24]),
        '<link rel="apple-touch-icon" href="../icons/apple-touch-icon.png">',
        '<!-- apex-universal-container v1 -->',
    ]
    head_inj = "\n" + "\n".join(head_bits) + "\n"
    m = re.search(r"</head\s*>", html, re.I)
    if m:
        html = html[:m.start()] + head_inj + html[m.start():]
    else:
        stats["no_head"] += 1
        html = head_inj + html
    if "serviceWorker" not in html:
        body_inj = ("\n<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){"
                    "navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>\n")
        m2 = re.search(r"</body\s*>", html, re.I)
        if m2:
            html = html[:m2.start()] + body_inj + html[m2.start():]
        else:
            stats["no_body"] += 1
            html = html + body_inj
    else:
        stats["had_sw"] += 1
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)
    stats["injected"] += 1
print("face injection:", stats)

# store manifest
store_manifest = {
    "name": "Apex Universal — Face Store",
    "short_name": "Apex Universal",
    "description": "The third set: all 56 Apex faces in the house universal container. One address, both platforms.",
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "background_color": "#050807",
    "theme_color": "#07130b",
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
with open(os.path.join(ROOT, "manifest.webmanifest"), "w") as f:
    json.dump(store_manifest, f, indent=1)

with open(os.path.join(ROOT, "CNAME"), "w") as f: f.write(DOMAIN + "\n")
open(os.path.join(ROOT, ".nojekyll"), "w").close()
print("icons, workers, manifests, CNAME written")
json.dump({"faces": len(faces)}, open(os.path.join(ROOT, "build-info.json"), "w"))

# ---------- storefront index.html ----------
CSS = """
:root{--bg:#050807;--panel:#0a120c;--line:#1d3320;--ink:#d8f5dc;--dim:#8fbf97;--grn:#39ff6a;--amber:#ffc857}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
header{padding:28px 18px 10px;max-width:1060px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px;letter-spacing:.04em}h1 .u{color:var(--grn)}
.sub{color:var(--dim);margin:0 0 6px}.addr{color:var(--amber);font-family:ui-monospace,Menlo,Consolas,monospace}
main{max-width:1060px;margin:0 auto;padding:0 18px 40px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0}
.panel h2{font-size:16px;margin:0 0 8px;color:var(--grn)}
.panel p{margin:6px 0}.small{font-size:13px;color:var(--dim)}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:var(--amber);word-break:break-all}
button,.btn{display:inline-block;background:#0e2413;color:var(--grn);border:1px solid var(--grn);border-radius:999px;
padding:7px 14px;font-size:13.5px;cursor:pointer;text-decoration:none;margin:3px 4px 3px 0}
button:hover,.btn:hover{background:#14301a}.btn.apk{border-color:var(--amber);color:var(--amber)}
input[type=search]{width:100%;padding:10px 12px;border-radius:8px;border:1px solid var(--line);background:#07130b;color:var(--ink);font-size:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px 14px}
.card h3{margin:0 0 2px;font-size:15.5px}.card .title{color:var(--dim);font-size:12.5px;margin:0 0 6px}
.price{color:var(--grn);font-weight:700}.status{color:var(--amber);font-size:12px;letter-spacing:.06em}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:11.5px;color:var(--dim);margin:2px 3px 2px 0}
.note{font-size:12.5px;color:var(--dim);margin:7px 0}
footer{max-width:1060px;margin:0 auto;padding:0 18px 34px;color:var(--dim);font-size:12.5px}
a{color:var(--grn)}
"""

def card_html(face):
    slug = face["slug"]
    funcs = "".join('<span class="chip">%s</span>' % esc(x) for x in face.get("functions", []))
    mb = face["apkSizeBytes"] / 1048576.0
    return (
        '<article class="card" data-slug="%s" data-text="%s">'
        "<h3>%s</h3>"
        '<p class="title">%s</p>'
        '<p><span class="price">$%.2f</span> · <span class="status">%s</span></p>'
        "<p>%s</p>"
        '<p class="note">%s</p>'
        '<p><a class="btn" href="faces/%s.html">Open the container</a>'
        '<a class="btn apk" href="https://tinyradr.com%s">Android APK · %.1f MB</a></p>'
        '<p class="small">APK SHA-256 <code>%s</code></p>'
        "</article>"
    ) % (
        slug,
        esc((face["name"] + " " + slug + " " + " ".join(face.get("functions", []))).lower()),
        esc(face["name"]), esc(face.get("title", "")), face["priceUsd"], esc(face.get("status", "")),
        funcs, esc(face.get("note", "")), slug, face["apkPath"], mb, face["apkSha256"],
    )

cards = "\n".join(card_html(f) for f in faces)
index = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Apex Universal — The Third Set · 56 Faces, One Container</title>
<meta name="description" content="All 56 Apex watch faces in the house universal container. One address, both platforms: Android and Apple install from this shelf.">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#07130b">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Apex Universal">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" href="icons/icon-192.png">
<style>%s</style>
</head>
<body>
<header>
<h1>APEX <span class="u">UNIVERSAL</span> — THE THIRD SET</h1>
<p class="sub">All 56 Apex faces in the house universal container. One address, both platforms.</p>
<p class="addr">%s</p>
</header>
<main>
<section class="panel" id="platformPanel">
<h2 id="platformTitle">Your platform</h2>
<p id="platformBody">Reading your platform…</p>
<p><button id="storeInstall" hidden>Install this store</button>
<a class="btn" href="test.html">Cross-container test protocol</a>
<a class="btn" href="https://tinyradr.com/depot">The depot shelf (tinyradr.com)</a></p>
</section>
<section class="panel">
<h2>What the universal container is — stated plain</h2>
<p>Each face is one file. On this shelf that file is delivered as an <strong>installable web app</strong>:
it installs to the home screen, opens full-screen with no browser bar, and after the first load it
relaunches offline. The same face file rides inside the depot's Android APK — the native container —
so Android carries two containers for every face and Apple carries the web container, all from this one address.</p>
<p>What it is not: on Apple it is not a native binary. Apple's rules give the web container as the
store-free install — no App Store, no account, no third party holding this shelf. That is the
Never-Again Storefront Law working as designed: the storefront sits in the house's hands.</p>
<p class="small">Checkout, in the depot's own words: %s</p>
</section>
<p><input type="search" id="filter" placeholder="Filter 56 faces by name or function…" aria-label="Filter faces"></p>
<section class="grid" id="grid">
%s
</section>
</main>
<footer>
<p>Catalogue data: the tinyradr.com depot catalog, carried verbatim — names, prices, APK hashes and sizes
are the depot's own record, nothing re-typed. Face files on this shelf are the live shelf's bytes at build
(%s). The universal set is a third set beside the depot's Android set and the Apple web plane.</p>
<p>Apex Air Solutions · <a href="https://tinyradr.com">tinyradr.com</a> · Orders: sales@apexairsolutions.com</p>
</footer>
<script>
(function(){
  var ua = navigator.userAgent || '';
  var isAndroid = /Android/i.test(ua);
  var isIOS = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var title = document.getElementById('platformTitle'), body = document.getElementById('platformBody');
  if (isAndroid) {
    title.textContent = 'Your platform: Android';
    body.innerHTML = 'Open any face, then install it from your browser menu (Install app) or the prompt — ' +
      'it lands on your home screen as the universal container. Prefer the native container? Every card also ' +
      'carries the depot Android APK with its SHA-256 printed, so you can scan-verify the download before you install it.';
  } else if (isIOS) {
    title.textContent = 'Your platform: Apple';
    body.innerHTML = 'Open any face in Safari, tap <strong>Share</strong>, then <strong>Add to Home Screen</strong>. ' +
      'The face installs as the universal web container: full-screen, its own icon, offline after the first load. ' +
      'Apple offers no install prompt, so the two taps are the whole road — no App Store anywhere in it.';
  } else {
    title.textContent = 'Your platform: desktop';
    body.innerHTML = 'You are reading the shelf from a computer. Every face opens and runs right here; ' +
      'on a phone, Android installs from the browser menu and Apple installs from Share → Add to Home Screen.';
  }
  var deferred = null, btn = document.getElementById('storeInstall');
  window.addEventListener('beforeinstallprompt', function(e){ e.preventDefault(); deferred = e; btn.hidden = false; });
  btn.addEventListener('click', function(){ if (deferred) { deferred.prompt(); deferred = null; btn.hidden = true; } });
  if ('serviceWorker' in navigator) { window.addEventListener('load', function(){ navigator.serviceWorker.register('sw.js').catch(function(){}); }); }
  var filter = document.getElementById('filter');
  filter.addEventListener('input', function(){
    var q = filter.value.toLowerCase(), cards = document.querySelectorAll('.card');
    for (var i = 0; i < cards.length; i++) { cards[i].style.display = cards[i].getAttribute('data-text').indexOf(q) >= 0 ? '' : 'none'; }
  });
})();
</script>
</body>
</html>
""" % (CSS, DOMAIN, esc(cat["checkoutState"]), cards, BUILD_DATE)
with open(os.path.join(ROOT, "index.html"), "w") as f: f.write(index)
print("index.html written, cards:", len(faces))

# ---------- test protocol page + PROTOCOL.md ----------
rows = "\n".join(
    '<tr><td>%d</td><td>%s</td><td>%s</td><td class="c">☐</td><td class="c">☐</td><td class="c">☐</td><td class="c">☐</td><td></td></tr>'
    % (i + 1, esc(f["name"]), esc(f["slug"]), )
    for i, f in enumerate(faces))
test = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cross-Container Test Protocol — Apex Universal</title>
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#07130b">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<style>%s
table{border-collapse:collapse;width:100%%;font-size:13px}td,th{border:1px solid var(--line);padding:5px 7px;text-align:left}
th{color:var(--grn)}td.c{text-align:center;font-size:15px}ol li{margin:5px 0}
</style>
</head>
<body>
<header><h1>CROSS-CONTAINER <span class="u">TEST PROTOCOL</span></h1>
<p class="sub">The third set gets proven the way the house proves everything: on real handsets, both platforms, face by face.</p>
<p class="addr">%s</p></header>
<main>
<section class="panel"><h2>The testers</h2>
<p><strong>Android seat — the owner</strong>, on his handset. <strong>Apple seat — Kevin</strong>, full operator
licence, on his Apple device. Same address, same shelf, same faces. Each tester works the full 56.</p></section>
<section class="panel"><h2>Android run (owner)</h2><ol>
<li>Open <strong>%s</strong> in Chrome. Confirm the shelf reads 56 faces.</li>
<li>Open a face. Install it: browser menu → <em>Install app</em> (or accept the prompt). Confirm the icon lands on the home screen.</li>
<li>Launch from the icon. PASS needs: full-screen, no browser bar; the clock live and ticking; the face's own function answering.</li>
<li><strong>Scan step:</strong> on the same card, download the depot Android APK. Verify the file's SHA-256 against the hash printed on the card before installing (any hash-checker app). Install the APK and run it — the same face in the native container.</li>
<li>Airplane mode on. Relaunch the web container from its icon: it must open and run offline (the service worker carries it).</li>
<li>Grade the face in the table: Container install · Runs · Offline · APK scan+run. Any failure gets its symptom written in Notes, in plain words.</li>
</ol></section>
<section class="panel"><h2>Apple run (Kevin)</h2><ol>
<li>Open <strong>%s</strong> in Safari. Confirm the shelf reads 56 faces.</li>
<li>Open a face. Tap <strong>Share → Add to Home Screen</strong>. Confirm the icon lands.</li>
<li>Launch from the icon. PASS needs: full-screen standalone, no Safari bar; the clock live; the face's own function answering.</li>
<li>Airplane mode on. Relaunch from the icon: it must open and run offline.</li>
<li>Grade the face in the table. Apple has no APK column — the web container is Apple's container, and that is the point of the set.</li>
</ol></section>
<section class="panel"><h2>What PASS means, per face</h2>
<p>Installs from this one address · launches standalone · clock live · its listed function responds ·
offline relaunch works · layout holds at the device size, nothing overlapping, nothing cut.
A face that fails any leg is a FAIL with the symptom named — never a quiet pass.</p>
<p class="small">Known platform truth, stated before the test so nobody grades it as a defect: iOS gives no
install prompt (the two Share taps are the road), and faces whose functions read device bridges
(Wi-Fi scan class) answer through the native container on Android; in a web container they read
their honest NO MEASURE, exactly as they do on the depot shelf.</p></section>
<section class="panel"><h2>The 56 — grade sheet</h2>
<table><tr><th>#</th><th>Face</th><th>Slug</th><th>Install</th><th>Runs</th><th>Offline</th><th>APK (Android)</th><th>Notes</th></tr>
%s
</table></section>
</main>
<footer><p><a href="index.html">Back to the shelf</a> · Apex Air Solutions · The protocol also lives in the repo as PROTOCOL.md.</p></footer>
<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>
</body></html>
""" % (CSS, DOMAIN, DOMAIN, DOMAIN, rows)
with open(os.path.join(ROOT, "test.html"), "w") as f: f.write(test)

proto_md = ["# Cross-Container Test Protocol — Apex Universal (Third Set)", "",
            "Address: https://%s" % DOMAIN, "",
            "Testers: the owner on Android (his handset); Kevin on Apple (full operator licence test seat).",
            "Both work the full 56 faces from the one address.", "",
            "## Android run", "",
            "1. Open the address in Chrome; confirm the shelf reads 56 faces.",
            "2. Open a face; install via menu → Install app (or the prompt); confirm the home-screen icon.",
            "3. Launch from the icon: full-screen, clock live, the face's function answering.",
            "4. Scan step: download the depot APK from the same card; verify its SHA-256 against the printed hash; install; run — the same face in the native container.",
            "5. Airplane mode: relaunch the web container; it must open and run offline.",
            "6. Grade per face: Install · Runs · Offline · APK. Failures get the symptom in plain words.", "",
            "## Apple run", "",
            "1. Open the address in Safari; confirm 56 faces.",
            "2. Open a face; Share → Add to Home Screen; confirm the icon.",
            "3. Launch from the icon: standalone full-screen, clock live, function answering.",
            "4. Airplane mode: relaunch; must open and run offline.",
            "5. Grade per face. No APK column on Apple — the web container is Apple's container.", "",
            "## PASS, per face", "",
            "Installs from the one address · launches standalone · clock live · listed function responds · offline relaunch works · layout holds at device size. Any failed leg is a FAIL with the symptom named.", "",
            "## The 56", ""]
for i, f in enumerate(faces):
    proto_md.append("%d. %s (`%s`) — Install ☐ · Runs ☐ · Offline ☐ · APK ☐ · Notes:" % (i + 1, f["name"], f["slug"]))
with open(os.path.join(ROOT, "PROTOCOL.md"), "w") as f: f.write("\n".join(proto_md) + "\n")

readme = """# Apex Universal — The Third Set

The house universal container storefront: all 56 Apex faces at one address,
**%s**, installable on Android and Apple from the same shelf.

- `index.html` — the sales assembly. Cards are generated from the depot's own
  catalog (`catalog.json`, carried verbatim from tinyradr.com/depot): names,
  prices, APK hashes and sizes are the depot's record, nothing re-typed.
- `faces/` — the 56 face files (live shelf bytes at build, %s), each carrying
  its own web app manifest (`<slug>.webmanifest`) so it installs as the
  universal web container: home-screen icon, full-screen, offline after first
  load via `faces/sw.js`.
- Android also gets the native container: every card links the depot APK on
  tinyradr.com with its SHA-256 printed for scan-verification.
- Apple gets the web container — the store-free install Apple's rules allow.
  No App Store, no account: the Never-Again Storefront Law in working form.
- `test.html` / `PROTOCOL.md` — the cross-container test protocol: the owner
  runs Android, Kevin runs Apple, all 56 faces graded per the sheet.
- Rebuild: `fetch_faces.py` pulls the live shelf (and verifies each face's
  SHA-256 against the catalogue), `build_site.py` regenerates this site.
  Build tooling lives in the house workspace (universal-storefront-build).
""" % (DOMAIN, BUILD_DATE)
with open(os.path.join(ROOT, "README.md"), "w") as f: f.write(readme)
print("test.html, PROTOCOL.md, README.md written")
