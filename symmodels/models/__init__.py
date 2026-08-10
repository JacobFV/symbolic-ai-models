"""The architectures under comparison.

Importing this package registers every model, so ``model_names()`` is complete
after ``import symmodels.models`` and a new architecture becomes available by
being imported here — there is no separate list to keep in sync.
"""

from .base import ModelConfig, ModelOutput, SymbolicModel
from .registry import REGISTRY, build, get, model_names, register

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import hrr, ndr, recurrent, tpr, transformer  # noqa: F401

__all__ = ["ModelConfig", "ModelOutput", "SymbolicModel", "REGISTRY", "build",
           "get", "model_names", "register"]
