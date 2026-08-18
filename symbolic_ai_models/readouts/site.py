"""``site``: which head does this token attach under?

The readout the corpus is privileged for, and the one nothing here has ever
asked. Every other question in the repo is answered *on* the term graph, where
the models do well, or *on* the token chain, where they do not; nothing has
asked the question that joins the two — **for this word of the rendering, which
already-read word is the head it hangs under?**

A token may attach to the phrase before it or the phrase after it, and at
different depths of the tree, and which one is right is a fact about the term
rather than about the string. The curriculum ships the true term *and* its
rendering from one seed, so the correct site has ground truth at every position,
for free, with no annotator and no estimation step.

The codomain: positions, not parse nodes
----------------------------------------

The obvious design is "the model names a node of its own parse". It cannot be
scored. Two parsers do not share an index space, and ``flat`` — the honest zero
— has no term nodes at all, only words. A site readout in parse-node indices
would have been an oracle-only readout, which is precisely the failure the whole
design is against.

The repo already settled this for the other pointer: **score a pointer by what
it picked, never by index** (``_pointer_counts`` compares ``label_group``). So
``site`` is ``[B, L, L]`` over the **token positions of the same batch** —
exactly the shape and exactly the seam of ``source_logits``, a pointer over the
sites of whichever surface the batch carries — and correctness is *word*
equality with the true attachment site, not index equality. Every parser can be
asked, including none.

Where the target comes from
---------------------------

:func:`symbolic_ai_models.prefix.availability` already computes, for each node
of the true term, how many words of the rendering must be read before its label
has been seen. Read backwards it says *which word realises which node*; walking
up to the nearest ancestor that was already realised gives *which site this word
attaches under*; and the word that spelled that ancestor is a token position.

Three consequences, each stated because each could have been a mistake:

* **Structural nodes are skipped.** ``list``, ``record``, ``tuple``, ``app`` and
  ``nil`` carry no label and therefore have no surface, so no token position
  denotes them. Walking past them to the nearest *labelled* available ancestor
  is not a convenience; it is the only thing the codomain admits.
* **Attaching at the top is a real answer, not a dropped one.** A word whose
  every available ancestor is structural, or which has none, attaches at ROOT,
  and ROOT is position 0. Dropping those would let the readout quietly select
  the positions that flatter it. ``site_root_share`` reports how much of the
  column that is, because it is the majority class and a reader is owed it.
* **This is a target and never an input.** It is computed here, task-side, from
  ``meta["graphs"]`` — the answer key — exactly as ``target_tokens`` is
  computed from the episode. No model is handed it. The one thing that can read
  the same object is the oracle prefix parser, which is why
  :class:`~symbolic_ai_models.models.gsite_001.model.GraphSiteOracle` scores
  **0.998** on the full curriculum. That number is the definition of the target
  agreeing with itself — a consistency check, asserted in
  ``tests/test_readouts.py`` — and it is not a result. The residual 0.2% is
  multi-word labels, where the head becomes readable part-way through the
  phrase attaching to it and the two walks end one node apart.

The floor
---------

Three structure-free rules, best of, fitted on training episodes and scored on
the evaluation ones:

``previous``
    attach under the word immediately before. The right-branching default, and
    on running text a strong one.
``start``
    attach at ROOT, always. The majority class.
``offset``
    the commonest *word* offset per positional context, applied blind — the same
    shape as :meth:`~symbolic_ai_models.tasks.masked_node.MaskedNode._copy_floor`,
    which learns the commonest offset to a same-label node and applies it
    without reading anything.

None of them reads a symbol. Whatever a real reader scores above the best of
them is the part that came from parsing the episode.
"""

from __future__ import annotations

import bisect
import collections
from typing import Any, Sequence

import torch

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import TermGraph
from symbolic_ai_core.data.tokenizer import SymbolTokenizer, split_words
from symbolic_ai_core.floors import Totals, ratio
from symbolic_ai_core.readout import SITE, HasChannels, Readout, best_floor, register

from ..prefix import Reading, availability

__all__ = ["SiteReadout", "site_targets", "ROOT", "words_read",
           "position_of_word", "words_at_position"]

#: What position 0 denotes. A sentinel rather than a word, so "attaches at the
#: top" can never be satisfied by accident by whichever word happens to sit at
#: the start of a left-truncated sequence. Angle brackets are not word
#: characters here, so no rendering can produce it.
ROOT = "<ROOT>"

#: `availability` uses this for "never readable from this text".
_NEVER = 1 << 30


def words_read(reading: Reading) -> list[int]:
    """``position -> how many whole words the reader has read by then``.

    ``Reading.n_complete_words`` computed once for the sequence instead of per
    query. Non-decreasing, which is what makes :func:`position_of_word` a
    bisect.
    """
    return [reading.n_complete_words(t) for t in range(len(reading.ids))]


def position_of_word(reading: Reading, read: Sequence[int] | None = None
                     ) -> list[int]:
    """``word index -> the position by which the reader has read that word``.

    Deliberately the *reader's* rule and not a character count. A prefix ending
    in an alphanumeric character does not count its final word, because ``fran``
    may yet become ``frank`` — so the position at which the last byte of a word
    arrives is **not** the position at which that word has been read, and the
    two differ by one at essentially every word of this curriculum.

    Using the character count instead would put the scored position one token
    ahead of the parse that is supposed to answer it: the reader's own parse at
    that position would not yet contain the node the word realises, and every
    row would score the same as abstention. Which is how this was written first.

    A word the sequence never finishes reading — the last one, when the sequence
    ends mid-alphanumeric — has no position and is left out.
    """
    read = list(read) if read is not None else words_read(reading)
    n = len(read)
    out: list[int] = []
    for w in range(len(reading.words)):
        t = bisect.bisect_left(read, w + 1)
        out.append(t if t < n else -1)
    return out


def words_at_position(reading: Reading, t: int,
                      read: Sequence[int] | None = None) -> frozenset[str]:
    """Everything a reader pointing at ``t`` could be naming.

    A *set*, not a word, and that is forced rather than convenient. One token
    routinely finishes two words on this curriculum — every clause ends with an
    argument and a full stop arriving together, because the conservative "the
    last word may still be growing" rule holds the argument back until the stop
    lands — so a position can denote either of them and a pointer has no way to
    say which. Naming a position is as fine-grained as this codomain gets.

    Scoring against a single word instead was the first version, and it marked
    a *third* of the corpus wrong: every sentence-final argument, pointed at
    correctly, was compared against ``.``.
    """
    if t <= 0:
        return frozenset({ROOT})
    read = read if read is not None else words_read(reading)
    if t >= len(read):
        return frozenset({ROOT})
    lo, hi = read[t - 1], read[t]
    if hi <= lo:
        # No word became readable here, so the position denotes the last one
        # that did — a pointer into the middle of a word is still a pointer at
        # the word.
        return frozenset({reading.words[hi - 1].lower()}) if hi else frozenset({ROOT})
    return frozenset(w.lower() for w in reading.words[lo:hi])


def site_targets(graph: TermGraph, reading: Reading
                 ) -> dict[int, tuple[int, str]]:
    """``{position: (the site's position, the site's word)}`` for one sequence.

    A position is scored exactly when the word completing there realises a
    labelled node of the true term. Everything else — function words, the
    scaffolding, the answer line — is unasked rather than wrong.

    The site is the nearest ancestor of that node whose label had *already* been
    read when the word began, so it is always strictly earlier in the sequence
    and the readout cannot be satisfied by looking forward.
    """
    words = reading.words
    if not words or not len(graph):
        return {}
    need = availability(graph, words)
    keys = [tuple(p.lower() for p in split_words(lab)) if lab else ()
            for lab in graph.labels]
    read = words_read(reading)
    at = position_of_word(reading, read)

    #: last word index of a node's realisation -> (node, first word index)
    realised: dict[int, tuple[int, int]] = {}
    for i, key in enumerate(keys):
        if not key or need[i] >= _NEVER:
            continue
        realised.setdefault(need[i] - 1, (i, need[i] - len(key)))

    out: dict[int, tuple[int, str]] = {}
    for last_word, (node, first_word) in sorted(realised.items()):
        t = at[last_word]
        if t <= 0:
            continue                      # nothing earlier to attach under
        p = graph.parent[node]
        site = -1
        while 0 <= p < len(graph):
            # Already read *before* this word began: `need[p] <= first_word`.
            # A structural node has no surface, so it is walked past rather than
            # pointed at -- see the module docstring.
            if keys[p] and need[p] <= first_word:
                site = p
                break
            p = graph.parent[p]
        if site < 0:
            out[t] = (0, ROOT)
            continue
        w = need[site] - 1
        j = at[w]
        # One token can finish two words, and then the site and the word
        # attaching to it land on the same position. Pointing at itself is not
        # an answer, so the position is left unasked rather than scored against
        # a target no pointer could name.
        if 0 <= j < t:
            out[t] = (j, words[w].lower())
    return out


def _episode_targets(episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                     max_len: int) -> list[tuple[Reading, dict]]:
    """The readings and targets for a set of episodes, built once.

    Encoded exactly as ``collate_text`` encodes — the same two halves, the same
    left truncation — because a target computed from a differently built
    sequence is a target for a different question.
    """
    out: list[tuple[Reading, dict]] = []
    for ep in episodes:
        ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
        ids = ids[max(len(ids) - max_len, 0):]
        reading = Reading(ids, tok)
        out.append((reading, site_targets(ep.graph, reading)))
    return out


@register("site-001", channel=SITE, prefix="site",
          doc="Which already-read word is the head this token attaches under.")
class SiteReadout(Readout):
    """Attachment on the text surface, scored by what was pointed at.

    Reads ``ModelOutput.channels['site']``. A model that emits nothing there is
    **unscored** rather than scored as zero: "cannot point" and "points badly"
    are different facts and one column cannot hold both.
    """

    def __init__(self, max_len: int = 512) -> None:
        self.max_len = max_len

    # ---- scoring --------------------------------------------------------
    def score(self, out: HasChannels, batch: Any) -> dict[str, float]:
        logits = out.channels.get(SITE)
        graphs = (batch.meta or {}).get("graphs")
        if logits is None or not graphs or batch.rel is not None:
            return {}
        tok = (batch.meta or {}).get("tokenizer")
        if tok is None:
            return {}

        tokens = batch.tokens.tolist()
        lengths = batch.pad_mask.sum(1).tolist()
        n = hits = root = 0
        nll = 0.0
        logp = torch.log_softmax(logits.float(), dim=-1)
        for b, graph in enumerate(graphs):
            ids = tokens[b][:int(lengths[b])]
            if not ids:
                continue
            reading = Reading(ids, tok)
            targets = site_targets(graph, reading)
            if not targets:
                continue
            read = words_read(reading)
            for t, (site, key) in targets.items():
                if not 0 <= t < logits.shape[1]:
                    continue
                n += 1
                root += key == ROOT
                picked = int(logp[b, t, :len(ids)].argmax())
                hits += key in words_at_position(reading, picked, read)
                # Bits are charged against the *stated* site, not against the
                # equivalence class: a distribution that spread its mass over
                # six spellings of the right word has not said where the head
                # is, and the accuracy column already forgives it.
                nll += -float(logp[b, t, site])
        if not n:
            return {}
        return {"site_n": float(n), "site_correct": float(hits),
                "site_nll": nll, "site_root": float(root)}

    def summarize(self, totals: Totals) -> dict[str, float]:
        if not totals.get("site_n"):
            return {}
        out = ratio(totals, "site")
        # The majority class, reported next to the score rather than left for a
        # reader to wonder about. `start` is one of the floor's own rules, so
        # this is also the number that says how much of the floor is that rule.
        out["site_root_share"] = totals["site_root"] / totals["site_n"]
        return out

    # ---- the floor ------------------------------------------------------
    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], **kwargs: Any) -> dict[str, float]:
        """Best of three structure-free rules, and which one won."""
        fitted = _episode_targets(train, tok, max_len=self.max_len)
        scored = _episode_targets(episodes, tok, max_len=self.max_len)

        # `offset`: the commonest word offset per positional context, counted on
        # training episodes. Positional, so it reads no symbol -- the same
        # commitment the masked-node floor's structural key makes.
        table: dict[int, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for reading, targets in fitted:
            read = words_read(reading)
            at = position_of_word(reading, read)
            back = {p: w for w, p in enumerate(at) if p >= 0}
            for t, (site, _) in targets.items():
                w_here, w_site = back.get(t), back.get(site)
                if w_here is None:
                    continue
                table[min(w_here, 12)][w_here - (w_site if w_site is not None
                                                 else -1)] += 1
        overall: collections.Counter = collections.Counter()
        for counts in table.values():
            overall.update(counts)
        fallback = overall.most_common(1)[0][0] if overall else 1

        rules = {"previous": 0, "start": 0, "offset": 0}
        total = 0
        for reading, targets in scored:
            read = words_read(reading)
            at = position_of_word(reading, read)
            back = {p: w for w, p in enumerate(at) if p >= 0}
            for t, (_, key) in targets.items():
                total += 1
                rules["previous"] += key in words_at_position(reading, t - 1, read)
                rules["start"] += key == ROOT
                w_here = back.get(t)
                if w_here is None:
                    continue
                counts = table.get(min(w_here, 12))
                d = counts.most_common(1)[0][0] if counts else fallback
                j = w_here - d
                guess = at[j] if 0 <= j < len(at) and at[j] >= 0 else 0
                rules["offset"] += key in words_at_position(reading, guess, read)
        if not total:
            return {"site_acc": float("nan"), "site_n": 0.0}
        best = best_floor(
            {name: {"site_acc": hits / total, "site_n": float(total)}
             for name, hits in rules.items()}, "site_acc")
        # Namespaced, because a run's floors are one flat dict per task and an
        # unqualified `floor_by` would be claimed by whichever readout ran last.
        best["site_floor_by"] = best.pop("floor_by", "")
        return best
