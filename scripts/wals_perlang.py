"""Per-language claw reliabilities, one language per process-step, resumable.

Four attempts to fit one model over all 46 languages in a single process were
killed (exit 137) before printing a line. The measurement does not need a single
fit: what the typology correlation consumes is a *per-language* vector of claw
reliabilities, and that is estimable one language at a time. Each language is
written to its own JSON the moment it finishes, so an interrupted run resumes
instead of restarting.

The cost of doing it this way is stated rather than hidden: each language gets
its own tokenizer and its own fit, so this is the *bucketed* design, not the
conditioned one. For a per-language reliability estimate the two agree -- the
conditioned model's `claw_evidence` is keyed by language anyway -- but a claim
about conditioning cannot be read off this.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

from symbolic_ai_core.data.curriculum import generate, lesson_ids
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.train import TrainConfig, build_tokenizer
import symbolic_ai_core.data.langdb as L

OUT = Path("runs/wals46_perlang")
MODEL = "omegaclaw_textlang-002"


def one(code: str, n_train: int = 5) -> dict:
    lessons = lesson_ids()
    eps = list(generate(lessons, n=n_train, language=code))
    tok = build_tokenizer(TrainConfig(vocab_size=4096), eps)
    m = build(MODEL, ModelConfig(vocab_size=len(tok), max_len=320,
                                 max_nodes=128, extra={"max_examples": 6000}))
    m.fit_on(eps, tok)
    return {"code": code, "episodes": len(eps),
            "totals": {k: list(v) for k, v in m.claw_totals.items()},
            "reliability": {k: m.reliability(k) for k in m.claw_totals}}


def main(argv):
    L.enable()
    OUT.mkdir(parents=True, exist_ok=True)
    codes = argv[0].split(",")
    for code in codes:
        dest = OUT / f"{code}.json"
        if dest.exists():
            continue
        t = time.time()
        try:
            dest.write_text(json.dumps(one(code), indent=1), encoding="utf-8")
            print(f"{code} ok {time.time()-t:.0f}s", flush=True)
        except Exception as e:                                # keep going
            print(f"{code} FAILED {type(e).__name__}: {e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
