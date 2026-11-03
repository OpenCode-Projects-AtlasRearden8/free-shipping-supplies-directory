# Free Shipping Supplies Directory

A plain-English, no-nonsense directory of where to get **free or cheap shipping supplies** -
for resellers on eBay, Etsy, Poshmark, Mercari, Amazon, or anywhere a label prints.

Four lanes, one truthful price on every row:

- **USPS programs** - free branded boxes/envelopes, flat-rate strategy, Ground Advantage, the rules
- **Courier programs** - FedEx One Rate + free expedited packaging, UPS account supplies, DHL OSO
- **Store give-aways** - produce/bike/furniture/liquor-store sources, U-Haul box exchange, local free groups
- **Frugal alternatives** - reuse first, then bulk mailers/boxes/tape with real observed prices, newsprint roll ends, and a free postage platform

Every cost and link is stamped **as observed on 2026-11-02**. Prices move; dates keep us honest.
No affiliate links anywhere - links go to the program or product page itself.

## Quick start

Open **`site/index.html`** in any browser (it is fully static - no build server, no CDNs,
no tracking; every QR code is generated offline and embedded).

Or serve it locally:

```sh
make serve          # http://localhost:8123
# ...or plain python:
python3 -m http.server 8123 --directory site
```

Printable QR bench sheet: open **`site/print.html`**, print, cut, tape it where you pack.

The long-form guide (USPS/courier programs + store give-aways + frugal alternatives) lives in
**`docs/guide.md`**, and the data-backed table is **`docs/catalog.md`**.

## Repository layout

```
data/suppliers.json   single source of truth (24 curated sources, dated observations)
tools/build.py        generates site/index.html, site/print.html, docs/catalog.md
tools/linkcheck.py    live-checks every URL -> data/linkcheck.json + docs/link-log.md
tools/verify.py       offline test suite (schema, parity, QR, no-affiliate, no-secrets)
tools/vendor/         vendored MIT QR generator (Project Nayuki's qrcodegen.py)
site/                 the static directory + bench sheet + stylesheet
docs/guide.md         the field guide (the friend-who-knows-things version)
docs/link-log.md      every checked link with its HTTP status and date
Makefile              build / links / test / serve
```

## Keeping it fresh

```sh
make build     # rebuild site + catalog from data/suppliers.json
make links     # re-check every URL (needs network); refreshes the link log
make test      # offline verification suite (must pass)
```

Edit `data/suppliers.json`, run `make build && make test`, and the site, bench sheet,
and catalog all stay in sync automatically.

## Honest-use notes

- Service-branded free packaging ships its own service (USPS Priority/Express, FedEx
  expedited/One Rate, UPS express, DHL Express). Cross-loading it onto another carrier is
  misuse per the carriers' own rules - see the supply-rules card in the site and guide.
- Prices/postage observed 2026-11-02 drift with each January USPS price cycle and every
  promo. Re-check before big orders.
- Nothing here is legal or hazmat advice; carriers' current rules are the binding text.

## Credits

Built and maintained by **Asdale Dynamics, LLC** - beginner-friendly AI education, books,
and practical tools (including The Massive AI Manual - AI explained "like a friend would").
Project hub: <https://dylanasdale.github.io/>

The directory uses a vendored copy of Project Nayuki's MIT-licensed
[QR Code generator library](https://www.nayuki.io/page/qr-code-generator-library);
its full license header is preserved in `tools/vendor/qrcodegen.py`.

## License

MIT - see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.
