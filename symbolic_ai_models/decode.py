"""Sampling continuations, for looking at rather than for scoring.

Every number this repo reports is teacher-forced: the model is shown the true
prefix and asked how much probability it puts on the true next symbol. That is
what language models are trained on and it is the right thing to measure, but it
is a poor thing to *read*. A model with a respectable cross-entropy can still
produce nonsense the moment it has to stand on its own output, and no aggregate
will show you that. This module exists so a person — or a large pretrained model
acting as a reviewer — can look at what actually comes out.

It is deliberately outside the evaluation path. Nothing here feeds a metric,
nothing here is compared against a floor, and no score in ``summary.json``
depends on it. Treat it as a window, not a benchmark: sampled text is evidence
about a model, and turning it into a number would need a judge whose own biases
would then be in the result.

The one nice consequence of the shared interface is that this works for both
families unchanged. A decision list and a transformer both answer
``forward(batch) -> logits``, so the same sampler decodes from either, and you
can read a rule-based model's continuations next to a network's.

There is no KV cache: each step re-runs the model over the whole prefix. That
is quadratic and completely fine at the volumes qualitative review runs at, and
it keeps the decoder honest — it is the same forward pass the metrics use, with
nothing bolted on that could diverge from it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import torch

from .data.batch import text_batch
from .data.curriculum import Episode
from .data.tokenizer import SymbolTokenizer
from .models.base import Model

__all__ = ["SamplingConfig", "Generation", "Sample", "generate",
           "sample_episodes", "transcript", "write_json"]


@dataclass
class SamplingConfig:
    """How to decode. Greedy by default, because the first question a reviewer
    has is what the model actually believes, not what it might say."""

    max_new_tokens: int = 24
    greedy: bool = True
    temperature: float = 1.0
    top_k: int = 0
    top_p: float = 0.0
    #: Answers occupy one line, so a newline ends the continuation.
    stop_on_newline: bool = True
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Generation:
    """One continuation, with enough detail to judge it by."""

    text: str
    token_ids: list[int] = field(default_factory=list)
    pieces: list[str] = field(default_factory=list)
    logprobs: list[float] = field(default_factory=list)
    stopped: str = "length"          # eos | newline | length

    @property
    def mean_logprob(self) -> float:
        return sum(self.logprobs) / len(self.logprobs) if self.logprobs else float("nan")


@dataclass
class Sample:
    """A prompt, what the model said, and what the curriculum wanted."""

    lesson_id: str
    instance_id: str
    seed: int
    prompt: str
    gold: str
    generated: str
    exact_match: bool
    mean_logprob: float
    stopped: str
    choices: list[str] = field(default_factory=list)

    @property
    def in_answer_set(self) -> bool:
        """Whether the continuation is even one of the offered options.

        Weaker than being right and much more informative early on: a model that
        cannot yet answer but has learned to emit *something from the answer
        set* is in a different state from one producing free-form noise.
        """
        return self.generated.strip() in {c.strip() for c in self.choices}

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["in_answer_set"] = self.in_answer_set
        return d


# ---------------------------------------------------------------------------
# decoding
# ---------------------------------------------------------------------------
@torch.no_grad()
def generate(model: Model, tok: SymbolTokenizer, prompt: str, *,
             config: SamplingConfig | None = None,
             device: torch.device | str = "cpu") -> Generation:
    """Continue ``prompt`` one token at a time.

    The prompt is fed exactly as training saw it — ``<bos> prompt \\n`` — so the
    model is standing where the answer began in every episode it was fitted on.
    """
    cfg = config or SamplingConfig()
    was_training = model.training
    model.eval()
    rng = torch.Generator().manual_seed(cfg.seed)

    ids = tok.encode(prompt, bos=True)
    produced: list[int] = []
    logprobs: list[float] = []
    stopped = "length"

    for _ in range(max(cfg.max_new_tokens, 0)):
        logits = model(text_batch(ids, tok, device)).symbol_logits[0, -1].float().cpu()
        nxt = _pick(logits, cfg, rng)
        if nxt in (tok.eos_id, tok.pad_id):
            stopped = "eos"
            break
        piece = tok.itos[nxt]
        if cfg.stop_on_newline and "\n" in piece:
            stopped = "newline"
            break
        logprobs.append(float(torch.log_softmax(logits, -1)[nxt]))
        produced.append(nxt)
        ids.append(nxt)

    if was_training:
        model.train()
    return Generation(text=tok.decode(produced), token_ids=produced,
                      pieces=[tok.itos[i] for i in produced],
                      logprobs=logprobs, stopped=stopped)


def _pick(logits: torch.Tensor, cfg: SamplingConfig,
          rng: torch.Generator) -> int:
    """Greedy, or temperature with optional top-k / top-p truncation."""
    if cfg.greedy:
        return int(logits.argmax())
    scaled = logits / max(cfg.temperature, 1e-6)
    if cfg.top_k > 0:
        kth = torch.topk(scaled, min(cfg.top_k, scaled.numel())).values[-1]
        scaled = scaled.masked_fill(scaled < kth, float("-inf"))
    if 0.0 < cfg.top_p < 1.0:
        order = torch.argsort(scaled, descending=True)
        keep = torch.cumsum(torch.softmax(scaled[order], -1), -1) - \
            torch.softmax(scaled[order], -1) < cfg.top_p
        drop = order[~keep]
        scaled = scaled.index_fill(0, drop, float("-inf"))
    return int(torch.multinomial(torch.softmax(scaled, -1), 1, generator=rng))


def sample_episodes(model: Model, tok: SymbolTokenizer,
                    episodes: Sequence[Episode], *,
                    config: SamplingConfig | None = None,
                    device: torch.device | str = "cpu") -> list[Sample]:
    """Decode a continuation for each episode, from the prompt alone.

    The answer never enters the input: the model is given ``prompt + "\\n"`` and
    has to produce the rest. ``gold`` travels alongside for the reader's
    benefit, not the model's.
    """
    cfg = config or SamplingConfig()
    out: list[Sample] = []
    for i, ep in enumerate(episodes):
        # Vary the seed per episode so sampling does not repeat one draw.
        step = SamplingConfig(**{**cfg.to_dict(), "seed": cfg.seed + i})
        gen = generate(model, tok, ep.prompt + "\n", config=step, device=device)
        out.append(Sample(
            lesson_id=ep.lesson_id, instance_id=ep.instance_id, seed=ep.seed,
            prompt=ep.prompt, gold=ep.answer, generated=gen.text,
            exact_match=gen.text.strip() == ep.answer.strip(),
            mean_logprob=gen.mean_logprob, stopped=gen.stopped,
            choices=list(ep.choices)))
    return out


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------
def transcript(samples: Sequence[Sample], *, show_prompt: bool = True,
               limit: int = 0) -> str:
    """A readable transcript, for a person.

    The summary lines at the end are counts, not scores: how often the model hit
    the answer exactly and how often it produced something that was at least one
    of the options. Neither is reported as a metric anywhere else, and neither
    has a floor attached, because this file is for looking rather than ranking.
    """
    rows = list(samples)[:limit] if limit else list(samples)
    parts: list[str] = []
    for s in rows:
        mark = "OK  " if s.exact_match else ("set " if s.in_answer_set else "    ")
        parts.append(f"=== {mark} {s.lesson_id}  seed={s.seed}")
        if show_prompt:
            parts.append(_indent(s.prompt))
        parts.append(f"  gold      : {s.gold!r}")
        parts.append(f"  generated : {s.generated!r}"
                     f"   [{s.stopped}, mean logp {s.mean_logprob:.3f}]")
        parts.append("")

    total = len(samples)
    exact = sum(s.exact_match for s in samples)
    in_set = sum(s.in_answer_set for s in samples)
    parts.append("-" * 60)
    parts.append(f"{total} samples | exact {exact} ({_pct(exact, total)}) | "
                 f"in answer set {in_set} ({_pct(in_set, total)})")
    parts.append("counts, not a metric: sampling is outside the evaluation path")
    return "\n".join(parts)


def write_json(path: str | Path, samples: Sequence[Sample], *,
               model: str = "", config: SamplingConfig | None = None) -> Path:
    """Dump samples as JSON, for a reviewer that is itself a model.

    Flat records with the prompt, the gold answer and the continuation, which is
    what a frontier model needs to grade a batch without being handed this
    repo's vocabulary or conventions.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "model": model,
        "sampling": (config or SamplingConfig()).to_dict(),
        "n": len(samples),
        "samples": [s.to_dict() for s in samples],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def _indent(text: str, prefix: str = "  | ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"
