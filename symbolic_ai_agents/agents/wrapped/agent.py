"""Any model from the other package, used as a policy.

``extra.model`` names anything in :data:`symbolic_ai_models.models.REGISTRY` —
``ngram``, ``ilp``, ``omegaclaw_ctx``, and the neural architectures too when
they are registered. The model is built and fitted on the same training episodes
every agent here gets, and then it *acts*: each legal action is scored as a
continuation of the observation text by
:func:`symbolic_ai_models.agent.score_choices`, and the best one is taken.

This is the row that makes the two packages answerable to each other. On
:mod:`symbolic_ai_agents.envs.choice` the wrapped model is scoring literally the
options :func:`symbolic_ai_models.agent.evaluate_choices` scores, and
``tests/test_agent_wrap.py`` pins that: this agent's *raw preference* must rank
them in the same order that function does, so a divergence there is a bug in the
wrapper rather than a finding.

What is **not** identical is the action finally taken, and the difference is
deliberate rather than an oversight. Every agent here mixes its preference
against the shared prior at its measured confidence, so ``wrap`` on ``choice``
is "this model, backed by the floor when it is unsure" — which is what makes it
comparable with the other five agents, and which means its ``choice`` accuracy
is not the model's ``ans acc`` from the other package. The two agree exactly
only where the calibrated confidence is 1.

Everywhere else the same model is being asked something the model harness cannot
ask, and the difference between its ``choice`` column and its ``repair`` column
is the measurement this package exists for.

Three honest limits
-------------------
* **Scoring is per-action and therefore linear in the action set.** A rule-based
  model's forward pass is pure Python over the whole sequence, so twenty-four
  candidates cost twenty-four passes. ``extra.max_actions`` (default 8) caps how
  many are scored, ranked by the shared prior — a fixed, agent-independent rule,
  but a real handicap on :mod:`symbolic_ai_agents.envs.repair`, whose candidate
  sets are larger than that. A ``repair`` score from this agent is a score under
  truncation and is not comparable with the same model's masked-node number.
* **The graph head is not used.** ``repair`` hands the agent a
  :class:`~symbolic_ai_models.models.symbolic.GraphView`, and this wrapper
  ignores it, scoring the rendered s-expression as text instead. A wrapper that
  called ``node_votes`` directly would be a better agent and a worse experiment:
  it would only work for the rule-based half of the registry, and the point of
  this row is that one wrapper serves everything.
* **Probes are never taken.** A language model has no opinion about ``look 3``
  as a continuation, so this agent abstains over the probes and the shared prior
  decides — which in practice means it answers immediately. That is a policy,
  and a defensible one, but it means this row's ``probe`` column measures
  answering blind rather than choosing not to ask.
"""

from __future__ import annotations

from typing import Sequence

import torch

from symbolic_ai_models.agent import score_choices
from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models import ModelConfig, RuleBasedModel, build as build_model

from ...envs.base import Observation
from ..base import ABSTAIN, Preference, PolicyAgent, held_out, training_views
from ..registry import register

__all__ = ["WrappedModel"]


@register("wrap", doc="Any symbolic_ai_models architecture, scored as a policy.")
class WrappedModel(PolicyAgent):
    """A model from the other package, asked to choose instead of to predict."""

    LEARNED = ("model", "model_name")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        self.model_name = str(self.get("model", "ngram"))
        self.max_actions = int(self.get("max_actions", 8))
        self.max_len = int(self.get("max_len", 512))
        self.model = None

    # ---- fitting --------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        cfg = ModelConfig(
            vocab_size=len(tok),
            d_model=int(self.get("d_model", 64)),
            n_layers=int(self.get("n_layers", 2)),
            n_heads=int(self.get("n_heads", 4)),
            max_len=self.max_len,
            max_nodes=int(self.get("max_nodes", 256)),
            extra=dict(self.get("model_extra", {})))
        model = build_model(self.model_name, cfg)
        if isinstance(model, RuleBasedModel):
            model.fit_on(list(episodes), tok)
        else:
            # A network needs a training budget, which this package does not
            # supply: an agent run is a fit, not a schedule. Rather than train a
            # network badly and report the number, refuse and say why.
            raise ValueError(
                f"wrap: {self.model_name!r} is a neural model and needs a "
                "training budget. Train it with `symbolic-ai-models train` and "
                "point `extra.run` at the finished run directory instead.")
        self.model = model.eval()
        self._calibrate(episodes, tok)

    def _calibrate(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Price the model's own margin on held-out training episodes.

        The margin between the best and second-best option is a statement about
        *separation*, which is measurable, and not about correctness, which is
        what the calibrator is for. The distinction is the one
        :class:`symbolic_ai_models.calibration.ScoreCalibrator` was written to
        enforce, and it applies here unchanged.
        """
        from ...envs import build as build_env
        _, held = held_out(episodes)
        env = build_env("choice")
        scores: list[float] = []
        correct: list[bool] = []
        for obs, gold in training_views(env, held, tok):
            if gold is None or not obs.actions:
                continue
            votes, raw = self._raw(obs)
            if not votes:
                continue
            best = max(votes, key=lambda a: (votes[a], a))
            scores.append(raw)
            correct.append(best == gold)
        self.calibrate_on(scores, correct)

    # ---- acting ---------------------------------------------------------
    @torch.no_grad()
    def _raw(self, obs: Observation) -> tuple[dict[str, float], float]:
        if self.model is None or self.tok is None or not obs.actions:
            return {}, 0.0
        options = self._shortlist(obs)
        if len(options) < 2:
            return ({options[0]: 1.0}, 0.0) if options else ({}, 0.0)
        scores = score_choices(self.model, self.tok, obs.text, options,
                               max_len=self.max_len)
        finite = [s for s in scores if s == s and s != float("-inf")]
        if not finite:
            return {}, 0.0
        logits = torch.tensor(scores, dtype=torch.float64)
        logits[~torch.isfinite(logits)] = float(min(finite)) - 10.0
        probs = torch.softmax(logits, dim=0).tolist()
        votes = {a: float(p) for a, p in zip(options, probs)}
        top = sorted(probs, reverse=True)
        return votes, float(top[0] - top[1])

    def _shortlist(self, obs: Observation) -> list[str]:
        """The actions worth paying a forward pass for, ranked by the shared prior.

        Truncation is a handicap and is stated as one in the module docstring.
        Ranking by the *shared* prior rather than by anything this agent knows
        keeps the rule agent-independent, so two wrapped models face the same
        shortlist and the comparison between them is still about the models.
        """
        options = list(obs.actions)
        if len(options) <= self.max_actions:
            return options
        prior = self._prior_over(obs, options)
        return sorted(options, key=lambda a: (-prior.get(a, 0.0),
                                              options.index(a)))[:self.max_actions]

    def prefer(self, obs: Observation) -> Preference:
        votes, raw = self._raw(obs)
        if not votes:
            return ABSTAIN
        return votes, self.confidence(raw)

    def n_parameters(self) -> int:
        return self.model.n_parameters() if self.model is not None else 0

    def render(self) -> str:
        lines = [f"=== {self.name}({self.model_name}): "
                 f"{self.n_parameters():,} model parameters ===",
                 f"  scores at most {self.max_actions} actions per decision",
                 f"  confidence map: "
                 f"{'fitted' if self.confidence_map.fitted else 'unfitted'}"]
        inner = getattr(self.model, "render", None)
        if callable(inner):
            lines.append("")
            lines.append(inner())
        return "\n".join(lines)
