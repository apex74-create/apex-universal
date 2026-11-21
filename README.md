# Apex Universal — The Third Set

The house universal container storefront: all 56 Apex faces at one address,
**universal.apex-airsolutions.com**, installable on Android and Apple from the same shelf.

- `index.html` — the sales assembly. Cards are generated from the depot's own
  catalog (`catalog.json`, carried verbatim from tinyradr.com/depot): names,
  prices, APK hashes and sizes are the depot's record, nothing re-typed.
- `faces/` — the 56 face files (live shelf bytes at build, 2026-11-20), each carrying
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
