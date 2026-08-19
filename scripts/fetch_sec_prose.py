"""Fetch a small sample of real SEC filing prose, for a second genre.

`scripts/gate_on_real_prose.py` measures the staleness gate on 36,223 sentences
of scientific abstracts -- the only real prose on disk. One corpus is not a
measurement, and the genre that actually bears on this repo is **financial
filings**, which is what the solvency domain imitates. Abstracts over-represent
the passive of *use* and under-represent `former`, `ceased`, `withdrawn`, which
is precisely the vocabulary a filing uses.

Downloads a handful of 10-K primary documents from EDGAR, which is public domain
and permits automated access at a modest rate. Writes plain sentences to
``data/artifacts/sec_sentences.jsonl`` -- ``/data/`` is gitignored, so the
artefact stays out of the repo and this script is the reproduction.

Run: uv run python -u scripts/fetch_sec_prose.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

OUT = Path("data/artifacts/sec_sentences.jsonl")
UA = "symbolic-ai-models research (non-commercial; automated at <1 req/sec)"

#: A spread of filers rather than one sector, so the sample is not one drafting
#: house's house style.
CIKS = ["0000320193", "0000789019", "0000019617", "0000200406", "0000104169",
        "0000034088", "0000021344", "0000051143", "0000097745", "0000063908",
        "0000064040", "0000078003", "0000093410", "0000101829", "0000318154"]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def latest_10k(cik: str) -> str | None:
    meta = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    recent = meta["filings"]["recent"]
    for form, acc, doc in zip(recent["form"], recent["accessionNumber"],
                              recent["primaryDocument"]):
        if form == "10-K" and doc.endswith((".htm", ".html", ".txt")):
            a = acc.replace("-", "")
            return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{a}/{doc}")
    return None


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def sentences(html: str) -> list[str]:
    text = _WS.sub(" ", _TAG.sub(" ", html))
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&#8217;", "'").replace("&#160;", " "))
    out = []
    for s in re.split(r"(?<=[.?!])\s+", text):
        s = s.strip()
        if len(s) < 40 or len(s) > 600:
            continue
        letters = sum(c.isalpha() or c.isspace() for c in s)
        if letters / len(s) < 0.85:          # skip tables rendered as prose
            continue
        if len(s.split()) < 8:
            continue
        out.append(s)
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with OUT.open("w") as fh:
        for cik in CIKS:
            try:
                url = latest_10k(cik)
                time.sleep(1.1)
                if not url:
                    print(f"{cik}: no 10-K found")
                    continue
                html = _get(url).decode("utf-8", errors="ignore")
                time.sleep(1.1)
            except Exception as e:
                print(f"{cik}: {type(e).__name__} {e}")
                continue
            sents = sentences(html)
            for s in sents:
                fh.write(json.dumps({"cik": cik, "sentence": s}) + "\n")
            total += len(sents)
            print(f"{cik}: {len(sents)} sentences  ({url.split('/')[-1]})")
    print(f"\n{total} sentences -> {OUT}")


if __name__ == "__main__":
    main()
