"""Train and evaluate symbolic text model architectures on one harness.

Two questions, asked of every architecture, out of one shared vocabulary and
through one shared output head:

* **next-token prediction** over the episode as the curriculum renders it;
* **masked-node prediction** over the typed term graph the curriculum rendered
  it *from*.

The data comes from ``langcurriculum`` — 179 procedurally generated lessons
whose episodes are pure functions of a seed, so an evaluation set is a set of
worlds that did not exist until it was asked for and cannot have been trained
on. See https://jacobfv.github.io/formal-language-cirriculum/.

    >>> import symbolic_ai_models
    >>> cfg = symbolic_ai_models.TrainConfig(model="rgt", lessons="unification",
    ...                             steps=50, out="runs/demo")
    >>> summary = symbolic_ai_models.train(cfg)                 # doctest: +SKIP
"""

from __future__ import annotations

from .data.batch import SymbolicBatch, collate_graph, collate_text
from .data.curriculum import Episode, build_split, generate, resolve_lessons
from .data.graph import Graph, graph_from_json
from .data.tokenizer import SymbolTokenizer
from .models import Model, ModelConfig, NeuralModel, RuleBasedModel, build, model_names
from .tasks import LanguageModelling, MaskedNode, Task, make_task, task_names
from .train import TrainConfig, evaluate_model, load_run, train

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # data
    "Episode", "Graph", "SymbolicBatch", "SymbolTokenizer",
    "generate", "build_split", "resolve_lessons", "graph_from_json",
    "collate_text", "collate_graph",
    # models
    "Model", "NeuralModel", "RuleBasedModel", "ModelConfig", "build", "model_names",
    # tasks
    "Task", "LanguageModelling", "MaskedNode", "make_task", "task_names",
    # training
    "TrainConfig", "train", "evaluate_model", "load_run",
]
