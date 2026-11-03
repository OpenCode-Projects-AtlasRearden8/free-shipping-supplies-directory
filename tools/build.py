#!/usr/bin/env python3
"""Build the Free Shipping Supplies Directory.

Reads data/suppliers.json (single source of truth) and generates:
  - site/index.html    -> browsable directory with QR-ready cards
  - site/print.html    -> printable QR card sheet for a packing-bench wall
  - docs/catalog.md    -> markdown table of every source with observed costs

Pure stdlib + the vendored MIT QR generator (tools/vendor/qrcodegen.py).
No network access at build time; no external runtime dependencies.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = Path(__file__).resolve().parent / "vendor"
sys.path.insert(0, str(VENDOR))

from qrcodegen import QrCode  # noqa: E402  (vendored, MIT - Project Nayuki)

DATA_FILE = ROOT / "data" / "suppliers.json"
SITE_DIR = ROOT / "site"
DOCS_DIR = ROOT / "docs"

OBSERVED_ON = "2026-11-02"

COST_PILLS = {
    "free-with-service": ("Free w/ service", "cost-service"),
    "free": ("Free", "cost-free"),
    "free-call-ahead": ("Free - call ahead", "cost-call"),
    "cheap": ("Cheap", "cost-cheap"),
}


# --------------------------------------------------------------------------- QR

def qr_svg(text: str, dark: str = "#101820", margin: int = 2) -> str:
    """Render text as a crisp SVG QR code (small, self-contained)."""
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    n = qr.get_size()
    total = n + 2 * margin
    parts = [f"M{x} {y}h1v1h-1z"
             for y in range(n) for x in range(n) if qr.get_module(x, y)]
    d = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{total * 4}" height="{total * 4}" shape-rendering="crispEdges" '
        f'role="img" aria-label="QR code">'
        f'<rect width="{total}" height="{total}" fill="#ffffff"/>'
        f'<path transform="translate({margin} {margin})" fill="{dark}" d="{d}"/>'
        f"</svg>"
    )


def qr_data_uri(text: str) -> str:
    svg = qr_svg(text)
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


# ------------------------------------------------------------------- helpers

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def load_data() -> dict:
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def category_map(data: dict) -> dict:
    return {c["key"]: c["label"] for c in data["categories"]}


# ------------------------------------------------------------------- cards

def card_html(sup: dict, cat_label: str) -> str:
    pill_text, pill_class = COST_PILLS[sup["cost_type"]]
    lines: list[str] = []
    lines.append(
        f'<article class="card" id="{esc(sup["id"])}" data-cat="{esc(sup["category"])}" '
        f'data-cost="{esc(sup["cost_type"])}">'
    )
    lines.append('<div class="card-top">')
    lines.append(f'<span class="pill cat-pill">{esc(cat_label)}</span>')
    lines.append(f'<span class="pill cost-pill {pill_class}">{esc(pill_text)}</span>')
    lines.append("</div>")
    lines.append(f'<h2 class="card-title">{esc(sup["name"])}</h2>')
    lines.append(f'<p class="gist">{esc(sup["gist"])}</p>')
    lines.append('<ul class="details">')
    for detail in sup["details"]:
        lines.append(f"<li>{esc(detail)}</li>")
    lines.append("</ul>")

    evidence = sup.get("price_evidence") or []
    if evidence:
        lines.append('<div class="evidence"><div class="evidence-title">Price evidence</div><ul>')
        for ev in evidence:
            lines.append(
                f'<li><span class="claim">{esc(ev["claim"])}</span> '
                f'<span class="ev-date">observed {esc(ev["observed"])} - {esc(ev["source"])}</span></li>'
            )
        lines.append("</ul></div>")

    lines.append('<div class="card-foot">')
    if sup.get("url"):
        lines.append(
            f'<a class="btn-link" href="{esc(sup["url"])}" target="_blank" '
            f'rel="noopener noreferrer">{esc(sup["url_label"])} &#8599;</a>'
        )
    else:
        lines.append('<span class="nolink-hint">No web link - call ahead or ask in person</span>')
    lines.append(f'<span class="verified">verified {esc(sup["verified"])}</span>')
    lines.append("</div>")

    if sup.get("url"):
        lines.append('<div class="qr-wrap">')
        lines.append(
            f'<img class="qr-img" alt="Scan to open: {esc(sup["url"])}" '
            f'src="{qr_data_uri(sup["url"])}" width="110" height="110" loading="lazy">'
        )
        lines.append('<span class="qr-cap">scan for the link</span>')
        lines.append("</div>")

    lines.append("</article>")
    return "\n".join(lines)


def section_html(cat: dict, suppliers: list[dict]) -> str:
    label = cat["label"]
    cards = "\n".join(card_html(s, label) for s in suppliers)
    count = len(suppliers)
    free_types = ("free-with-service", "free", "free-call-ahead")
    free_count = sum(1 for s in suppliers if s["cost_type"] in free_types)
    return (
        f'<section class="cat-section" id="cat-{esc(cat["key"])}" data-cat="{esc(cat["key"])}">'
        f'<header class="cat-head">'
        f'<h2 class="cat-title">{esc(label)}</h2>'
        f'<span class="cat-count">{count} sources &middot; {free_count} with free packaging</span>'
        f"</header>"
        f'<div class="card-grid">{cards}</div>'
        f"</section>"
    )


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Free Shipping Supplies Directory - freebie sources for resellers</title>
<meta name="description" content="A no-affiliate, field-tested directory of free and cheap shipping supplies: USPS and courier programs, store give-aways, and frugal alternatives. Prices marked with the date they were observed.">
<meta name="theme-color" content="#faf6ef">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-head">
  <div class="wrap">
    <p class="kicker">ASDALE DYNAMICS &middot; A RESELLER FREEBIE DIRECTORY</p>
    <h1>Free (or nearly) shipping supplies</h1>
    <p class="tagline">Where to get free or cheap boxes, mailers, tape and void fill -
    USPS and courier programs, store give-aways, and frugal alternatives -
    with every cost and link dated to <strong>__OBSERVED_ON__</strong>. No affiliate links.</p>
    <nav class="filters" aria-label="Filter sources">
      <button class="chip chip-active" data-filter="all">All <span>__TOTAL__</span></button>
      <button class="chip" data-filter="usps">USPS programs <span>__N_USPS__</span></button>
      <button class="chip" data-filter="couriers">Courier programs <span>__N_COURIERS__</span></button>
      <button class="chip" data-filter="stores">Store give-aways <span>__N_STORES__</span></button>
      <button class="chip" data-filter="frugal">Frugal alternatives <span>__N_FRUGAL__</span></button>
      <button class="chip chip-free" data-filter="free">Free packaging only <span>__N_FREE__</span></button>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="howto">
    <div class="howto-item"><span class="howto-n">1</span><span>Filter to a lane above - most resellers live in <em>Ground Advantage</em> + <em>store give-aways</em>.</span></div>
    <div class="howto-item"><span class="howto-n">2</span><span>Each card carries the observed price and its date. Postage and packaging change; dates keep us honest.</span></div>
    <div class="howto-item"><span class="howto-n">3</span><span>Scan a card's QR when you are out sourcing, or print the <a href="print.html">bench sheet</a> for your wall.</span></div>
  </div>

  __SECTIONS__

  <section class="fineprint">
    <h2>The honest fine print</h2>
    <ul>
      <li>Every price here was <strong>observed on 2026-11-02</strong> and will drift. Re-check before big orders - postage pages are the source of truth.</li>
      <li>Service-branded free packaging (USPS Priority, FedEx One Rate, UPS express) exists so you ship <em>that service</em>. Using it for another carrier is misuse - see the USPS supply-rules card.</li>
      <li>No affiliate links anywhere in this project; links go to the program or product page itself. Store give-aways are local folk practice, marked &ldquo;call ahead.&rdquo;</li>
      <li>Hazmat notes: USPS Priority packaging has no dangerous-goods exemptions - lithium batteries, nail polish, perfumes and aerosols ship Ground with their own rules.</li>
    </ul>
  </section>
</main>

<footer class="site-foot">
  <div class="wrap">
    <p>Built by <strong>Asdale Dynamics, LLC</strong> &middot; a freebie directory for resellers, from the folks who write AI guides &ldquo;like a friend would&rdquo; at <a href="https://dylanasdale.github.io/" rel="noopener noreferrer">dylanasdale.github.io</a></p>
    <p class="foot-meta">Data observed __OBSERVED_ON__ &middot; rebuild stamp __BUILD_DATE__ &middot; <a href="../docs/guide.md">the long-form guide</a> (repo)</p>
  </div>
</footer>

<script>
(function () {
  var chips = document.querySelectorAll(".chip[data-filter]");
  var sections = document.querySelectorAll(".cat-section");
  var cards = document.querySelectorAll(".card");
  function apply(mode) {
    var free = mode === "free";
    var cat = free ? "all" : mode;
    sections.forEach(function (sec) {
      sec.hidden = !(cat === "all" || sec.dataset.cat === cat);
      if (!sec.hidden && free) {
        var stillThere = sec.querySelectorAll('.card:not([data-cost="cheap"])');
        sec.hidden = stillThere.length === 0;
      }
    });
    cards.forEach(function (card) {
      card.hidden = free && card.dataset.cost === "cheap";
    });
    chips.forEach(function (chip) {
      chip.classList.toggle("chip-active", chip.dataset.filter === mode);
    });
  }
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () { apply(chip.dataset.filter); });
  });
})();
</script>
</body>
</html>
"""

PRINT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bench sheet - QR cards for the packing wall</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="print-body">
<header class="print-head">
  <h1>Bench sheet - free shipping supplies</h1>
  <p>Costs observed __OBSERVED_ON__. Cut the tiles you want, tape them where you pack.
  Full details live on <a href="index.html">the directory page</a>.</p>
</header>
<main class="print-grid">
__TILES__
</main>
<footer class="print-foot">
  <p>Built by Asdale Dynamics, LLC &middot; data observed __OBSERVED_ON__ &middot; no affiliate links</p>
</footer>
</body>
</html>
"""


def build_index(data: dict, build_date: str) -> str:
    cats = category_map(data)
    sources = data["suppliers"]
    sections = "\n".join(
        section_html(cat, [s for s in sources if s["category"] == cat["key"]])
        for cat in data["categories"]
    )
    counts = {key: sum(1 for s in sources if s["category"] == key)
              for key in ("usps", "couriers", "stores", "frugal")}
    free_n = sum(1 for s in sources
                 if s["cost_type"] in ("free", "free-with-service", "free-call-ahead"))
    tpl = (INDEX_TEMPLATE
           .replace("__OBSERVED_ON__", OBSERVED_ON)
           .replace("__BUILD_DATE__", build_date)
           .replace("__TOTAL__", str(len(sources)))
           .replace("__N_USPS__", str(counts["usps"]))
           .replace("__N_COURIERS__", str(counts["couriers"]))
           .replace("__N_STORES__", str(counts["stores"]))
           .replace("__N_FRUGAL__", str(counts["frugal"]))
           .replace("__N_FREE__", str(free_n))
           .replace("__SECTIONS__", sections))
    return tpl


def print_tile(sup: dict) -> str:
    pill_text, pill_class = COST_PILLS[sup["cost_type"]]
    return (
        f'<article class="tile">'
        f'<img class="tile-qr" alt="QR code" src="{qr_data_uri(sup["url"])}">'
        f'<h3 class="tile-name">{esc(sup["name"])}</h3>'
        f'<span class="pill cost-pill {pill_class} tile-cost">{esc(pill_text)}</span>'
        f'<span class="tile-url">{esc(sup["url"])}</span>'
        f'<span class="tile-observed">observed {esc(sup["verified"])}</span>'
        f"</article>"
    )


def build_print(data: dict) -> str:
    tiles = "\n".join(print_tile(s) for s in data["suppliers"] if s.get("url"))
    return (PRINT_TEMPLATE
            .replace("__OBSERVED_ON__", OBSERVED_ON)
            .replace("__TILES__", tiles))


def build_catalog(data: dict) -> str:
    cats = category_map(data)
    out: list[str] = []
    out.append("# Supplier catalog (generated)")
    out.append("")
    out.append("Auto-generated from `data/suppliers.json` - do not hand-edit; rerun")
    out.append("`python3 tools/build.py` after changing the data. All observations")
    out.append(f"dated **{OBSERVED_ON}**. No affiliate links.")
    out.append("")
    for cat in data["categories"]:
        sources = [s for s in data["suppliers"] if s["category"] == cat["key"]]
        out.append(f"## {cats[cat['key']]}")
        out.append("")
        out.append("| Source | Cost (observed) | In one line | Link |")
        out.append("| --- | --- | --- | --- |")
        for s in sources:
            link = (f"[open &#8599;]({s['url']})" if s.get("url") else "no link - call ahead")
            out.append(
                f"| {esc(s['name']).replace('|', '/')} | "
                f"{esc(s['cost']).replace('|', '/')} | "
                f"{esc(s['gist']).replace('|', '/')} | {link} |"
            )
        out.append("")
        out.append("Observed-price evidence:")
        out.append("")
        for s in sources:
            for ev in s.get("price_evidence") or []:
                out.append(
                    f"- **{s['id']}** - {esc(ev['claim'])} "
                    f"(observed {ev['observed']}; {ev['source']})"
                )
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    data = load_data()
    build_date = date.today().isoformat()
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "index.html").write_text(build_index(data, build_date), encoding="utf-8")
    (SITE_DIR / "print.html").write_text(build_print(data), encoding="utf-8")
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "catalog.md").write_text(build_catalog(data), encoding="utf-8")
    print(f"built: site/index.html, site/print.html, docs/catalog.md "
          f"({len(data['suppliers'])} sources, stamped {OBSERVED_ON})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
