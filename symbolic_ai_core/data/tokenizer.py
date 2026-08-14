"""One symbol vocabulary, shared by both tasks.

The point of this repo is to ask whether a model that predicts the next token
and a model that predicts a masked node in the graph are doing the same thing.
That question is only answerable if both are predicting out of *the same*
vocabulary, so there is exactly one tokenizer here and it is used for the
running text, for the node labels, and for the answer strings alike.

The scheme is a frequency-ranked piece vocabulary with a **byte fallback**:
anything not in the vocabulary is emitted as its UTF-8 bytes, so encoding is
lossless for every language the curriculum can be rendered in, including the
ones (Chinese, Swahili, Turkish) that share no pieces with the English default.
Nothing is learned and nothing is downloaded — the vocabulary is a JSON file
built from a sample of episodes, so a run is reproducible from its config.
"""

from __future__ import annotations

import collections
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

__all__ = ["SymbolTokenizer", "split_words", "word_spans", "PAD", "UNK", "MASK",
           "BOS", "EOS", "SEP", "SPECIALS"]

PAD, UNK, MASK, BOS, EOS, SEP = "<pad>", "<unk>", "<mask>", "<bos>", "<eos>", "<sep>"
SPECIALS = (PAD, UNK, MASK, BOS, EOS, SEP)

#: Words, numbers, and single non-alphanumerics, each optionally carrying the
#: one space that preceded it — so that decoding is plain concatenation.
#:
#: The trailing ``.`` is load-bearing and is the whole reason this is written as
#: a *total* pattern rather than an enumeration of the cases anyone thought of.
#: ``re.findall`` silently drops every character that matches no branch, so a
#: pretokenizer built from alternatives is lossy exactly where its author's
#: imagination ran out — and it was: ``_`` matches none of the first four
#: branches (``[^\W\d_]`` excludes it by name, and ``[^\s\w]`` excludes it
#: because ``_`` counts as a word character), so **underscores were deleted**.
#: ``'foo_bar_baz'`` encoded and decoded back to ``'foobarbaz'``, 9 of 85 answer
#: strings on a twelve-lesson slice could not be produced by any model however
#: good, and 28% of episode texts did not survive a round trip.
#:
#: A catch-all cannot fix a *wrong* segmentation, but it makes losing a
#: character impossible rather than unlikely, which is the property the
#: docstring on ``build`` was already claiming.
_PIECE_RE = re.compile(r" ?[^\W\d_]+|\ ?\d+|\ ?[^\s\w]|\s+|.", re.UNICODE | re.DOTALL)

#: Bare words, with no whitespace attached. Used for node labels and for
#: exploding a string-valued term into child nodes. Total for the same reason.
_WORD_RE = re.compile(r"[^\W\d_]+|\d+|[^\s\w]|[^\s]", re.UNICODE)


def split_words(text: str) -> list[str]:
    """Split into bare symbols, dropping whitespace. Used on the graph side."""
    return _WORD_RE.findall(text)


def word_spans(text: str) -> list[tuple[str, int, int]]:
    """:func:`split_words` with character offsets: ``(word, start, end)``.

    The same compiled pattern, deliberately. A causal reader of a *prefix* needs
    to know which words are finished, and the only honest way to answer that is
    with the offsets of the segmentation everything else in the repo uses — a
    second regex written to look like this one is how two components come to
    disagree about what a word is.
    """
    return [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _split_pieces(text: str) -> list[str]:
    """Split into space-carrying pieces. ``"".join`` of these is the input.

    That sentence is an invariant, not a description, and
    :func:`tests.test_data.test_the_pretokenizer_is_total` enforces it directly
    on the characters rather than on whichever lessons a fixture happened to
    draw. The previous round-trip test was real, passed, and missed this for the
    same reason a six-lesson slice missed the model ranking: it sampled the
    world instead of covering it.
    """
    return _PIECE_RE.findall(text)


@dataclass
class SymbolTokenizer:
    """A piece vocabulary with byte fallback. Deterministic and lossless."""

    itos: list[str]

    def __post_init__(self) -> None:
        self.stoi = {s: i for i, s in enumerate(self.itos)}
        self.pad_id = self.stoi[PAD]
        self.unk_id = self.stoi[UNK]
        self.mask_id = self.stoi[MASK]
        self.bos_id = self.stoi[BOS]
        self.eos_id = self.stoi[EOS]
        self.sep_id = self.stoi[SEP]
        self._byte0 = self.stoi["<0x00>"]

    def __len__(self) -> int:
        return len(self.itos)

    # ---- construction ------------------------------------------------
    @classmethod
    def build(cls, corpus: Iterable[str], *, max_vocab: int = 8192,
              min_count: int = 2) -> "SymbolTokenizer":
        """Rank pieces by frequency over ``corpus`` and keep the top ones.

        Byte tokens are always present, so a small ``max_vocab`` degrades to a
        byte-level model rather than to a lossy one.
        """
        counts: collections.Counter[str] = collections.Counter()
        for text in corpus:
            counts.update(_split_pieces(text))
        bytes_ = [f"<0x{b:02x}>" for b in range(256)]
        budget = max_vocab - len(SPECIALS) - len(bytes_)
        if budget < 0:
            raise ValueError(f"max_vocab must be at least {len(SPECIALS) + len(bytes_)}")
        kept = [p for p, c in counts.most_common() if c >= min_count][:budget]
        return cls(list(SPECIALS) + bytes_ + kept)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"itos": self.itos}, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SymbolTokenizer":
        return cls(json.loads(Path(path).read_text(encoding="utf-8"))["itos"])

    # ---- use ---------------------------------------------------------
    def _piece_ids(self, piece: str) -> list[str] | list[int]:
        i = self.stoi.get(piece)
        if i is not None:
            return [i]
        return [self._byte0 + b for b in piece.encode("utf-8")]

    def encode(self, text: str, *, bos: bool = False, eos: bool = False) -> list[int]:
        out: list[int] = [self.bos_id] if bos else []
        for piece in _split_pieces(text):
            out.extend(self._piece_ids(piece))
        if eos:
            out.append(self.eos_id)
        return out

    def decode(self, ids: Sequence[int], *, skip_special: bool = True) -> str:
        out: list[str] = []
        buf = bytearray()
        for i in ids:
            s = self.itos[i] if 0 <= i < len(self.itos) else UNK
            if s.startswith("<0x") and s.endswith(">") and len(s) == 6:
                buf.append(int(s[3:5], 16))
                continue
            if buf:
                out.append(buf.decode("utf-8", errors="replace"))
                buf.clear()
            if skip_special and s in SPECIALS:
                continue
            out.append(s)
        if buf:
            out.append(buf.decode("utf-8", errors="replace"))
        return "".join(out)

    def label_id(self, label: str) -> int:
        """A single id for a node label — the vocabulary entry if there is one.

        Node prediction is a classification, so a label has to land on one id.
        A label the vocabulary does not carry becomes ``<unk>`` and is excluded
        from the masked-node loss by :mod:`symmodels.tasks.masked_node`, which
        is honest: a target the model cannot name is not a target.
        """
        return self.stoi.get(label, self.stoi.get(" " + label, self.unk_id))
