"""``WorldCase`` — one sample, before anyone has decided what task it is for.

``Episode`` is a very specific object: a lesson id, a language, a prompt, an
answer, four choices and a term graph. That shape is one curriculum and one
family of outputs, and every task in this repo has had to be phrased in terms of
it. A world case is the general form:

```
world          the represented state, as an artifact
observations   what a reader is given -- text, a scene render, a table
queries        what is asked
targets        what a correct answer looks like, per objective
```

The point is that **one case can carry several surfaces of one world at once**
— text, term graph, world IR and a structured target — so a next-token model, a
missing-claim model and a planner can be scored on the same sample rather than
on three corpora that are only claimed to correspond.

``Episode`` is not deleted and is not wrapped away. It becomes a *view*:
:func:`language_episode_view` reads one out of a case, and
:func:`case_from_episode` builds a case around one, so every existing model and
every published number keeps working while the general object grows around it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..artifact.value import Artifact, Provenance
from .key import SampleKey

__all__ = ["WorldCase", "case_from_episode", "language_episode_view"]


@dataclass(frozen=True)
class WorldCase:
    """One addressed sample, in as many surfaces as its generator produced."""

    key: SampleKey
    world: Artifact | None = None
    observations: Mapping[str, Artifact] = field(default_factory=dict)
    queries: Mapping[str, Artifact] = field(default_factory=dict)
    targets: Mapping[str, Artifact] = field(default_factory=dict)
    provenance: Provenance = field(default_factory=Provenance)
    meta: Mapping[str, Any] = field(default_factory=dict)

    def surfaces(self) -> tuple[str, ...]:
        return tuple(sorted(self.observations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": {"dataset_id": self.key.dataset_id, "split": self.key.split,
                    "epoch": self.key.epoch, "ordinal": self.key.ordinal},
            "world": self.world.to_dict() if self.world is not None else None,
            "observations": {k: v.to_dict()
                             for k, v in sorted(self.observations.items())},
            "queries": {k: v.to_dict() for k, v in sorted(self.queries.items())},
            "targets": {k: v.to_dict() for k, v in sorted(self.targets.items())},
            "provenance": self.provenance.to_dict(),
            "meta": dict(self.meta),
        }


def case_from_episode(episode, key: SampleKey, *, dataset_id: str = "",
                      recipe: str = "") -> WorldCase:
    """Wrap one curriculum ``Episode`` as a case. Lossless.

    Every field of the episode goes somewhere a consumer can find it, and
    :func:`language_episode_view` reconstructs it exactly — which is the
    property that lets the streaming path replace the list-of-episodes path
    without redefining a single published number.
    """
    text = Artifact(type="text", value=episode.prompt,
                    profiles=("language.document",))
    graph = Artifact(type="term_graph", value=episode.graph.to_dict(),
                     schema="sai.term_graph@1", profiles=("logic.term",))
    return WorldCase(
        key=key,
        world=graph,
        observations={"text": text, "term_graph": graph},
        queries={"prompt": text,
                 "choices": Artifact(type="text_list",
                                     value=list(episode.choices))},
        targets={"answer": Artifact(type="text", value=episode.answer)},
        provenance=Provenance(producer=recipe or "symbolic_ai_data",
                              source=dataset_id, method="curriculum"),
        meta={"lesson_id": episode.lesson_id, "seed": episode.seed,
              "instance_id": episode.instance_id, "language": episode.language,
              "tags": list(episode.tags)},
    )


def language_episode_view(case: WorldCase):
    """Read a curriculum ``Episode`` back out of a case."""
    from .curriculum import Episode
    from .term_graph import TermGraph

    m = case.meta
    return Episode(
        lesson_id=str(m["lesson_id"]), seed=int(m["seed"]),
        instance_id=str(m["instance_id"]), language=str(m["language"]),
        prompt=str(case.queries["prompt"].value),
        answer=str(case.targets["answer"].value),
        choices=list(case.queries["choices"].value),
        graph=TermGraph.from_dict(case.observations["term_graph"].value),
        tags=list(m.get("tags") or []),
    )
