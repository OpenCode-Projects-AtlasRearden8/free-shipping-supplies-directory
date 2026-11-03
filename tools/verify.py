#!/usr/bin/env python3
"""Offline verification suite for the Free Shipping Supplies Directory.

Runs with no network access. Checks that:
  1. dataset schema is sane (categories, cost types, unique ids, https URLs)
  2. the committed site/docs outputs are byte-identical to a fresh rebuild
  3. cards, QR codes, sections and counts line up; zero external asset deps
  4. no affiliate-link patterns anywhere URLs exist
  5. no secrets/API keys appear in the repo
  6. LICENSE / README / STATUS / Makefile / link log are present and correct

Exit code 0 = everything green; 1 = at least one check failed.
Run after `python3 tools/build.py` (and after `tools/linkcheck.py` once).
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build as build_mod  # noqa: E402
import linkcheck  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, hint: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" - {hint}" if (hint and not cond) else ""))
    if not cond:
        FAILS.append(name)


def repo_files(suffixes: tuple[str, ...]) -> list[Path]:
    skip_dirs = {".git", "__pycache__", "site", "docs", ".venv"}
    out: list[Path] = []
    for p in ROOT.rglob("*"):
        if p.is_file():
            if any(part in skip_dirs for part in p.parts):
                continue
            if p.suffix in suffixes:
                out.append(p)
    return out


# ------------------------------------------------------------------ dataset

def check_dataset() -> dict:
    data = json.loads(build_mod.DATA_FILE.read_text(encoding="utf-8"))
    sups = data["suppliers"]

    check("suppliers.json loads and has >= 20 entries", len(sups) >= 20)

    ids = [s["id"] for s in sups]
    check("supplier ids unique", len(ids) == len(set(ids)))

    valid_cats = {c["key"] for c in data["categories"]}
    check("all categories are known",
          all(s["category"] in valid_cats for s in sups))

    valid_cost = set(build_mod.COST_PILLS)
    check("all cost types are known", all(s["cost_type"] in valid_cost for s in sups))

    check("every supplier has name/gist/details/cost/verified",
          all(s.get("name") and s.get("gist") and s.get("details") and s.get("cost")
              and s.get("verified") for s in sups))

    urls = [s["url"] for s in sups if s.get("url")]
    check("all supplier URLs are https", all(str(u).startswith("https://") for u in urls))

    check("verification dates are ISO dates",
          all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["verified"]) for s in sups))

    check("price_evidence entries are well formed",
          all(set(e) >= {"claim", "observed", "source"}
              for s in sups for e in (s.get("price_evidence") or [])))

    check("no-url entries never render a QR card",
          all("qr-wrap" not in build_mod.card_html(s, "x")
              for s in sups if not s.get("url")))
    return data


# ------------------------------------------------- affiliate + secret scans

AFFILIATE_PATTERNS = [
    r"[\?&]tag=[\w-]+",            # amazon associates tag
    r"amzn\.to", r"purl\.org", r"shareasale", r"awin1\.com", r"clickbank",
    r"impact\.com[/?]", r"\bcj\.com\b", r"flexlinks", r"rstyle\.me",
    r"shop(?:my|stores)\.com", r"affiliate", r"affid=", r"aff_id=",
    r"utm_medium=affiliate", r"[\?&]ref=tag",
]

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{16,}", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}",
    r"gho_[A-Za-z0-9]{20,}", r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\b(api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"][^'\"]{8,}",
]


def iter_urls() -> list[tuple[str, str]]:
    """(url, location) for every URL string we consider 'published'.

    Mirrors linkcheck.collect_urls() so the link log and the published set
    can never drift apart; the local serve example and the credit link are
    excluded on purpose (same rule as the checker).
    """
    return sorted(linkcheck.collect_urls().items(), key=lambda kv: kv[0])


def check_affiliate_free() -> None:
    combined = re.compile("|".join(AFFILIATE_PATTERNS), re.IGNORECASE)
    bad = [(u, loc) for (u, loc) in iter_urls() if combined.search(u)]
    check("no affiliate-link patterns in published URLs", not bad,
          hint=f"flagged: {bad[:3]}")


def check_no_secrets() -> None:
    combined = re.compile("|".join(SECRET_PATTERNS), re.IGNORECASE)
    bad = []
    for p in repo_files({".py", ".md", ".json", ".html", ".css", ".yml", ".txt"}):
        text = p.read_text(encoding="utf-8", errors="replace")
        if combined.search(text):
            bad.append(str(p.relative_to(ROOT)))
    check("no secrets / API keys in repo files", not bad, hint=f"flagged: {bad[:3]}")


# ------------------------------------------------------------- rebuild parity

def check_rebuild_parity(data: dict) -> None:
    idx_txt = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    committed_stamp = re.search(r"rebuild stamp (\d{4}-\d{2}-\d{2})", idx_txt)
    stamp = committed_stamp.group(1) if committed_stamp else data["observed_on"]
    prn = build_mod.build_print(data)
    cat = build_mod.build_catalog(data)
    committed_prn = (ROOT / "site" / "print.html").read_text(encoding="utf-8")
    committed_cat = (ROOT / "docs" / "catalog.md").read_text(encoding="utf-8")
    check("site/index.html matches fresh rebuild", idx_txt == build_mod.build_index(data, stamp))
    check("site/print.html matches fresh rebuild", committed_prn == prn)
    check("docs/catalog.md matches fresh rebuild", committed_cat == cat)
    check("index observed-on stamp matches dataset", data["observed_on"] in idx_txt)


# --------------------------------------------------------------- site checks

def check_site(data: dict) -> None:
    idx = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    prn = (ROOT / "site" / "print.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "assets" / "style.css").read_text(encoding="utf-8")

    sups = data["suppliers"]
    with_url = [s for s in sups if s.get("url")]

    check("card count == supplier count",
          len(re.findall(r'<article class="card"', idx)) == len(sups))
    check("category sections == 4",
          len(re.findall(r'<section class="cat-section"', idx)) == 4)
    check("QR codes == url-bearing suppliers",
          len(re.findall(r'class="qr-img"', idx)) == len(with_url))
    check("print tiles == url-bearing suppliers",
          len(re.findall(r'<article class="tile"', prn)) == len(with_url))
    check("all external links are noopener-noreferrer",
          all('rel="noopener noreferrer"' in m.group(0)
              for m in re.finditer(r'<a [^>]*target="_blank"[^>]*>', idx)))

    ext_dep = re.findall(
        r'<(?:script|link|img)[^>]+(?:src|href)="https?://', idx + prn)
    check("zero external asset dependencies in site pages", not ext_dep,
          hint=str(ext_dep[:3]))

    check("stylesheet linked from both pages",
          'href="assets/style.css"' in idx and 'href="assets/style.css"' in prn)
    check("stylesheet has no @import of remote domains",
          not re.search(r"@import\s+https?://", css))

    anchors = set(re.findall(r'id="(?!card-)([\w-]+)"', idx))
    missing = [a for a in [s["id"] for s in sups] if a not in anchors]
    check("every supplier id gets its card anchor", not missing, hint=str(missing))

    qr_uris = re.findall(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', idx + prn)
    check("QR data URIs decode to SVG with a path", all(
        (lambda b: b.startswith(b"<svg") and b"<path" in b and len(b) > 400)
        (base64.b64decode(u)) for u in qr_uris))
    check("QR codes are unique per URL", len(set(qr_uris)) == len(with_url))


# ------------------------------------------------------------------ documents

def check_documents() -> None:
    guide = (ROOT / "docs" / "guide.md").read_text(encoding="utf-8")
    h2s = re.findall(r"^## (.+)$", guide, flags=re.MULTILINE)
    required = ["USPS programs", "Courier programs", "Store give-aways",
                "Frugal alternatives"]
    check("guide covers the four required sections",
          all(any(req.lower() in h.lower() for h in h2s) for req in required),
          hint=str(h2s))

    check("guide carries an observation date",
          "2026-11-02" in guide)

    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    check("README exists and credits Asdale Dynamics, LLC",
          bool(readme) and "Asdale Dynamics, LLC" in readme)

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").exists() else ""
    check("LICENSE is MIT",
          license_text.startswith("MIT License") or "Permission is hereby granted, free of charge" in license_text)
    check("LICENSE copyright line is exactly right",
          "Copyright (c) 2026 Asdale Dynamics, LLC" in license_text)

    status = (ROOT / "STATUS.md").read_text(encoding="utf-8") if (ROOT / "STATUS.md").exists() else ""
    check("STATUS.md exists with run instructions",
          bool(status) and "python3 tools/verify.py" in status)

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8") if (ROOT / "Makefile").exists() else ""
    for target in ("build", "links", "test", "serve"):
        check(f"Makefile target '{target}' present", f"{target}:" in makefile)


# ------------------------------------------------------------------ link log

def check_link_log() -> None:
    check("data/linkcheck.json exists",
          (ROOT / "data" / "linkcheck.json").exists())
    if not (ROOT / "data" / "linkcheck.json").exists():
        return
    log = json.loads((ROOT / "data" / "linkcheck.json").read_text(encoding="utf-8"))
    results = log.get("results", [])
    check("link log is current (2026-11-02 run recorded)",
          log.get("checked_date", "").startswith("2026-11"), hint=log.get("checked_date", ""))
    bad = [r for r in results if r["classification"] not in ("ok", "blocked")]
    check("link log contains no unresolved errors", not bad, hint=str(bad[:2]))
    logged = {r["url"] for r in results}
    published = set(linkcheck.collect_urls())
    unlogged = published - logged
    strayed = logged - published
    check("every published URL has a link-log entry", not unlogged, hint=str(sorted(unlogged)[:3]))
    check("link log has no stray URLs", not strayed, hint=str(sorted(strayed)[:3]))


def main() -> int:
    data = check_dataset()
    check_rebuild_parity(data)
    check_site(data)
    check_affiliate_free()
    check_no_secrets()
    check_documents()
    check_link_log()

    print()
    if FAILS:
        print(f"{len(FAILS)} check(s) FAILED: " + ", ".join(FAILS))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
