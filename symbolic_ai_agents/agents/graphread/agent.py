"""The same model as ``wrap``, read through its graph head instead of as text.

``wrap``'s own docstring records the limit this agent exists to remove: *"The
graph head is not used. ``repair`` hands the agent a ``GraphView``, and this
wrapper ignores it, scoring the rendered s-expression as text instead."* One
readout, welded in, for every model in the registry — which is exactly a
representation that only works when read one way, and no number in the model
harness could have shown it, because the model harness only ever asks the one
question.

So this is ``wrap`` with a single difference and no others. Same
:class:`~symbolic_ai_agents.agents.base.PolicyAgent` base, same ``extra.model``
naming anything in :data:`symbolic_ai_models.models.REGISTRY`, same refusal to
fit a network without a training budget, same held-out
:class:`~symbolic_ai_core.calibration.ScoreCalibrator`, same shared prior
underneath. What changes:

* ``wrap`` scores each legal action as a **text continuation** through
  :func:`symbolic_ai_models.agent.score_choices`.
* ``graphread`` reads the model's **graph emission** — ``node_votes`` and
  ``source_votes`` — through
  :class:`symbolic_ai_agents.readouts.action.ActionReadout`.

``extra.channel`` picks which channel the readout consumes: ``symbol`` (the
vocabulary head, spelled and filtered to the legal set), ``node`` (the pointer
head, resolved to the label each pointed-at node carries), or ``both``. Two runs
differing only in that string are a measurement of the readout rather than a
comparison of models, which is the reason the channel is a knob at all.

Honest limits
-------------
* **``choice`` has no graph, so this agent abstains there by construction, and
  its ``choice`` row IS the shared prior.** It is not a score of the model, of
  the readout, or of anything else; it is what every abstaining agent gets, and
  it is in the table only because leaving an environment out would be worse.
  Read it as a control that the abstention path lands where it claims to.
  ``retry`` and ``probe`` carry no graph either and the same applies. Only
  ``repair`` is a measurement.
* **No fallback to text, ever.** Where the graph is absent or the model emits
  nothing on the chosen channel, this agent returns
  :data:`~symbolic_ai_agents.agents.base.ABSTAIN` and lands on the prior. A row
  that silently switched mechanism when its own mechanism had nothing to say
  would be a measurement of neither mechanism, and the abstention rate — printed
  by :meth:`render` and carried in :attr:`spoke` / :attr:`asked` — is the number
  that makes the switch visible if it ever creeps back in.
* **The view ``repair`` builds carries no prompt text.**
  ``Repair._view`` constructs its :class:`~symbolic_ai_core.graphview.GraphView`
  without ``text``, so ``view.mentions`` returns ``-1`` and any part of a model
  that reads the surface is inert here. That handicaps text-reading models on
  this row relative to their masked-node numbers, and it is a property of the
  environment rather than of this agent — but a reader comparing the two columns
  is owed it.
* **Fitting is the model's own ``fit_on``, not experience.** Like ``wrap``, this
  agent learns from labels rather than from reward; only the *reading* is
  different. The calibrator is the one thing fitted through the environment, and
  it is fitted on ``repair`` rather than ``choice`` for the obvious reason that
  ``choice`` produces no decision this agent participates in.
"""

from __future__ import annotations

from typing import Sequence

import torch

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models import ModelConfig, RuleBasedModel, build as build_model

from ...envs.base import Environment, Observation
from ...readouts.action import ActionReadout, emit
from ..base import ABSTAIN, Preference, PolicyAgent, held_out, training_views
from ..registry import register

__all__ = ["GraphReadAgent"]


@register("graphread",
          doc="A symbolic_ai_models model read through its graph head as an action.")
class GraphReadAgent(PolicyAgent):
    """``wrap``, but the graph emission is what gets read."""

    LEARNED = ("model", "model_name", "channel")

    def __init__(self, extra=None) -> None:
        super().__init__(extra)
        self.model_name = str(self.get("model", "ngram"))
        self.channel = str(self.get("channel", "symbol"))
        self.max_len = int(self.get("max_len", 512))
        self.readout = ActionReadout(channel=self.channel)
        self.model = None
        #: decisions this agent was asked for while *acting*, and how many of
        #: them it had something to say about. Not touched during fitting — the
        #: calibrator calls :meth:`_raw` directly — so the printed rate is the
        #: rate on the episodes that were scored.
        self.asked = 0
        self.spoke = 0

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
            # Same refusal as `wrap`, and for the same reason: an agent run is a
            # fit, not a schedule, and an undertrained number reported straight
            # is worse than no number. This repo has already recorded a null
            # ("gru is beaten at -0.050") that was 1.3 training passes.
            raise ValueError(
                f"graphread: {self.model_name!r} is a neural model and needs a "
                "training budget. Train it with `symbolic-ai-models train` and "
                "point `extra.run` at the finished run directory instead.")
        self.model = model.eval()
        self._calibrate(episodes, tok)

    def fit(self, ctx) -> None:
        self._learn_envs = list(ctx.envs.values())
        super().fit(ctx)

    def _graph_envs(self, episodes: Sequence[Episode],
                    tok: SymbolTokenizer) -> list[Environment]:
        """The environments that actually hand out a graph, found by asking.

        Taken from the ones this run was fitted with, so the calibrator sees the
        ``repair`` settings the evaluation will use rather than a default copy
        of it — ``mask_rate`` and ``max_actions`` both change how separable a
        decision is, and a map fitted at one and applied at another is a map for
        a different question. ``wrap`` calibrates on a freshly built ``choice``
        and gets away with it because ``choice`` has no settings.

        Which ones carry a graph is *measured*, by resetting each on a few
        episodes, rather than read off a name. A hard-coded ``== "repair"`` would
        silently exclude the next environment that exposes structure, and the
        symptom would be an unfitted calibrator rather than an error.
        """
        from ...envs import REGISTRY, build
        envs = list(getattr(self, "_learn_envs", ()) or ())
        if not envs:
            envs = [build(n) for n in sorted(REGISTRY)]
        out: list[Environment] = []
        for env in envs:
            if any(env.reset(ep, tok=tok).graph is not None
                   for ep in list(episodes)[:8]):
                out.append(env)
        return out

    def _calibrate(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Price the readout's own separation on held-out training episodes.

        Held out from the *model's* fit as well as from evaluation, which is what
        makes the map a measurement rather than a certificate of overconfidence
        — the argument :class:`~symbolic_ai_core.calibration.ScoreCalibrator`
        makes at length and that applies here unchanged. The known bias is the
        same one ``careful`` states: the model itself was fitted on all of the
        training episodes, so the confidences seen here are a little in-sample
        and the map is a little too generous. Fixing it means fitting the model
        twice, which costs more than the bias does.
        """
        _, held = held_out(episodes)
        scores: list[float] = []
        correct: list[bool] = []
        for env in self._graph_envs(episodes, tok):
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
        """The readout's preference over this observation's legal actions.

        One graph emission per decision, not one forward pass per candidate:
        ``wrap``'s ``max_actions`` truncation has no analogue here, because the
        cost of asking does not grow with the size of the action set. That is a
        real difference between the two rows and it favours this one on
        ``repair``, whose candidate sets are larger than ``wrap`` will score.
        """
        if self.model is None or obs.graph is None or obs.node < 0:
            return {}, 0.0
        votes, raw = self.readout.prefer(emit(self.model, obs.graph), obs)
        return dict(votes), float(raw)

    def prefer(self, obs: Observation) -> Preference:
        self.asked += 1
        votes, raw = self._raw(obs)
        if not votes:
            return ABSTAIN
        self.spoke += 1
        return votes, self.confidence(raw)

    def explain(self, obs: Observation, action: str, votes, conf: float) -> str:
        if not votes:
            where = "no graph" if obs.graph is None else f"no {self.channel} votes"
            source = f"prior ({self.shortcut.name})" if self.shortcut else "prior"
            return f"abstained ({where}) -> {source}"
        return f"{self.channel}: {len(votes)} actions at {conf:.2f}"

    def n_parameters(self) -> int:
        return self.model.n_parameters() if self.model is not None else 0

    def render(self) -> str:
        rate = self.spoke / self.asked if self.asked else float("nan")
        lines = [f"=== {self.name}({self.model_name}, channel={self.channel}): "
                 f"{self.n_parameters():,} model parameters ===",
                 f"  spoke on {self.spoke:,} of {self.asked:,} decisions "
                 f"({rate:.1%}); the rest abstained onto the shared prior",
                 "  `choice`, `retry` and `probe` carry no graph, so every "
                 "decision there is one of the abstentions above",
                 f"  confidence map: "
                 f"{'fitted' if self.confidence_map.fitted else 'unfitted'}"]
        inner = getattr(self.model, "render", None)
        if callable(inner):
            lines.append("")
            lines.append(inner())
        return "\n".join(lines)
