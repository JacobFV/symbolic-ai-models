"""The training path over an address space, with nothing materialised.

`symbolic_ai_core.data.stream` already gives batches from a keyed permutation
with a bounded window and a resumable cursor, and `tests/test_streaming.py`
proves the *key enumeration* costs the same on a 10^12-address split as on a
24-address one.

Two things that path still lacked, both named in the programme's streaming
requirements:

**A tokenizer fitted from bounded deterministic samples.** `train.build_tokenizer`
takes a ``Sequence[Episode]``, so fitting a vocabulary required the corpus to
exist. :func:`fit_tokenizer_from_stream` takes a prefix of the stream instead --
deterministic because the permutation is a pure function of
``(dataset, split, epoch, worker)``, so the same prefix yields the same
vocabulary on any machine and after any interruption.

**Proof that the whole path stays bounded**, not only the keys. Enumerating
addresses cheaply is worth nothing if generating episodes from them
materialises. :func:`peak_bytes_for` measures it end to end.

What is *not* here, deliberately: `train()` is untouched. Fifty-one published
models depend on that path, floors and one-pass rule induction both genuinely
want the whole training set, and only the batch-consuming learner benefits from
streaming. Closing the requirement does not require rewriting the trainer, and
pretending otherwise would be a refactor detached from capability.
"""

from __future__ import annotations

import tracemalloc
from typing import Any, Iterator

from symbolic_ai_core.data.stream import Cursor, stream_episodes

__all__ = ["fit_tokenizer_from_stream", "peak_bytes_for", "cursor_round_trip"]


def fit_tokenizer_from_stream(dataset, cfg, *, n_samples: int = 512,
                              split: str = "train"):
    """A vocabulary from a bounded, deterministic prefix of the stream.

    ``n_samples`` episodes are drawn in permutation order and discarded as they
    are consumed, so the corpus never exists. The prefix is the same on every
    machine and after any interruption, because the order is a pure function of
    the key rather than of a shuffled array that had to be built.
    """
    import collections

    from symbolic_ai_core.data.tokenizer import SymbolTokenizer

    reserved = int(cfg.vocab_size * cfg.label_vocab_fraction)
    cursor = Cursor(split=split)
    texts: list[str] = []
    labels: collections.Counter[str] = collections.Counter()
    for n, ep in enumerate(stream_episodes(dataset, cursor, epochs=None)):
        if n >= n_samples:
            break
        texts.append(ep.text)
        labels.update(l for l in ep.graph.labels if l)
    # The same two-part budget `train.build_tokenizer` uses: pieces from prose,
    # then whole node labels, because a label like `o2` is two pieces in text
    # and must land on one id for the masked-node head to be able to name it.
    tok = SymbolTokenizer.build(iter(texts),
                                max_vocab=max(cfg.vocab_size - reserved, 262))
    for label, _ in labels.most_common():
        if len(tok.itos) >= cfg.vocab_size:
            break
        if label not in tok.stoi:
            tok.stoi[label] = len(tok.itos)
            tok.itos.append(label)
    return tok


def _drain(iterator: Iterator[Any], n: int) -> None:
    for _, _ in zip(range(n), iterator):
        pass


def peak_bytes_for(dataset, *, n: int = 40, split: str = "train") -> int:
    """Peak traced bytes generating ``n`` episodes from ``dataset``.

    Episodes, not keys. Enumerating addresses cheaply proves nothing if turning
    an address into a case materialises the corpus behind it.
    """
    tracemalloc.start()
    _drain(stream_episodes(dataset, Cursor(split=split), epochs=None), n)
    _, top = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return top


def cursor_round_trip(cursor: Cursor) -> Cursor:
    """A cursor through a checkpoint dict and back. Small enough to sit in one."""
    return Cursor.from_dict(dict(cursor.to_dict()))
