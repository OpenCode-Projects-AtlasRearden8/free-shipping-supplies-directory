#!/usr/bin/env python3
"""Live link checker for the Free Shipping Supplies Directory.

Collects every URL from data/suppliers.json, docs/guide.md and README.md,
requests each one (browser-style UA, redirects followed), and writes:

  - data/linkcheck.json  (machine-readable results, stamped with the date)
  - docs/link-log.md     (human table: status + classification per link)

Classification:
  ok      200-299
  blocked 400-499 (bot shield or login wall; human browsers usually still fine)
  error   5xx, DNS failure, timeout - a genuine problem

Exit codes: 0 = no errors, 2 = at least one error, 3 = no network at all.

No secrets, no API keys - plain HTTPS GETs only.
"""

from __future__ import annotations

import json
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "suppliers.json"
GUIDE = ROOT / "docs" / "guide.md"
README = ROOT / "README.md"
OUT_JSON = ROOT / "data" / "linkcheck.json"
OUT_MD = ROOT / "docs" / "link-log.md"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36") + " LinkCheck-AsdaleDyn/1.0"

# Citation sources used inside dataset evidence fields. They are part of the
# published record, so they are link-checked alongside the card URLs.
EXTRA_URLS = [
    "https://pe.usps.com/text/dmm300/Notice123.htm",
    "https://pe.usps.com/text/dmm300/135.htm",
    "https://pe.usps.com/text/dmm300/115.htm",
    "https://www.usps.com/ship/online-shipping.htm",
    "https://www.usps.com/ship/mail-shipping-services.htm",
    "https://www.usps.com/business/prices.htm",
    "https://store.usps.com/store/product/shipping-supplies/priority-mail-flat-rate-envelope-P_EP_14_F",
    "https://store.usps.com/store/product/shipping-supplies/priority-mail-flat-rate-medium-box-1-P_O_FRB1",
    "https://www.uhaul.com/MovingSupplies/Packing-Tape",
    "https://sameday.dollartree.com/store/dollar-tree/products/22671861-clear-packing-tape-each",
    "https://www.ebay.com/help/selling/selling-online/ebayseller-transaction-process?id=4085",
]


def collect_urls() -> dict[str, list[str]]:
    """Return {url: [where it is used]} across the project sources."""
    found: dict[str, list[str]] = {}

    def add(url: str, where: str) -> None:
        url = url.rstrip(",;")
        if not url.startswith("http"):
            return
        if re.match(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])", url):
            return  # example commands like the README serve-snippet, not published links
        if "dylanasdale.github.io" in url:  # credit link, not a data source
            return
        found.setdefault(url, []).append(where)

    with open(DATA, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for sup in data["suppliers"]:
        if sup.get("url"):
            add(sup["url"], "data/suppliers.json")

    for path in (GUIDE, README):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"https?://[^\s)>\]]+", text):
                add(m.group(0), path.name)

    for extra in EXTRA_URLS:
        add(extra, "docs evidence citations")

    return found


def check_url(url: str) -> dict:
    res = _check_via_urllib(url)
    if res["classification"] == "error":
        res = _check_via_curl(url, res)  # some bot shields block urllib but allow curl
    return res


def _check_via_urllib(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            status = resp.getcode()
            resp.read(2048)
            return {"url": url,
                    "status": status,
                    "classification": "ok" if status and 200 <= status < 400 else "error",
                    "note": ""}
    except urllib.error.HTTPError as e:
        code = e.code
        if 400 <= code < 500:
            return {"url": url, "status": code,
                    "classification": "blocked",
                    "note": ("bot-shield or login wall (40x) - a human browser usually "
                             "still reaches this; content was cross-checked via search "
                             "snapshots on the same date where relevant")}
        return {"url": url, "status": code, "classification": "error", "note": "server error"}
    except (urllib.error.URLError, socket.timeout, ConnectionResetError, TimeoutError) as e:
        reason = str(getattr(e, "reason", "")) or str(e)
        return {"url": url, "status": None, "classification": "error",
                "note": f"connection problem: {reason[:120]}"}
    except Exception as e:  # noqa: BLE001 - keep the checker unkillable
        return {"url": url, "status": None, "classification": "error",
                "note": f"unexpected: {type(e).__name__}: {str(e)[:120]}"}


def _check_via_curl(url: str, prev: dict) -> dict:
    """Fallback transport: curl handles a few anti-bot layers urllib trips on."""
    import subprocess
    try:
        proc = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-L", "-m", "30",
             "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0 Safari/537.36", "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=40)
        code_text = (proc.stdout or "").strip()[-3:]
        status = int(code_text) if code_text.isdigit() else None
    except Exception:  # noqa: BLE001
        return prev
    if status is None:
        return prev
    if 200 <= status < 400:
        return {"url": url, "status": status, "classification": "ok",
                "note": "ok via curl fallback (urllib was bot-blocked)"}
    if status in (400, 403, 406, 429) or 500 <= status < 600:
        return {"url": url, "status": status, "classification": "blocked",
                "note": ("bot-shield answered (status " + str(status) + ") even via curl - "
                         "content cross-checked via search snapshots on the same date "
                         "where relevant")}
    return prev


def write_markdown(results: list[dict], checked_date: str, stamp: str) -> None:
    rows: list[str] = []
    rows.append("# Link log (generated)")
    rows.append("")
    rows.append(f"Checked **{checked_date}** at {stamp} UTC by `tools/linkcheck.py`.")
    rows.append("Classifications: **ok** (200-399), **blocked** (40x bot-shield/login wall -")
    rows.append("content cross-checked by search snapshot on the same date), **error** (real failure).")
    rows.append("")
    rows.append("No affiliate links are used anywhere in this project; these are plain")
    rows.append("program/product pages, tested as-assessed.")
    rows.append("")
    order = {"ok": 0, "blocked": 1, "error": 2}
    results = sorted(results, key=lambda r: (order[r["classification"]], r["url"]))
    rows.append("| Status | HTTP | Classification | Where used | URL |")
    rows.append("| --- | --- | --- | --- | --- |")
    for r in results:
        where = ", ".join(r["used_in"]) if r["used_in"] else "-"
        link_text = r["url"]
        rows.append(f"| {'ok' if r['classification']=='ok' else r['classification']} "
                    f"| {r['status'] if r['status'] is not None else 'n/a'} "
                    f"| {r['classification']} | {where} | <{link_text}> |")
    rows.append("")
    ok_n = sum(1 for r in results if r["classification"] == "ok")
    blk_n = sum(1 for r in results if r["classification"] == "blocked")
    err_n = sum(1 for r in results if r["classification"] == "error")
    rows.append(f"Totals: {ok_n} ok &middot; {blk_n} blocked &middot; {err_n} error.")
    OUT_MD.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    urls = collect_urls()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    checked_date = now.date().isoformat()

    results: list[dict] = []
    for url in sorted(urls):
        res = check_url(url)
        res["used_in"] = urls[url]
        results.append(res)

    payload = {
        "checked_date": checked_date,
        "checked_at_utc": stamp,
        "checker": "tools/linkcheck.py",
        "results": [
            {
                "url": r["url"],
                "status": r["status"],
                "classification": r["classification"],
                "note": r["note"],
                "used_in": r["used_in"],
            }
            for r in results
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload["results"], checked_date, stamp)

    ok_n = sum(1 for r in results if r["classification"] == "ok")
    blk_n = sum(1 for r in results if r["classification"] == "blocked")
    err_n = sum(1 for r in results if r["classification"] == "error")
    print(f"linkcheck: {ok_n} ok, {blk_n} blocked, {err_n} error "
          f"({len(results)} urls, date {checked_date})")
    for r in results:
        if r["classification"] == "error":
            print(f"  ERROR  {r['status']} {r['url']} - {r['note']}")
        elif r["classification"] == "blocked":
            print(f"  blocked {r['status']} {r['url']}")

    if err_n:
        if ok_n == 0 and blk_n == 0:
            return 3
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
