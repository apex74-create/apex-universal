#!/usr/bin/env python3
"""Fetch the 56 depot faces + their relative assets from the live shelf
(tinyradr.com, published from tinyradr main 58619d2b) into the third-set
build tree. Verifies every face file's SHA-256 against the depot
catalogue's own faceSha256. Prints a summary only."""
import hashlib, json, os, re, subprocess, sys, urllib.parse

BASE = "https://tinyradr.com"
ROOT = os.path.expanduser("~/workspace/universal-storefront-build/site")
os.makedirs(os.path.join(ROOT, "faces"), exist_ok=True)

def get(url):
    out = subprocess.run(["curl", "-fsSL", "--retry", "3", "--retry-delay", "1",
                          "-A", "apex-universal-fetch/1.0", url],
                         capture_output=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError("curl failed for %s: %s" % (url, out.stderr.decode()[:200]))
    return out.stdout

cat = json.loads(get(BASE + "/depot/catalog.json"))
faces = cat["faces"]
print("catalog faces:", len(faces))
with open(os.path.join(ROOT, "catalog.json"), "wb") as f:
    f.write(json.dumps(cat, indent=1).encode())

ref_re = re.compile(r'''(?:src|href)\s*=\s*["']([^"'#]+)["']|url\(\s*["']?([^"')]+)["']?\s*\)''')
assets = {}
mismatch, missing = [], []
for face in faces:
    path = face["facePath"]  # /faces/<slug>.html
    data = get(BASE + path)
    h = hashlib.sha256(data).hexdigest()
    if h != face["faceSha256"]:
        mismatch.append((face["slug"], h, face["faceSha256"]))
    dest = os.path.join(ROOT, path.lstrip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    # spider relative asset references
    text = data.decode("utf-8", "replace")
    for m in ref_re.finditer(text):
        ref = m.group(1) or m.group(2)
        if not ref or ref.startswith(("http://", "https://", "data:", "//", "mailto:", "javascript:")):
            continue
        abs_url = urllib.parse.urljoin(BASE + path, ref)
        if not abs_url.startswith(BASE):
            continue
        apath = urllib.parse.urlparse(abs_url).path
        if apath == path or apath.endswith(".html"):
            continue
        assets.setdefault(apath, abs_url)

print("asset refs found:", len(assets))
asset_fail = []
for apath, aurl in sorted(assets.items()):
    dest = os.path.join(ROOT, apath.lstrip("/"))
    if os.path.exists(dest):
        continue
    try:
        data = get(aurl)
    except Exception as e:
        asset_fail.append((apath, str(e)))
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)

total = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(ROOT) for fn in fns)
nfiles = sum(len(fns) for _, _, fns in os.walk(ROOT))
print("files in tree:", nfiles, "total bytes:", total)
print("face hash mismatches:", mismatch)
print("asset failures:", asset_fail)
