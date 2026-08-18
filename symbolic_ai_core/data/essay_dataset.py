"""The essay generator as an **address space**, and a source it does not assume.

``essay.generate`` draws topics by sampling a pool, which makes an essay a pure
function of ``(topic, seed)`` but not of an *address* — you cannot ask for the
137th essay without drawing the first 136. This wraps it the way
:mod:`symbolic_ai_core.data.dataset` wraps the curriculum: ordinal *n* factors
into a topic and a seed, so the 137th is one call.

The source is named by the recipe and resolved through the knowledge-graph
registry, and its **capabilities are checked at construction** rather than at
sample time. That is the point of item 7: the generator stops assuming WordNet,
and a source that cannot drive it is refused by name before a corpus exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence

from ..artifact.value import Artifact, Provenance
from .case import WorldCase
from .dataset import SplitSpec
from .key import SampleKey, keyed_seed, positions

__all__ = ["EssayDataset"]


@dataclass
class EssayDataset:
    """Multi-paragraph essays over a named knowledge source, addressed."""

    source: str
    dataset_id: str = "kg_essays"
    width: int = 4
    max_sections: int = 5
    min_sections: int = 3
    splits: dict[str, SplitSpec] = field(default_factory=dict)
    recipe_hash: str = ""
    _kg: Any = field(default=None, repr=False)
    _pool: tuple[int, ...] = field(default=(), repr=False)
    _coverage: Mapping[str, float] = field(default_factory=dict, repr=False)

    # ---- construction -------------------------------------------------
    def __post_init__(self) -> None:
        if not self.splits:
            self.splits = {"train": SplitSpec(seed0=0, per_lesson=1_000),
                           "eval": SplitSpec(seed0=1_000_000, per_lesson=4,
                                             shuffle=False, finite=True)}
        self._ensure()

    def _ensure(self) -> None:
        if self._kg is not None:
            return
        from symbolic_ai_kg import load as load_kg

        from .essay import REQUIRED, rich_topics, sections_available
        from .knowledge_source import capabilities_of, require_capabilities

        kg = load_kg(self.source)
        require_capabilities(
            capabilities_of(kg, name=self.source, names=REQUIRED), REQUIRED,
            who=f"the essay generator on source {self.source!r}")
        self._kg = kg
        self._pool = tuple(rich_topics(kg, min_sections=self.min_sections))
        if not self._pool:
            raise ValueError(
                f"source {self.source!r} has no topic with "
                f"{self.min_sections} populated sections, so it can produce "
                f"paragraphs but not essays")
        self._coverage = sections_available(kg, name=self.source)

    @classmethod
    def from_recipe(cls, recipe, params: Mapping[str, Any]) -> "EssayDataset":
        source = str(params.get("source") or _source_of(recipe))
        return cls(source=source, dataset_id=recipe.id,
                   width=int(params.get("width", 4)),
                   max_sections=int(params.get("max_sections", 5)),
                   min_sections=int(params.get("min_sections", 3)),
                   splits=recipe.splits or {}, recipe_hash=recipe.hash)

    # ---- coverage, carried rather than assumed ------------------------
    @property
    def coverage(self) -> Mapping[str, float]:
        """Per rhetorical section, how populated this source is.

        Attached to the dataset so a corpus carries the fact that three of its
        eight sections are unreachable on WordNet, instead of that being
        discoverable only by someone who thought to look.
        """
        return dict(self._coverage)

    def dead_sections(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, v in self._coverage.items() if v == 0.0))

    # ---- the address space --------------------------------------------
    @property
    def n_topics(self) -> int:
        return len(self._pool)

    def block(self, split: str) -> int:
        return self.n_topics * self.splits[split].per_lesson

    def address(self, split: str, ordinal: int) -> tuple[int, int]:
        """``ordinal -> (topic, seed)``. Topic-minor, so any prefix covers the
        whole topic pool rather than being many seeds of the first topic."""
        spec = self.splits[split]
        return (self._pool[ordinal % self.n_topics],
                spec.seed0 + ordinal // self.n_topics)

    def keys(self, split: str, *, epoch: int = 0, worker: int = 0,
             workers: int = 1) -> Iterator[SampleKey]:
        spec = self.splits[split]
        if spec.finite and epoch != 0:
            raise ValueError(f"split {split!r} is finite and pinned")
        key = keyed_seed(self.dataset_id, split, self.source, self.recipe_hash)
        for ordinal in positions(block=self.block(split), epoch=epoch,
                                 worker=worker, workers=workers, key=key,
                                 shuffle=spec.shuffle):
            yield SampleKey(self.dataset_id, split, epoch, ordinal)

    # ---- the sample ----------------------------------------------------
    def essay(self, key: SampleKey):
        from .essay import plan, realise

        topic, seed = self.address(key.split, key.ordinal)
        secs = plan(self._kg, topic, seed=seed, width=self.width,
                    max_sections=self.max_sections)
        return realise(self._kg, topic, secs, seed=seed)

    def get(self, key: SampleKey) -> WorldCase:
        e = self.essay(key)
        text = Artifact(type="text", value=e.text,
                        profiles=("language.document",))
        spans = Artifact(type="json", value=[
            {"start": m.start, "end": m.end, "node": m.node,
             "antecedent": m.antecedent} for m in e.mentions],
            profiles=("language.mention", "language.reference"))
        return WorldCase(
            key=key, world=spans,
            observations={"text": text, "mentions": spans},
            queries={"prompt": text},
            targets={"inference": Artifact(type="json", value=list(e.inference)
                                           if e.inference else None,
                                           present=e.inference is not None)},
            provenance=Provenance(producer=self.dataset_id, source=self.source,
                                  method="kg essay realisation"),
            meta={"topic": e.topic, "topic_word": e.topic_word, "seed": e.seed,
                  "kg": e.kg, "n_paragraphs": len(e.paragraphs),
                  "n_sentences": len(e.sentences),
                  "n_mentions": len(e.mentions),
                  "dead_sections": list(self.dead_sections())})

    def __getstate__(self):
        d = dict(self.__dict__)
        d["_kg"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._ensure()


def _source_of(recipe) -> str:
    """The knowledge source a recipe draws on, from its first snapshot ref."""
    from ..source.manifest import parse_ref

    for ref in recipe.sources:
        cls, ident = parse_ref(ref)
        if cls in ("snapshot", "source"):
            return ident.split("@", 1)[0]
    raise ValueError(f"recipe {recipe.id!r} names no source to draw on")
