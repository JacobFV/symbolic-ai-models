---
date: 2026-08-16
author: agent-premise-selection
status: pre-registration
related: [2026-08-16-once-deduction-is-exact-the-hard-part-is-premise-selection,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]
---

# The middle row: what an exact lookup scores when it must choose its own premise

CoTu ([arXiv:2607.14735](https://arxiv.org/abs/2607.14735)) claims that once
deduction is handed to an exact solver, the residual difficulty is **premise
selection**. This repo can price that claim with no LLM and no solver, because
both endpoints of the ladder are already published on the derived bucket of
`derive:wordnet`:

| arm | what the deduction is given | score |
|---|---|---|
| oracle premise | the kind sibling, **named** | 1.000 (`dfloor_not_copyable`) |
| **self-selected** | every visible candidate, **must choose** | **this experiment** |
| blind | no sibling at all | 0.167 (`blind_not_copyable`) |

The deduction is held fixed at the *same* table in all three rows. Only the
premise varies. The 0.833 gap between the published endpoints is, by
construction, entirely premise selection.

## What is being built

`scripts/premise_selection.py`, a sibling of `scripts/derived_split.py` and
importing its machinery unchanged (`carrying_lessons`, `matched_episodes`,
`derivation_floor`, `_positions`). It touches no run's `derived_split.json`; it
writes its own `premise_selection.json`, so the 22 published rows per arm are
untouchable by it.

**No model weights survive under `runs/`** (only `summary.json` and `rules.txt`
are tracked), so `derived_split.py`'s `main` cannot be re-run at all. The config
is rebuilt with `TrainConfig.from_dict(summary["config"])` and the tokenizer
with `build_tokenizer(cfg, load_data(cfg)[0])`, both pure functions of the
recorded config. **The gate on that reconstruction is that it must reproduce the
published floors bit for bit** — `dfloor_n = 1345`, `dfloor_* = 1.000`,
`blind_not_copyable = 0.16720257234726688` on `derive:wordnet`. If it does not,
the population is not the published one and no number below may be read. (This
has been checked and it does reproduce, exactly, before the selector was
written.)

## The selector, fixed now

Scored on the **identical positions** the published rows use — same
`matched_episodes` intersection, same 8 masking draws, same `_hidden`, same
`_scorable`, same requirement that the kind sibling be visible. Same denominator
means the three rows are one ladder rather than three populations.

Fitted on training seeds `0..19` only; scored on eval seeds `>= 1_000_000`.

For a hidden derived value at node `vi`, the candidate set is every **visible**
node `j != vi` in the candidate scope. From training, for every candidate label
`s`, a counter `rule_all[s]` over the derived values it co-occurred with. Then:

* score `s` by its **evidence-shrunk mode probability**,
  `(max_v count_s[v] + 1) / (total_s + |V|)` with `|V| = 6` — the posterior
  predictive accuracy of reading `s`, under Dirichlet(1). Shrinkage is not
  decoration: the object-id sibling (`o0`, `o1`, ...) and a once-seen rare label
  are both spuriously peaked without it, and picking them is exactly the failure
  mode the arm is meant to be able to show.
* pick the highest-scoring candidate, ties to the lowest node index (the tree
  shapes are identical across arms, so a tie-break cannot favour one arm);
* predict `rule_all[s].most_common(1)`. A candidate with no training support
  scores `1/6` and predicts the blind marginal — so the self-selected row can
  never fall *below* the blind row, which is correct: choosing badly should cost
  you the conditional, not the marginal.

When the chosen candidate *is* the kind sibling, the prediction is bit-identical
to the oracle floor's, because `rule_all['building'] == rule['building']`. The
deduction really is held fixed.

## Two candidate scopes, because they ask different questions

* **siblings** (the literal design in the question note): the other children of
  the same `obj` predicate. Measured: that is **four** candidates — the object
  id, the kind, and two `num` nodes.
* **whole graph** (the faithful CoTu version): every visible node in the
  episode, tens of candidates, and the co-occurrence table for a kind label is
  *diluted* — a graph containing `building` also contains three other objects
  whose values are not `annex`, so `rule_all['building']` is smeared over the
  value vocabulary in a way the sibling-scoped table is not.

Reporting only the sibling scope would be the flattering half. Four candidates
with one informative is not premise selection in CoTu's sense and a 1.000 there
licenses nothing; the whole-graph scope is where the claim can actually fail.

## Predictions, before the run

* **siblings: near 1.000.** `rule_all['building'] = {annex: 68}` scores
  `69/74 = 0.93` while an object id or a digit is near-uniform at `~0.20`. I do
  not expect this row to be interesting, and I am recording that in advance so
  that a 1.000 cannot later be reported as a discovery.
* **whole graph: genuinely unknown.** The dilution argument gives the kind label
  roughly `1/4 + (3/4)(1/6) ~= 0.375` against `~0.167` for an uninformative
  label — enough to win if nothing else in the graph is peaked, and there are
  hundreds of other labels with small counts for the shrinkage to have to
  suppress. This is the row worth running.
* **`derive:wordnet-perm`: both scopes at ~0.167, and this is the falsifier.**
  In the control the kind->value correspondence is redrawn per episode, so no
  candidate carries cross-episode information and there is nothing to select
  *for*. **If the self-selected row separates from 0.167 in `-perm`, the
  selector is cheating** — it has found a within-episode leak — and the
  treatment number must not be reported. This control is the reason the arm is
  worth anything.

## What each reading would mean, decided now

* **Near 1.000 in the treatment:** premise selection on this curriculum is
  trivial, CoTu's residual does **not** reproduce here, and the derived bucket's
  difficulty was purely **representational** — which is what `frontier-001`'s
  map form addressed (`notes/findings/2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary.md`).
* **Near 0.167 in the treatment:** selection is the **entire** difficulty,
  expressiveness was never the constraint, and
  `notes/findings/2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it.md`
  has to be reread as a statement about **search**, not about hypothesis
  language. That would materially change what the repo believes.
* **The two scopes disagreeing** is a third outcome and not a failure: it would
  say the residual is real but is a function of the *candidate count*, which is
  a sharper version of CoTu's claim than CoTu states.

## What is deliberately not claimed

This is a floor, not a model. It says what an exact table with an honest,
no-learning selector gets. It does not say what `frontier-001` (0.532 treatment
/ 0.072 control on `acc | derived, not copyable`, premise chosen by a *learned*
guard) is doing — the comparison is informative because this is the no-learning
version of the same question, not because the two numbers are commensurable
metrics of the same object.
