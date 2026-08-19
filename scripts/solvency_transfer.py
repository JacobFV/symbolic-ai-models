"""Does the reader machinery transfer to a structurally opposite task?

Flood is routing over a network, a subset answer, expensive kernels. Solvency is
one boolean per group, a trivial kernel, and a **bitemporal** core: a figure
filed after the decision date was not knowable and must not be used.

That inverts a rule the flood reader learned. There a superseded value was a
distractor and *take the latest number* was right. Here the revision is the
substance and *take the latest* is wrong. **The same surface feature is a trap in
one domain and the answer in the other**, so a flood-derived heuristic should
misfire here by a measurable amount -- which is what makes this a transfer test
rather than a second implementation.

Arms, each recovering `(members, filings, threshold, decision_date)` from text
alone and then running the task's own `decide`:

    oracle              the true case                       ceiling
    signature           type-signature routing, date-aware
    latest-value        the FLOOD heuristic: newest figure, dates ignored
    first-filed         ignore revisions entirely
    majority class      the floor

Run: uv run python -u scripts/solvency_transfer.py
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.surface import render_observation

OUT = Path("runs/solvency_transfer.json")
N_CASES = 60
_MEMBER = re.compile(r"\b((?:group|sub_\d+))\b")
_USD = re.compile(r"(\d+\.\d{2}) USD")
_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_LONG = re.compile(r"\b(\d{1,2}) (January|February|March|April|May|June|July|"
                   r"August|September|October|November|December) (\d{4})\b")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _dates(sent: str) -> list[str]:
    """Every date, normalised to ISO. Two surface formats, one representation."""
    out = list(_ISO.findall(sent))
    for d, mon, y in _LONG.findall(sent):
        out.append(f"{y}-{_MONTHS.index(mon) + 1:02d}-{int(d):02d}")
    return out


def read_signature(text: str) -> dict:
    """``text -> (members, filings, threshold, decision_date)`` by signature.

    No content word is consulted. A sentence carrying two member ids and no
    number is an ownership claim; one member, one USD figure and one date is a
    filing; a bare USD figure is the threshold; a bare date is the decision.
    """
    members: set[str] = set()
    filings: list[tuple[str, float, str]] = []
    threshold = None
    decision = None
    for para in text.split("\n\n"):
        for sent in re.split(r"(?<=\.)\s+|(?<=\?)\s+", para):
            names = list(dict.fromkeys(_MEMBER.findall(sent)))
            money = [float(x) for x in _USD.findall(sent)]
            dates = _dates(sent)
            if len(names) == 2 and not money and not dates:
                members.update(names)
            elif len(names) == 1 and money and dates:
                members.add(names[0])
                filings.append((names[0], money[0], dates[0]))
            elif money and not names and not dates:
                threshold = money[0]
            elif dates and not names and not money:
                decision = dates[0]
    return {"members": sorted(members), "filings": filings,
            "threshold": threshold, "decision_date": decision}


def answer(rec: dict, *, policy: str) -> bool | None:
    """Run the covenant test on recovered data under one policy."""
    if rec["threshold"] is None or not rec["members"]:
        return None
    as_of = rec["decision_date"]
    total = 0.0
    for m in rec["members"]:
        seen = [(v, k) for e, v, k in rec["filings"] if e == m]
        if policy == "signature":
            if as_of is None:
                return None
            seen = [p for p in seen if p[1] <= as_of]
        elif policy == "first_filed":
            seen = sorted(seen, key=lambda p: p[1])[:1]
        # "latest_value" uses every filing, dates ignored -- the flood rule
        if not seen:
            continue
        total += max(seen, key=lambda p: p[1])[0]
    return total >= rec["threshold"]


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truth = [decide(c, as_of=c.decision_date)[0] for c in cases]
    base = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    print(f"{N_CASES} cases; {sum(truth)} cleared, {len(truth)-sum(truth)} not. "
          f"Majority-class floor {base:.3f}\n", flush=True)

    hdr = f"{'arm':<26} {'V=1':>7} {'V=2':>7} {'V=3':>7} {'V=4':>7}"
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    recalls = {}
    for name, policy in (("signature (date-aware)", "signature"),
                         ("latest value (FLOOD rule)", "latest_value"),
                         ("first filed", "first_filed")):
        accs = []
        for v in (1, 2, 3, 4):
            hits = 0
            rec_ok = 0
            for case, want in zip(cases, truth):
                rec = read_signature(render_observation(case, variants=v).text)
                got = answer(rec, policy=policy)
                hits += (got == want)
                # claim-level: did we recover every filing?
                gold = {(m, round(x, 2), k) for m, x, k in case.filings}
                mine = {(m, round(x, 2), k) for m, x, k in rec["filings"]}
                rec_ok += len(gold & mine) / max(1, len(gold))
            accs.append(hits / len(cases))
            if v == 4:
                recalls[name] = rec_ok / len(cases)
        rows[name] = accs
        print(f"{name:<26} " + " ".join(f"{a:>7.3f}" for a in accs))
    print(f"{'majority class (floor)':<26} " + " ".join(f"{base:>7.3f}" for _ in range(4)))

    print(f"\nfiling recall at V=4: " + ", ".join(
        f"{k.split(' (')[0]} {v:.3f}" for k, v in recalls.items()))
    sig, flood = rows["signature (date-aware)"], rows["latest value (FLOOD rule)"]
    print(f"\n  signature is flat across V: "
          f"{'yes' if max(sig)-min(sig) < 0.02 else 'NO'} "
          f"({min(sig):.3f}-{max(sig):.3f})")
    print(f"  the flood rule costs {statistics.mean(sig)-statistics.mean(flood):+.3f} "
          f"accuracy here")
    if statistics.mean(sig) - statistics.mean(flood) > 0.05:
        print(f"\n-> THE RULE THAT WAS RIGHT IN FLOOD IS WRONG HERE. Taking the "
              f"latest figure is\n   correct when a revision supersedes and "
              f"wrong when the question is what was\n   KNOWABLE. The reader "
              f"machinery transfers; a reader HEURISTIC does not.")
    else:
        print(f"\n-> the flood rule costs little here; the bitemporal trap is "
              f"not load-bearing\n   in this generator and the transfer test is "
              f"weak.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N_CASES, "floor": base,
                               "accuracy": rows, "filing_recall_V4": recalls},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
