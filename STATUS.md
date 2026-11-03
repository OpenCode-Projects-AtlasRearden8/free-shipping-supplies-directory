# STATUS.md

Project: **Free Shipping Supplies Directory** - freebie sources (free or cheap shipping supplies) for resellers.
Built for/by **Asdale Dynamics, LLC** (Dylan Asdale). All observations are stamped with the date they were gathered.

---

## What was built

| Piece | What it is |
| --- | --- |
| `site/index.html` | Static, single-page HTML directory: 24 curated sources across 4 categories (USPS programs / Courier programs / Store give-aways / Frugal alternatives), cost pills per card, per-category "costs at a glance," price-evidence footers with observation dates, QR-ready cards (17 inline SVG QR codes, generated offline), category filters + a "free packaging only" toggle (plain vanilla JS; page fully works without it). Zero external asset dependencies (no CDNs, webfonts, analytics, or tracking). |
| `site/print.html` | Printable QR bench sheet: 17 cut-out tiles (QR + name + cost + URL) to tape where you pack. |
| `site/assets/style.css` | Warm, responsive, print-friendly stylesheet; no webfonts, no remote imports. |
| `docs/guide.md` | The substantive field guide: USPS programs (free supplies mechanics, observed Flat Rate prices, DMM/FAQ rules, Ground Advantage tiers, worked examples), courier programs (FedEx One Rate + complimentary expedited packaging, UPS account supplies, UPS Store, DHL OSO), store give-aways (7 sources + etiquette scripts), frugal alternatives (reuse, bulk math with observed prices, newsprint roll ends, Dollar Tree doctrine, Pirate Ship), a zero-cost first-10-orders kit, care instructions, FAQ. |
| `docs/catalog.md` | Auto-generated markdown table of every source with observed costs and evidence citations. |
| `data/suppliers.json` | Single source of truth: 24 entries (5 USPS, 5 couriers, 7 stores, 7 frugal), each with `cost_type`, observed-cost text, dated `price_evidence`, and a verified-on date. |
| `tools/build.py` | Generates `site/index.html`, `site/print.html`, `docs/catalog.md` from the JSON; offline, stdlib + vendored QR library. |
| `tools/linkcheck.py` | Live-logs every published URL (cards + evidence citations + README) with HTTP status and classification into `data/linkcheck.json` + human table `docs/link-log.md`. |
| `tools/verify.py` | Offline test suite (40 checks): dataset schema, rebuild parity, card/QR counts, zero external deps, no-affiliate-pattern scan over all published URLs, secret/API-key scan, LICENSE/README/STATUS/Makefile and link-log consistency. |
| `tools/vendor/qrcodegen.py` | Vendored copy of Project Nayuki's MIT-licensed QR Code generator; full license header preserved. |
| `README.md`, `LICENSE` (MIT, exact line `Copyright (c) 2026 Asdale Dynamics, LLC`), `Makefile`, `.gitignore` | Project furniture. |

No affiliate links anywhere: all published URLs are plain program/product pages, verified by an automated pattern scan in the test suite. No secrets, API keys, or personal data in any file (also test-enforced).

## How to run it

```sh
# build the site + catalog from the dataset (idempotent)
python3 tools/build.py

# offline verification suite - all 40 checks should pass
python3 tools/verify.py

# live link check (needs network) - refreshes docs/link-log.md
python3 tools/linkcheck.py

# see it
python3 -m http.server 8123 --directory site    # then open http://localhost:8123
# (opening site/index.html directly from the file system also works)
```

`make build` / `make links` / `make test` / `make serve` are provided as conveniences
(the build environment used here had no `make` binary, so the direct `python3` commands
above are the verified path; a functional check of Makefile targets is in the test suite).

## Verification results (actual runs)

- **Build**: `python3 tools/build.py` - "built: site/index.html, site/print.html, docs/catalog.md (24 sources, stamped 2026-11-02)".
- **Test suite**: `python3 tools/verify.py` - **40/40 checks PASS** (dataset schema; rebuild parity byte-identical; 24 cards / 4 sections / 17 QR codes / 17 print tiles; all external anchors `noopener noreferrer`; zero external asset deps; QR data URIs decode to valid SVG; no affiliate patterns in any published URL; no secrets patterns; LICENSE/README/Makefile/link-log consistency). Exit code 0.
- **Link log**: `python3 tools/linkcheck.py` on 2026-11-03 08:26 UTC - **29 URLs checked: 26 ok (HTTP 200), 3 blocked (HTTP 403 bot-shield on store.usps.com), 0 errors.**
- **Serve smoke test** - `python3 -m http.server 8123 --directory site`:
  - `/` -> 200 (225,322 B)
  - `/print.html` -> 200 (185,637 B)
  - `/assets/style.css` -> 200 (8,541 B)
- Git identity commits only (plain messages, no trailers); nothing pushed or published.

## Known gaps (honestly)

1. **Prices drift.** Every price is stamped "observed" with its date (2026-11-02, gathered during a session that ran into the early hours of 2026-11-03 UTC; observation stamps use 2026-11-02 consistently, and the link log carries the exact check date/time). USPS reprices every January; online storefront prices move weekly. Re-observe before betting volume.
2. **Bot-shielded pages.** The USPS Postal Store pages answer `403` to automated requests although they are public and human-readable. Content for those was confirmed via search snapshots on the same date; the link log labels them `blocked`, not `ok`.
3. **Store give-aways are folk practice.** Produce/bike/furniture/liquor boxes and office paper cases have no URL to link and vary store-to-store; cards mark them "free - call ahead" and the guide gives scripts. The U-Haul box exchange is not at every location.
4. **Some content is platform-gated.** Facebook Marketplace/Buy Nothing are login-gated (Marketplace returned 400 to bots); the card links Nextdoor instead.
5. **eBay bulk-supply listings were observed via search snapshots** (search pages are bot-shielded too), so the mailers card links Amazon/Walmart/Uline pages that resolve, and notes eBay's bulk listings as text.
6. **Single-page, single-locale English site**; no search-as-you-type, no dark mode; filters degrade gracefully without JS. The QR codes are SVG (works from file:// and every modern phone camera).
7. **Guide includes a USPS-alcohol caution** summarized from USPS rules; for hazmat/liquor specifics the carriers' own current rules are the binding text - this project is not legal advice.
