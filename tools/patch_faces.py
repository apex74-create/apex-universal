#!/usr/bin/env python3
"""Patch the third-set face copies:
1. Rewrite absolute house-door links (href="/guard", "/cb", ...) in face
   copies to the live main-shelf URLs on tinyradr.com, so doors that leave
   the set point home instead of 404ing on the new origin.
2. Give signal-watch.html the faces-worker registration in addition to its
   own root registration (different scopes coexist; /faces/ wins for faces).
3. Drop the spider-downloaded extensionless 'guard' file.
Prints every change."""
import glob, os, re

ROOT = os.path.expanduser("~/workspace/universal-storefront-build/site")
BASE = "https://tinyradr.com"

door_re = re.compile(r'href\s*=\s*"(/(?!/)[A-Za-z0-9_\-./]+)"')
changed = {}
for p in sorted(glob.glob(os.path.join(ROOT, "faces", "*.html"))):
    t = open(p, encoding="utf-8", errors="replace").read()
    def rep(m):
        path = m.group(1)
        if path.startswith("/faces/") or path.startswith("/icons/"):
            return m.group(0)
        changed.setdefault(os.path.basename(p), []).append(path)
        return 'href="%s%s"' % (BASE, path)
    t2 = door_re.sub(rep, t)
    if t2 != t:
        open(p, "w", encoding="utf-8").write(t2)
print("door links rewritten:", changed)

sw_path = os.path.join(ROOT, "faces", "signal-watch.html")
t = open(sw_path, encoding="utf-8").read()
if "apex-universal-container" in t and "register('sw.js')" not in t:
    inj = ("\n<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){"
           "navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>\n")
    m = re.search(r"</body\s*>", t, re.I)
    t = t[:m.start()] + inj + t[m.start():] if m else t + inj
    open(sw_path, "w", encoding="utf-8").write(t)
    print("signal-watch: faces worker registration added alongside its own root registration")

g = os.path.join(ROOT, "guard")
if os.path.exists(g):
    os.remove(g)
    print("removed spider copy of /guard page (door now points at the live shelf)")
