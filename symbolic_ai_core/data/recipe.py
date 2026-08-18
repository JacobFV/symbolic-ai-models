"""A dataset recipe: how examples **exist**, not where a jsonl happens to be.

The old shape of a "dataset" here was a directory with `train.jsonl` and
`eval.jsonl` in it. That is a *cache*, and treating it as the dataset makes two
things unanswerable: which source version produced it, and what would happen if
you asked for more. A recipe answers both by construction — it names its sources
by typed ref, its generator by id, and its splits as **key ranges**, so a sample
is a pure function of `(recipe hash, source snapshot versions, key)` and
materialisation is optional rather than authoritative.

Three things a recipe carries that a jsonl cannot:

* **Capabilities.** A generator declares what it needs from its source, and the
  recipe fails at load if the named snapshot does not populate them — before a
  single sample is drawn. See :mod:`symbolic_ai_core.data.knowledge_source`.
* **Coverage.** What the source *cannot* supply, recorded on the recipe. An
  essay corpus missing three of its eight rhetorical sections reads exactly like
  one that is not, and this is where that stops being invisible.
* **Surfaces.** One latent world, several renderings, so a next-token model and
  a missing-claim model are scored on the same sample rather than on two corpora
  only claimed to correspond.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..source.manifest import load_yaml, manifest_hash
from ..source.registry import repo_root
from .dataset import CurriculumDataset, SplitSpec

__all__ = ["DatasetRecipe", "recipes", "load_recipe", "RecipeError"]


class RecipeError(ValueError):
    """A recipe that cannot be built, said at load rather than at sample time."""


@dataclass(frozen=True)
class DatasetRecipe:
    """One dataset, as a manifest. Immutable; the hash is over its content."""

    id: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def generator(self) -> Mapping[str, Any]:
        return self.raw.get("generator") or {}

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(self.raw.get("sources") or ())

    @property
    def surfaces(self) -> tuple[str, ...]:
        return tuple(self.raw.get("surfaces") or ())

    @property
    def objectives(self) -> tuple[str, ...]:
        return tuple(self.raw.get("objectives") or ())

    @property
    def splits(self) -> dict[str, SplitSpec]:
        out: dict[str, SplitSpec] = {}
        for name, d in (self.raw.get("splits") or {}).items():
            d = d or {}
            out[name] = SplitSpec(seed0=int(d.get("seed0", 0)),
                                  per_lesson=int(d.get("per_unit", 16)),
                                  shuffle=bool(d.get("shuffle", True)),
                                  finite=bool(d.get("finite", False)))
        return out

    @property
    def hash(self) -> str:
        """Over the recipe's content, excluding its own recorded hash.

        Part of every sample's identity: two recipes that differ anywhere
        produce different samples under the same key, and a number attached to
        the wrong one is unattributable.
        """
        return manifest_hash(dict(self.raw), exclude=("recipe_hash",))

    # ---- building ----------------------------------------------------
    def dataset(self, **overrides: Any):
        """The :class:`ReplayableDataset` this recipe describes.

        Dispatch is on ``generator.id`` and is deliberately a small explicit
        table rather than an import hook: a recipe is data, and data that can
        name an arbitrary importable is a recipe that can execute anything.
        """
        gid = str(self.generator.get("id", ""))
        builder = _BUILDERS.get(gid)
        if builder is None:
            raise RecipeError(
                f"recipe {self.id!r} names generator {gid!r}, which is not "
                f"registered. Known: {sorted(_BUILDERS)}. A recipe is data; it "
                f"cannot name an arbitrary importable.")
        return builder(self, dict(overrides))

    @classmethod
    def load(cls, path: str | Path) -> "DatasetRecipe":
        d = load_yaml(path)
        r = cls(id=d["id"], raw=d, path=Path(path))
        if r.id != Path(path).stem:
            raise RecipeError(f"{path}: id {r.id!r} does not match its filename")
        return r


def recipe_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "manifests" / "datasets"


def recipes(root: Path | None = None) -> dict[str, DatasetRecipe]:
    d = recipe_dir(root)
    if not d.exists():
        return {}
    return {r.id: r for r in (DatasetRecipe.load(p) for p in sorted(d.glob("*.yaml")))}


def load_recipe(recipe_id: str, root: Path | None = None) -> DatasetRecipe:
    try:
        return recipes(root)[recipe_id]
    except KeyError:
        raise RecipeError(f"no recipe {recipe_id!r} under {recipe_dir(root)}"
                          ) from None


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------
def _formal_curriculum(recipe: DatasetRecipe, overrides: dict[str, Any]):
    from .curriculum import resolve_lessons

    p = dict(recipe.generator.get("params") or {})
    p.update(overrides)
    ds = CurriculumDataset(
        lessons=resolve_lessons(p.get("lessons")),
        dataset_id=recipe.id,
        language=str(p.get("language", "english")),
        curriculum=str(p.get("curriculum", "base")),
        max_nodes=int(p.get("max_nodes", 512)),
        splits=recipe.splits or None)
    return ds


def _kg_essays(recipe: DatasetRecipe, overrides: dict[str, Any]):
    from .essay_dataset import EssayDataset

    p = dict(recipe.generator.get("params") or {})
    p.update(overrides)
    return EssayDataset.from_recipe(recipe, p)


_BUILDERS = {
    "formal_curriculum": _formal_curriculum,
    "kg_essays": _kg_essays,
}
