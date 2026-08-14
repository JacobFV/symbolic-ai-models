"""Is the script effect a script effect, or just "this language translates more"?

Held-out retention for `polycky-001` splits 0.78 for the 34 Latin-script
languages against 0.47 for the twelve that are the only language in the corpus
written in their script. Before that is a fact about orthography it has to
survive the obvious alternative: a language that leaves most of the English
frame in place will retain well for a reason that has nothing to do with script
and nothing to do with the parser.

So the alternative is measured rather than argued about. For each language,
**untranslated share** is the fraction of the English rendering's tokens that
survive verbatim into that language's rendering of the *same seed* — computable
exactly, because the corpus is parallel and the graph is byte-identical. Then
retention is correlated with the script indicator and with untranslated share,
and each is partialled out of the other.

This is the parser-side analogue of the Mantel test in
`scripts/language_typology.py`, and it is run for the same reason: the graded
language representation over these 46 languages correlates with script at
r +0.18 and with the WALS features the renderer never reads at a null, so
orthography is the live confound for anything language-conditioned here.

Training seeds only. Retention comes from `runs/polyglot/`, which is the
authority; nothing is refitted here.

    uv run python scripts/polyglot_script_control.py
"""

from __future__ import annotations

import json
import pathlib
import statistics

from symbolic_ai_core.data import langdb
from symbolic_ai_core.data.curriculum import generate, resolve_lessons
from symbolic_ai_parsers.polyglot import WALS46, scripts
from symbolic_ai_parsers.segment import words

RUNS = pathlib.Path("runs/polyglot")
#: Enough episodes for a stable overlap estimate and few enough that the step
#: is a minute rather than twenty. The quantity is a property of the renderer,
#: not of the draw, so it converges fast.
N_LESSONS, N_EPISODES = 24, 2


def untranslated_share(codes, lessons, n=N_EPISODES, split=words
                       ) -> dict[str, float]:
    """Share of the English rendering's tokens that survive into each language.

    ``split`` is a parameter because the covariate must not be measured with an
    instrument whose own effect is under test. The script-aware splitter emits
    one token per ideograph and the shared one emits whole runs, so they count
    overlap differently for exactly the languages this analysis is about. Both
    are computed and the correlation is reported under each.
    """
    base = {ep.instance_id: set(split(ep.prompt))
            for ep in generate(lessons, n=n, seed0=0, language="english",
                               max_nodes=128, on_error="skip")}
    out: dict[str, float] = {}
    for code in codes:
        rows = []
        for ep in generate(lessons, n=n, seed0=0, language=code, max_nodes=128,
                           on_error="skip"):
            en = base.get(ep.instance_id)
            if en:
                rows.append(len(en & set(split(ep.prompt))) / len(en))
        out[code] = statistics.fmean(rows) if rows else float("nan")
    return out


def clause_coverage(codes, lessons, n=N_EPISODES) -> dict[str, float]:
    """Per-language `Treebank.coverage`: the share of clause-shaped graph nodes
    that found a segment at all.

    The third candidate explanation, and the one hardest to tell apart from the
    other two from the outside. Everything downstream is capped by it, it is
    language-dependent (0.79 English against 0.63 Chinese), and if retention
    tracks it then retention is a statement about the span heuristic rather than
    about the parser.
    """
    from symbolic_ai_parsers.treebank import Treebank

    out: dict[str, float] = {}
    for code in codes:
        eps = list(generate(lessons, n=n, seed0=0, language=code,
                            max_nodes=128, on_error="skip"))
        out[code] = Treebank.build(eps, words).coverage
    return out


def pearson(xs, ys) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx > 1e-12 and dy > 1e-12 else float("nan")


def partial(xs, ys, zs) -> float:
    """r(x, y | z), the usual first-order partial correlation."""
    rxy, rxz, ryz = pearson(xs, ys), pearson(xs, zs), pearson(ys, zs)
    den = ((1 - rxz ** 2) * (1 - ryz ** 2)) ** 0.5
    return (rxy - rxz * ryz) / den if den > 1e-12 else float("nan")


def held_out(metric: str = "bracket_f1", parser: str = "polycky-001"
             ) -> dict[str, float]:
    held: dict[str, float] = {}
    for p in sorted(RUNS.glob("fold-*.json")):
        step = json.loads(p.read_text(encoding="utf-8"))
        row = {r["parser"]: r for r in step["parsers"]}[parser]
        for lang, cell in row["per_language"].items():
            held[lang] = cell["scores"][metric]
    return held


def retention(metric: str = "bracket_f1", parser: str = "polycky-001"
              ) -> dict[str, float]:
    mix = json.loads((RUNS / "mixture-0.json").read_text(encoding="utf-8"))
    ins = {r["parser"]: r for r in mix["parsers"]}[parser]["per_language"]
    held = held_out(metric, parser)
    return {l: held[l] / ins[l]["scores"][metric]
            for l in sorted(held)
            if l in ins and ins[l]["scores"][metric] > 1e-9}


def main() -> int:
    langdb.enable()
    lessons = resolve_lessons(None)[:N_LESSONS]
    keep = retention()
    codes = sorted(keep)
    share = untranslated_share(codes, lessons)
    sc = scripts(codes)

    ys = [keep[c] for c in codes]
    zs = [share[c] for c in codes]
    xs = [0.0 if sc[c] == "Latn" else 1.0 for c in codes]     # novel script

    # Where does the abstraction actually earn its keep? If replacing frame
    # words with classes is a real mechanism rather than a lexical accident, it
    # should pay *most* in the languages that translate most — the ones where a
    # literal right-hand side has nothing left to match.
    lit = retention(parser="polycky-literal")
    gain = [keep[c] - lit[c] for c in codes if c in lit]
    gz = [share[c] for c in codes if c in lit]
    gx = [0.0 if sc[c] == "Latn" else 1.0 for c in codes if c in lit]

    out = {
        "metric": "bracket_f1", "parser": "polycky-001",
        "r_abstraction_gain_untranslated": pearson(gz, gain),
        "r_abstraction_gain_novelscript": pearson(gx, gain),
        "mean_abstraction_gain": statistics.fmean(gain),
        "n_languages": len(codes), "n_lessons": len(lessons),
        "r_retention_novelscript": pearson(xs, ys),
        "r_retention_untranslated": pearson(zs, ys),
        "r_novelscript_untranslated": pearson(xs, zs),
        "partial_retention_novelscript_given_untranslated": partial(xs, ys, zs),
        "partial_retention_untranslated_given_novelscript": partial(zs, ys, xs),
        "per_language": {c: {"retention": keep[c], "untranslated": share[c],
                             "script": sc[c]} for c in codes},
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / "script_control.json").write_text(json.dumps(out, indent=1),
                                              encoding="utf-8")

    print(f"{len(codes)} languages, retention of polycky-001 on bracket_f1\n")
    print(f"{'correlate':<44}{'r':>8}")
    print("-" * 52)
    print(f"{'novel script (1/0)':<44}{out['r_retention_novelscript']:>8.3f}")
    print(f"{'untranslated share':<44}"
          f"{out['r_retention_untranslated']:>8.3f}")
    print(f"{'  ... and the two correlates with each other':<44}"
          f"{out['r_novelscript_untranslated']:>8.3f}")
    print("\npartial correlations with retention")
    print(f"{'novel script | untranslated share':<44}"
          f"{out['partial_retention_novelscript_given_untranslated']:>8.3f}")
    print(f"{'untranslated share | novel script':<44}"
          f"{out['partial_retention_untranslated_given_novelscript']:>8.3f}")
    print("\nwhere the abstraction pays: retention(polycky-001) - "
          "retention(polycky-literal)")
    print(f"{'  mean gain in retention':<44}"
          f"{out['mean_abstraction_gain']:>8.3f}")
    print(f"{'  vs untranslated share':<44}"
          f"{out['r_abstraction_gain_untranslated']:>8.3f}")
    print(f"{'  vs novel script':<44}"
          f"{out['r_abstraction_gain_novelscript']:>8.3f}")

    # The section above rests entirely on `retention`, which is a ratio of two
    # small numbers. If the correlation is a property of that statistic rather
    # than of the corpus it will not survive being recomputed on a different
    # metric or on the raw held-out score, so it is recomputed on both here
    # rather than left as a caveat for someone else.
    print("\nrobustness: the same correlation on other read-outs")
    print(f"{'read-out':<44}{'untr.':>8}{'script':>8}")
    print("-" * 60)
    robust = {}
    for label, ys2 in (
            ("retention, bracket_f1", ys),
            ("retention, edge_f1",
             [retention("edge_f1")[c] for c in codes]),
            ("retention, label_f1",
             [retention("label_f1")[c] for c in codes]),
            ("raw held-out bracket_f1",
             [held_out("bracket_f1")[c] for c in codes]),
            ("raw held-out edge_f1",
             [held_out("edge_f1")[c] for c in codes]),
    ):
        ru, rs = pearson(zs, ys2), pearson(xs, ys2)
        robust[label] = {"untranslated": ru, "novel_script": rs,
                         "partial_untranslated": partial(zs, ys2, xs),
                         "partial_novel_script": partial(xs, ys2, zs)}
        print(f"{label:<44}{ru:>8.3f}{rs:>8.3f}")
    out["robustness"] = robust

    # And the same, with the covariate measured by the *shared* splitter, so
    # that the corpus-side quantity does not depend on the instrument whose own
    # parser-side effect came out null.
    from symbolic_ai_core.data.tokenizer import split_words

    share_v1 = untranslated_share(codes, lessons, split=split_words)
    z1 = [share_v1[c] for c in codes]
    out["untranslated_split_words"] = {
        "r_retention": pearson(z1, ys),
        "partial_given_novelscript": partial(z1, ys, xs),
        "r_with_script_aware": pearson(z1, zs),
    }
    print("\nthe covariate, measured with the shared split_words instead")
    print(f"{'  r with retention':<44}"
          f"{out['untranslated_split_words']['r_retention']:>8.3f}")
    print(f"{'  ... script partialled out':<44}"
          f"{out['untranslated_split_words']['partial_given_novelscript']:>8.3f}")
    print(f"{'  agreement between the two instruments':<44}"
          f"{out['untranslated_split_words']['r_with_script_aware']:>8.3f}")

    # The third candidate: is retention really about the span heuristic?
    cov = clause_coverage(codes, lessons)
    cs = [cov[c] for c in codes]
    out["clause_coverage"] = {
        "per_language": cov,
        "r_retention": pearson(cs, ys),
        "r_with_untranslated": pearson(cs, zs),
        "partial_retention_coverage_given_untranslated": partial(cs, ys, zs),
        "partial_retention_untranslated_given_coverage": partial(zs, ys, cs),
    }
    c = out["clause_coverage"]
    print("\nthe third candidate: per-language treebank clause coverage")
    print(f"{'  r with retention':<44}{c['r_retention']:>8.3f}")
    print(f"{'  r with untranslated share':<44}"
          f"{c['r_with_untranslated']:>8.3f}")
    print(f"{'  coverage | untranslated share':<44}"
          f"{c['partial_retention_coverage_given_untranslated']:>8.3f}")
    print(f"{'  untranslated share | coverage':<44}"
          f"{c['partial_retention_untranslated_given_coverage']:>8.3f}")

    (RUNS / "script_control.json").write_text(json.dumps(out, indent=1),
                                              encoding="utf-8")
    return 0


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
