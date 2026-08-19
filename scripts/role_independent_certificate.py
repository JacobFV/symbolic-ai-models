"""A certificate that assumes nothing the reader guessed.

`certifies_insensitive` reads the roles to build its graph, so on a world whose
depot is wrong it certifies the wrong question. That is why replacing the role
flag with enumeration broke the pair's soundness: the certificate was consulted
on one arbitrary collapse.

The fix is to consume no guessed role at all -- require insensitivity to hold for
**every** candidate assignment, and require the candidates to agree. Cost is
``k`` DFS plus ``k`` solves, with ``k`` typically 1-3, because the certificate is
the cheap half.

Seed 83, the case that broke enumeration, shows the mechanism: the two
wrong-depot candidates certify and the **true** one does not, so requiring all of
them refuses it.

Run: uv run python -u scripts/role_independent_certificate.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (
    read_content_roles_checked, read_content_roles_worlds)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

sys.path.insert(0, "scripts")
from insensitivity_certificate import certifies_insensitive  # noqa: E402

OUT = Path("runs/role_independent_certificate.json")
N = 400
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def main() -> None:
    rows, widths = [], []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, headings=HEADINGS,
                                     shuffle=False)).text
        world, forced = read_content_roles_checked(text)
        try:
            got = solve(world)[0]
        except Exception:
            got = ()
        worlds = read_content_roles_worlds(text)
        widths.append(len(worlds))
        answers, certs = set(), []
        for w in worlds:
            try:
                answers.add(solve(w)[0])
            except Exception:
                answers.add(())
            certs.append(certifies_insensitive(w))
        rows.append({
            "ok": got == want, "forced": forced,
            "cert_collapsed": certifies_insensitive(world),
            "all_agree": len(answers) == 1,
            "all_certify": all(certs)})

    n = len(rows)
    policies = {
        "answer everything": lambda r: True,
        "flag + certificate": lambda r: r["forced"] and r["cert_collapsed"],
        "enumeration + certificate": lambda r: (r["all_agree"]
                                                and r["cert_collapsed"]),
        "ROLE-INDEPENDENT certificate": lambda r: (r["all_agree"]
                                                   and r["all_certify"]),
    }
    print(f"{n} non-empty cases, 400 seeds, interleaved, "
          f"hard_distractors=True\n")
    hdr = f"{'policy':<30} {'answers':>8} {'coverage':>9} {'wrong':>7} {'accuracy':>9}"
    print(hdr)
    print("-" * len(hdr))
    out = {}
    for label, accept in policies.items():
        kept = [r for r in rows if accept(r)]
        wrong = sum(not r["ok"] for r in kept)
        out[label] = {"answers": len(kept), "coverage": len(kept) / n,
                      "wrong": wrong,
                      "accuracy": 1 - wrong / len(kept) if kept else 0.0}
        v = out[label]
        print(f"{label:<30} {v['answers']:>8} {v['coverage']:>9.3f} "
              f"{v['wrong']:>7} {v['accuracy']:>9.4f}")

    flag = out["flag + certificate"]
    ind = out["ROLE-INDEPENDENT certificate"]
    print(f"\n  mean candidate worlds: {statistics.mean(widths):.2f}")
    print(f"  rule of three at n={ind['answers']}: bounds the error at "
          f"{3 / max(ind['answers'], 1):.2%}")

    print()
    if ind["wrong"] == 0 and ind["coverage"] > flag["coverage"]:
        print(f"-> IT WORKS, AND IT IS CLEANER. Requiring every candidate "
              f"assignment to certify\n   restores soundness that enumeration "
              f"lost, at {ind['coverage']:.1%} against the flag pair's "
              f"{flag['coverage']:.1%}\n   -- so dropping the guessed roles "
              f"BUYS coverage rather than costing it.")
        print(f"\n   The mechanism is visible on seed 83, the case that broke "
              f"enumeration: the two\n   wrong-depot candidates certify and the "
              f"TRUE one does not, so requiring all of\n   them refuses it. A "
              f"check that consumes no guess cannot be misled by one.")
    elif ind["wrong"] == 0:
        print(f"-> SOUND, but no cheaper: {ind['coverage']:.1%} against "
              f"{flag['coverage']:.1%}. The role flag was already\n   doing "
              f"this work implicitly.")
    else:
        print(f"-> STILL NOT SOUND: {ind['wrong']} wrong. Requiring every "
              f"candidate to certify is not\n   enough, so the phantom link is "
              f"invisible to link-insensitivity under some readings.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "rows": out,
                               "mean_worlds": statistics.mean(widths)},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
