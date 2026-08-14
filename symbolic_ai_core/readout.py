"""The readout: what a model's graph-valued output is *read as*, made a knob.

`symbolic_ai_parsers` made *text -> graph* a parameter, and the payoff was
immediate: ``gparse-003``'s six rows differ in one thing, so the spread between
them measures parsing rather than comparing models. This is the mirror-image
seam — *graph -> scored prediction* — and until now it was welded shut. There
was one readout in the repo (argmax of ``symbol_logits`` over 8,192 symbols) and
a half-generalised second one (``source_logits``, a pointer over nodes) that two
models emitted and one metric consumed.

Three measurements say the single readout is an assumption rather than a
neutral choice:

* **71.9%** of scored answers already sit on a visible node of the same
  episode. The label task is a *binding* problem scored as classification, so
  the vocabulary is the wrong codomain for two thirds of the questions asked.
* ``gparse-003`` abstains everywhere outside the answer span. It is an answer
  predictor sharing an LM head, not a language model, and 11 of 19 registered
  models cannot emit a token at all. The harness has no way to say that except
  by scoring them as though they had tried.
* ``label_acc`` and ``label_bits`` rank the models close to **inversely**,
  because one shared mixture ``(1 - c) * backoff + c * votes`` pushes deciding
  and estimating through the same scalar. Splitting *where* from *what* is a
  structural fix; retuning ``c`` is not one.

What a readout is
-----------------

``(model output, batch) -> counts``, plus ``summarize`` and — non-negotiably —
``floor``. A readout without its own fitted floor is not a readout, it is a
number: a site distribution scored without one would have been quoted against
nothing, and this repo has already published a lift over a floor that was 0.065
too low.

Channels
--------

:class:`ModelOutput` carries a ``channels`` mapping and every readout names the
one it consumes. ``source_logits`` is now ``channels["node"]`` rather than a
field with a special case around it — the seam was *generalised*, not
duplicated, which is the difference between this and a second parallel
mechanism. A model that emits nothing on a channel is **unscored** on that
readout rather than scored as zero, the same treatment ``source_logits = None``
already got.

The channels are deliberately few and are about the *codomain*, never about the
task:

``symbol``
    ``[B, L, V]`` — a distribution over the vocabulary at each site.
``type``
    ``[B, L, N_TYPES]`` — a distribution over node types.
``node``
    ``[B, L, L]`` — a pointer over the **nodes** of a graph batch. "The answer
    here is whatever that one says."
``site``
    ``[B, L, L]`` — a pointer over the **positions** of a text batch. "The head
    this token attaches under is that one." The same shape and the same seam as
    ``node``: a pointer over the sites of whichever surface the batch carries.

Scoring a pointer
-----------------

Never by index. Several nodes usually carry the same label and several words
usually spell it, so index equality marks a correct choice wrong whenever the
reader picked a different valid source. Both pointer channels are scored by
**what was picked** — the label group of the node, the word spelled at the
position — which is the rule ``_pointer_counts`` already followed and the reason
it is stated here once instead of re-derived per readout.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .data.curriculum import Episode
from .data.tokenizer import SymbolTokenizer
from .floors import Totals
from .registry import VersionedRegistry

__all__ = ["SYMBOL", "TYPE", "NODE", "SITE", "CHANNELS", "Readout",
           "HasChannels", "REGISTRY", "register", "build", "readout_names",
           "best_floor"]

#: A distribution over the vocabulary.
SYMBOL = "symbol"
#: A distribution over node types.
TYPE = "type"
#: A pointer over the nodes of a graph batch.
NODE = "node"
#: A pointer over the positions of a text batch.
SITE = "site"

CHANNELS: tuple[str, ...] = (SYMBOL, TYPE, NODE, SITE)


@runtime_checkable
class HasChannels(Protocol):
    """What a readout needs of a model output, and nothing more.

    Structural rather than nominal so that the core does not import
    :class:`symbolic_ai_models.models.base.ModelOutput`, which would invert the
    dependency ``tests/test_layering.py`` asserts. The consequence worth having
    is that anything with a ``channels`` mapping is readable — including a
    hand-built stub in a test, which is how a readout gets a unit test that does
    not have to fit a model first.
    """

    channels: Mapping[str, Any]


class Readout:
    """Turn a graph-valued output into a scored prediction over one answer space.

    Subclasses implement :meth:`score` and :meth:`floor`; :meth:`summarize` has
    a working default that reports accuracy and bits from the counts
    :meth:`score` returns, so a new readout is two methods and a docstring.

    The contract that keeps the table honest:

    * **counts, never averages.** A mean of per-batch means is not the mean when
      batches differ in how many targets they carry, and under dynamic padding
      they always do.
    * **unscored, never zero.** A model emitting nothing on :attr:`channel`
      returns ``{}`` from :meth:`score` and does not appear in that column.
      Scoring it as zero would put "has no pointer" and "has a bad pointer" in
      the same cell.
    * **its own floor.** :meth:`floor` is fitted on training episodes and scored
      on the evaluation ones, exactly as a task's floor is, and it may know the
      shape of the data and nothing about any symbol in it.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: which entry of ``ModelOutput.channels`` this readout consumes
    channel: str = SYMBOL
    #: the prefix its counts and metrics are reported under
    prefix: str = ""
    #: one line, printed by ``symbolic-ai-models readouts``
    summary: str = ""
    #: Whether this readout's number is a ceiling rather than a system's score.
    #: Greppable on purpose: "which rows in this table are ceilings" must not be
    #: a question answered by reading docstrings.
    ceiling: bool = False

    def score(self, out: HasChannels, batch: Any) -> dict[str, float]:
        """Exact counts for this readout on one batch, or ``{}`` if unscored."""
        raise NotImplementedError

    def summarize(self, totals: Totals) -> dict[str, float]:
        from .floors import ratio
        p = self.prefix or self.name
        if not totals.get(f"{p}_n"):
            return {}
        return ratio(totals, p)

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], **kwargs: Any) -> dict[str, float]:
        """What something that knows the shape and no symbol scores here."""
        raise NotImplementedError


def best_floor(candidates: Mapping[str, dict[str, float]], key: str
               ) -> dict[str, float]:
    """The strongest of several reference rules, and **which one won**.

    A floor is the one number in a table that nothing else is checked against,
    so taking a maximum over a family of cheap rules is the only way it is safe:
    a single hand-picked rule is a floor that happened to be weak. Naming the
    winner in ``floor_by`` matters for the same reason
    :func:`symbolic_ai_core.shortcuts.shortcut_table` names its winner — *which*
    cheat wins says what leaked.
    """
    best: dict[str, float] = {}
    for name, metrics in sorted(candidates.items()):
        if not best or metrics.get(key, 0.0) > best.get(key, 0.0):
            best = {**metrics, "floor_by": name}
    return best


REGISTRY: VersionedRegistry[Readout] = VersionedRegistry("readout")


def register(name: str, *, doc: str = "", channel: str = SYMBOL,
             prefix: str = "", ceiling: bool = False):
    """Register a readout under a versioned name. Same rule as everything else.

    A bare ``site`` resolves to the highest *numbered* version; a word-suffixed
    variant is a side experiment and must be asked for in full. The rule is
    shared with the model and parser registries rather than re-implemented,
    because two copies of a convention whose entire job is to keep published
    names honest is how ``ptrgen-argmax`` briefly became what ``ptrgen`` meant.
    """
    def decorate(cls: type[Readout]) -> type[Readout]:
        cls.name = name
        cls.channel = channel
        cls.prefix = prefix or cls.prefix or name
        cls.summary = doc or cls.summary
        cls.ceiling = ceiling or cls.ceiling
        REGISTRY.add(name, cls)
        return cls
    return decorate


def build(name: str, **kwargs: Any) -> Readout:
    return REGISTRY.get(name)(**kwargs)


def readout_names() -> list[str]:
    return REGISTRY.names()
