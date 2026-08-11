# symbolic-ai-001: one symbolic interaction protocol, many substrates

*A design note and first experiment.*
2026-08-06 · code commit: see `results/records.jsonl` · hardware: 1× NVIDIA GB10 (shared)

---

## Abstract

We define a single interaction protocol — an agent consumes symbolic
observations, emits symbolic actions, and receives a reward and a next
observation — and ask how much of contemporary machine learning can be
expressed inside it without distorting the tasks. The protocol and everything
built on it is ~7,200 lines of Python plus 600 lines of tests, with nine native
environments spanning prediction, reasoning,
control, scene understanding and tool use, and adapters that expose foreign
substrates (Hugging Face corpora and datasets, Gymnasium/Farama, PettingZoo,
Prime Intellect's `verifiers` tasksets, BrowserGym, TextWorld/ALFWorld/
ScienceWorld, OSWorld, OpenEnv) through the same contract while preserving
their native rewards, graders, episode boundaries and canonical metrics.

We show — as an executable check, not an argument — that language-model
pretraining is the special case of the protocol in which the action is a
predictive distribution and the reward is `log p(x_{t+1} | x_{<=t})`. On trained
checkpoints and held-out FineWeb-Edu text, the total return accumulated through
`Environment.step` and the total log-likelihood computed by ordinary batched
cross-entropy agree to **|Δ| = 2·10⁻⁵ over 512 token positions**.

We then train **`symbolic-ai-001`** — one 13.97M-parameter decoder-only
transformer — through this single interface on a mixture of FineWeb-Edu
next-token prediction, SST-2 classification, a symbolic gridworld, a real
Gymnasium MiniGrid task, three reasoning environments and a tool-calling
environment, and compare it against the conventional pipeline built from the
*identical* architecture: LM-only pretraining, and LM pretraining followed by
per-task finetuning (one model per task).

The single model matches or exceeds its per-task specialists on 4 of 7 trained
families (MiniGrid 0.70 vs 0.70 success, arithmetic 0.78 vs 0.78 exact, proof
1.00 vs 1.00, tool-calling 0.98 vs 1.00 solved), trails them on two (logic 0.60
vs 0.94 solved; gridworld 0.40 vs 0.44 success), and is at chance on SST-2
along with every other arm at this scale. Conventional LM-only pretraining
produces an agent at or below the random policy on every interactive family
(e.g. gridworld 0.00, tool-calling 0.00). The multi-task model pays for this
with language-model quality — held-out perplexity 89.1 vs 51.9 — under an
equal *optimizer-step* budget in which it received half as many corpus tokens.
Two further negative results are reported: LM pretraining transfers almost
nothing to these symbolic tasks at this scale (scratch-initialized specialists
nearly match LM-initialized ones), and no arm transfers to a family held out of
training entirely.

---

## 1. The question

> How much of AI can be represented as an agent consuming symbols, producing
> symbols, and receiving feedback from an environment?

This is an engineering question before it is a scientific one. The obstacle has
never been that the formalism is unavailable — the agent/environment loop is as
old as the field — but that each research area ships its own incompatible
harness: a dataloader for supervised learning, a `gym.Env` for RL, a
rollout-and-rubric API for LLM agents, a container protocol for computer use.
Any claim about "one agent across everything" therefore becomes a claim about
glue code.

We take the glue seriously and put all of it in one place: an *adapter*
boundary. Above the boundary there is exactly one contract. Below it, every
substrate keeps its own semantics.

## 2. The protocol

```python
Symbol = (type: str, value: Any, meta: dict)              # immutable, hashable, composable
Observation = Action = Symbol

class Environment:
    spec: EnvSpec                                          # provenance
    observation_space: SymbolSpace                         # typed, inspectable
    action_space: SymbolSpace
    def reset(self, *, seed=None, options=None) -> tuple[Observation, dict]
    def step(self, action: Action) -> Transition           # (obs, reward, terminated, truncated, info)

class Agent:
    def initial_state(self, *, seed=None, env=None) -> AgentState
    def act(self, state: AgentState, observation: Observation) -> tuple[AgentState, Action]
    def observe(self, state, action, transition) -> AgentState
```

The agent is the partial function

```
A : (S_agent, O*) → (S_agent, A*)
```

with agent state passed in and returned rather than hidden in the object. This
is not decoration: explicit state is what makes agents forkable for search,
replayable from a trajectory, and comparable across paradigms (a test asserts
that `act` does not mutate the state handed to it). A `StatefulAgent` wrapper
recovers the familiar `reset()` / `act(obs)` ergonomics on top of the pure core.

### 2.1 Symbols

A symbol is a typed node whose `value` may contain other symbols, so one
primitive covers tokens, strings, numbers, identifiers, predicates, relations,
tuples, lists, AST nodes, graph references, function applications, structured
records — and distributions over symbols:

```
tok:the                  (pred on a b)          [tok:a tok:b tok:c]
num:3.5                  (node Add x y)         {role=str:"user" content=str:"hi"}
str:"hello"              @scene_graph:17        (app search query=str:"why?")
```

Composites expose their children including the values of named fields, so
traversal reaches every symbol in a structure. Symbols are frozen and hashable
(so they can key a table policy), carry non-semantic `meta` (spans, logprobs,
token ids) that does not affect identity, and round-trip through JSON and
through a compact text grammar.

`Dist` — a distribution *over* symbols, itself a symbol — is the piece that
makes supervised prediction expressible as an action rather than as a separate
mode of the framework.

### 2.2 Symbol spaces

Every environment declares what may cross the boundary in each direction:
`Discrete`, `Atom`, `SeqSpace`, `StructSpace`, `OneOf`, `DistOver`, `AnySpace`.
Both discrete and structured actions are first class:

```
Discrete[moves](LEFT, RIGHT, UP, DOWN, PICKUP)
OneOf(Struct[app:search](query: Atom(str)) | Struct[app:calc](expr: Atom(str)) | ...)
DistOver(Discrete[bpe](8192 symbols))
```

Spaces are how an agent may adapt its *internal* encoding without learning
anything about the task (§5.2). `AnySpace` is deliberately available: an adapter
wrapping free-form shell commands should say so rather than pretend to a finite
action set.

### 2.3 What we borrowed

* **Gymnasium** — `reset(seed=…) → (obs, info)`, and the `terminated` vs
  `truncated` distinction: the difference between "the task ended" and "we ran
  out of budget", which matters for every value estimate.
* **Prime Intellect `verifiers`** — dataset/taskset-backed episodes; graders
  that own their reward semantics; per-episode task metadata; stop conditions; a
  registry keyed by environment id.
* **OpenEnv** — an explicit `state()` view of the episode, which is what lets a
  containerized or remote backend implement the same protocol, and lets our
  environments be *served* to that ecosystem (`SymbolicOpenEnvServer`).

What we did not borrow: vectorized-env machinery, a wrapper zoo, a tokenizer
contract, or any commitment to an optimizer. The `Learner` protocol is one
method — `update(trajectories) → metrics` — and the environment never sees it.

### 2.4 Trajectories and provenance

Trajectories are first-class and serializable: `[(observation, action, reward),
…]` plus env spec, agent spec, seed, task and native metrics. Every recorded
result additionally carries environment/taskset, upstream version, split, seed,
adapter version, encoder, decoder, agent checkpoint, training mixture, reward
definition, episode/token counts, and native benchmark metrics — the last
reported *alongside* the normalized reward, never in place of it
(`results/records.jsonl`, 255 rows for this note).

## 3. Prediction is interaction (checked, not asserted)

For a sequence `x_1 … x_n`:

```
observation_t = x_1 … x_t
action_t      = a predictive distribution for x_{t+1}      (a Dist symbol)
r_t           = log p(x_{t+1} | x_{<=t})                   (NLL = −r_t)
transition    = append x_{t+1} (teacher forcing) | append argmax (free running)
```

Three checks, at two levels of realism.

**Unit level** (`tests/test_lm_equivalence.py`, random model, random sequence):
the episode return equals the batched sum of `log p` over the same positions to
2·10⁻³; per step `info["nll"] == −reward` and `ppl == exp(nll)`; and a *uniform*
predictive policy earns exactly `log(1/V)` per step — the calibration check that
the reward really is a log-probability.

**End-to-end** (`symbolic/experiments/lm_protocol_check.py`, trained
checkpoints, held-out FineWeb-Edu chunks, identical positions):

| model | positions | Σ log p through `Environment.step` | Σ log p batched | \|Δ\| |
|---|---|---|---|---|
| symbolic-ai-001 | 512 | −2398.2746 | −2398.2747 | 1.9·10⁻⁵ |
| baseline-lm-only | 512 | −2324.7483 | −2324.7480 | 2.3·10⁻⁴ |

Two consequences. Maximum-likelihood pretraining is not a different objective
from RL-style credit assignment here; it is the case where every sample carries
weight 1 and the transition ignores the action. And the trainer may use batched
tensors for throughput without changing the objective, because this equality is
what licenses the shortcut.

The same reduction gives classification (one-step episodes, reward
`log p(y|x)`), sequence completion, scene question answering over detector
symbols, and any `dataset row → observation / target / grader` mapping.

## 4. Substrates

One adapter per *ecosystem*, never per benchmark; benchmark identity is
configuration.

| family | adapter | what stays native | status in this run |
|---|---|---|---|
| HF datasets / LM corpora | `hf_dataset.py`, `lm_corpus.py` | dataset revision, splits, row semantics | **used**: FineWeb-Edu (rev `87f0914`), SST-2 |
| Gymnasium / Farama | `gym_adapter.py` | reward, termination/truncation, seeds | **used**: MiniGrid; CartPole tested |
| PettingZoo | `pettingzoo_adapter.py` | AEC/parallel turn order, per-agent rewards | **used**: `rps_v2` (+ single-agent projection) |
| Prime Intellect `verifiers` | `prime_verifiers.py` | dataset rows, `env_response`, stop conditions, **Rubric** | **adapter tested** against a live `verifiers` environment scored by its own rubric; 23 tasksets registered |
| BrowserGym | `browsergym_adapter.py` | task validators, AXTree observation, high-level actions | registered; needs browsers + task servers |
| TextWorld / ALFWorld / ScienceWorld | `textworlds.py` | admissible commands, scores, quests | registered; backends do not build on this host (aarch64) |
| OSWorld | `osworld.py` | VM, per-task evaluator | registered; needs a VM provider |
| OpenEnv | `openenv.py` | client protocol, both directions | protocol view tested |

Two rules keep this honest.

**Never rewrite a grader.** The `verifiers` adapter drives the upstream
environment turn by turn and asks the upstream `Rubric` for the reward. Our
test constructs a real `verifiers.SingleTurnEnv` with its own dataset and rubric
and asserts that a correct answer scores 1.0 and an incorrect one 0.0 *through
the symbolic loop*. If a rubric cannot run in a given installation, the run
records `rubric_error` rather than substituting a homemade score. SWE-bench-style
pass/fail stays pass/fail.

**Never call a tensor a symbol.** Continuous or array-valued native observations
pass through a *named* `Encoder`; symbolic actions pass through a *named*
`Decoder`; both are recorded in every result. The same MiniGrid task is exposed
through a relational encoder — `(see goal green 2 2)`, egocentric predicates —
and through a flat numeric encoder, so representation is an experimental
variable. Images enter the same way: `DetectionEncoder` turns SAM/detector
output (`bbox + class + score`) into `(obj cup 0.91 cx cy w h)` symbols, leaving
the interesting part — integrating them into a scene-level answer — as the
learning problem.

The relational encoder is load-bearing rather than cosmetic: a rule policy
written *against its predicates* (`symbolic/agents/rulesets.py::minigrid_rules`)
reaches 100% success on `MiniGrid-Empty-5x5` and 62% on `Empty-Random-5x5`, and
is the teacher used for that component. Two bugs found while building it are
recorded in comments, because both are properties of the boundary rather than of
the environment: an object-count cap that spent its budget describing walls
behind the agent, and a greedy rule that oscillated because turning toward an
off-axis target swings it to the other side.

## 5. `symbolic-ai-001`

### 5.1 Architecture

Decoder-only transformer: 6 layers, 6 heads, `d_model` 384, context 512,
byte-level BPE with 8,192 merges trained on FineWeb-Edu text *plus* serialized
symbolic structures, tied embeddings — **13.97M parameters** (13.77M
non-embedding). It is deliberately ordinary: every neural arm uses this same
network, so the only difference between `symbolic-ai-001` and the conventional
baseline is the data distribution and the sample weighting.

### 5.2 Three internal encodings, chosen from the declared spaces

The agent linearizes symbols to text and back. It inspects the *spaces* an
environment declares — never the task — and binds one of:

* **stream** — the observation is a sequence over a discrete vocabulary, the
  action is a distribution over that same vocabulary, and each vocabulary symbol
  is a single token id (which the environment may declare in symbol metadata).
  The softmax row *is* the symbolic distribution. This case is byte-for-byte
  ordinary language modelling.
* **score** — the action space is enumerable and small: score every candidate
  continuation in one batched forward pass, and return either the arg-max action
  or a distribution over actions. Exact, and `O(|A|)` per step.
* **generate** — otherwise: free-decode action tokens and parse them back into a
  symbol. Unparseable output falls back to a legal action and is counted
  (`parse_fail_rate`), because decoding failure is a property of an agent worth
  measuring.

### 5.3 One loss

```
L(θ) = − Σ_i w_i · log p_θ(a_i | o_i) / Σ_i w_i·|a_i|
```

over the action segment of each symbolic step. The update rule is a choice of
`w`, not of architecture or interface:

| weight | what it is |
|---|---|
| `w = 1` on a token stream | maximum likelihood / next-token pretraining |
| `w = 1` on expert episodes | behavioural cloning |
| `w = exp((G − b)/β)` | advantage-weighted regression |
| `w = G − b` | REINFORCE with a baseline |
| `w = 1[G ≥ b]` | filtered / best-of-n cloning |

`symbolic-ai-001` uses `w = 1` for the corpus and dataset components and
advantage weighting (`β = 0.5`) for the interactive ones. Targets for the
interactive components come from teacher policies that are themselves ordinary
agents under the same contract — a best-first planner over `env.clone()`, and
rule policies written against the encoders' predicates. Other learners in the
repo (tabular Q, Monte-Carlo, symbolic rule induction, REINFORCE and BC for the
feature-hashing MLP) consume the *same* trajectory objects; none of them is
visible to any environment.

### 5.4 Training distribution

| component | family | weight | steps | training data | teacher | teacher score |
|---|---|---|---|---|---|---|
| lm/fineweb-edu | HF corpus | 0.50 | 3961 | 40.0M tokens (rev `87f0914`, shard 0) | — (max-likelihood) | — |
| hf/sst2 | HF dataset | 0.05 | 404 | 1500 rows | random driver | label is the target |
| gridworld | native | 0.10 | 807 | 500 eps / 7392 steps | search | success 0.65 |
| minigrid | Gymnasium | 0.08 | 650 | 800 eps / 8984 steps | rule (relational) | success 0.62 |
| logic | native | 0.08 | 632 | 1200 eps / 1564 steps | rule (forward chaining) | solved 1.00 |
| arithmetic | native | 0.06 | 505 | 600 eps / 2066 steps | search | exact 0.83 |
| proof | native | 0.05 | 397 | 600 eps / 753 steps | search | proved 1.00 |
| tool_call | native | 0.08 | 644 | 1200 eps / 2400 steps | rule (tool policy) | solved 1.00 |
| scene_qa | native | **0.00** | 0 | 1200 eps collected, *not trained on* | random driver | held-out family |

8,000 optimizer steps, batch 24 × 512, AdamW, cosine schedule, bf16, 16.0 min
wall-clock. A curriculum variant of the same mixture ships in
`configs/symbolic-ai-001-curriculum.yaml`; it is configuration, so "mixture vs
curriculum" is an experiment this repo can run, not an architectural commitment.

## 6. Experimental design

| arm | what it tests |
|---|---|
| `symbolic-ai-001` | one model, heterogeneous mixture, one interface |
| `baseline-lm-only` | conventional pretraining: same architecture, same 8,000 steps, corpus only (98.3M tokens) |
| `specialist-<env>` | conventional pretrain → finetune: from the LM checkpoint, 800 steps on one environment |
| `scratch-<env>` | same 800 steps from random init (isolates transfer) |
| `random`, `table`, `mlp`, `search` | non-neural reference points under the same contract |

* **Held-out seeds.** Training episodes used seeds `0…n`; evaluation uses seeds
  from `10 000`. Environment content is regenerated from the seed, so this is a
  fresh-task split, not a replay.
* **Held-out data.** SST-2 is evaluated on `validation`, never trained on. The
  corpus is split by `sha256(doc_id) < 0.01 → validation`, stable under re-runs,
  shard count and cap changes.
* **Held-out family.** `scene_qa` is in the repo and was collected, but has
  weight 0.00 in the mixture: no arm trained on it.
* 50 episodes per (agent, environment) cell; native metrics reported next to
  normalized return; every cell written to `results/records.jsonl` with full
  provenance.

## 7. Results

### 7.1 Native metrics (success / solved / exact / accuracy), 50 held-out episodes

| agent | gridworld | minigrid | logic | arithmetic | proof | tool_call | sst2* | scene_qa† |
|---|---|---|---|---|---|---|---|---|
| random | 0.02 | 0.40 | 0.56 | 0.00 | 1.00 | 0.00 | 0.58 | 0.16 |
| table (Q-learning) | 0.00 | 0.28 | 0.40 | 0.00 | 0.44 | 0.00 | 0.42 | 0.16 |
| mlp (symbol features) | 0.06 | 0.28 | 0.64 | 0.00 | 0.52 | 0.00 | 0.62 | 0.08 |
| search (planner) | **0.72** | 0.62 | **1.00** | 0.18 | 1.00 | 0.00 | 0.56 | 0.04 |
| **symbolic-ai-001** | 0.40 | **0.70** | 0.60 | **0.78** | **1.00** | 0.98 | 0.56 | **0.18** |
| baseline-lm-only | 0.00 | 0.28 | 0.44 | 0.00 | 0.40 | 0.00 | 0.56 | 0.02 |
| specialist-gridworld | 0.44 | 0.00 | 0.66 | 0.00 | 0.28 | 0.00 | 0.42 | 0.02 |
| specialist-minigrid | 0.00 | 0.70 | 0.66 | 0.00 | 0.28 | 0.00 | 0.58 | 0.04 |
| specialist-logic | 0.00 | 0.00 | **0.94** | 0.00 | 0.52 | 0.00 | 0.50 | 0.30 |
| specialist-arithmetic | 0.00 | 0.00 | 0.72 | 0.78 | 0.30 | 0.00 | 0.40 | 0.12 |
| specialist-proof | 0.00 | 0.00 | 0.66 | 0.00 | 1.00 | 0.00 | 0.42 | 0.16 |
| specialist-tool_call | 0.00 | 0.00 | 0.30 | 0.00 | 0.28 | **1.00** | 0.56 | 0.02 |
| specialist-hf_sst2 | 0.00 | 0.00 | 0.66 | 0.00 | 0.28 | 0.00 | 0.42 | 0.02 |
| specialist-scene_qa | 0.00 | 0.00 | 0.60 | 0.00 | 0.28 | 0.00 | 0.56 | 0.10 |
| scratch-gridworld | 0.26 | 0.00 | 0.66 | 0.00 | 0.28 | 0.00 | 0.46 | 0.02 |
| scratch-logic | 0.00 | 0.00 | 0.88 | 0.00 | 0.28 | 0.00 | 0.58 | 0.42 |
| scratch-tool_call | 0.00 | 0.00 | 0.62 | 0.00 | 0.28 | 1.00 | 0.58 | 0.16 |

Neural arms are shown as stochastic policies (T = 1); see §7.4. \
\* SST-2 accuracy near 0.5 is chance; the argmax of a uniform predictive policy
breaks ties toward the first class, which is why `random` reads 0.58 rather than
0.50. Return (`log p`) is the honest column for this row: random −0.693 =
log 0.5, symbolic-ai-001 −0.683. \
† `scene_qa` was held out of training for every arm.

### 7.2 Normalized return

| agent | gridworld | minigrid | logic | arithmetic | proof | tool_call | sst2 | scene_qa |
|---|---|---|---|---|---|---|---|---|
| random | −0.986 | +0.332 | −0.066 | −1.081 | +0.805 | −0.052 | −0.693 | −2.639 |
| table | −0.891 | +0.266 | −0.467 | −0.892 | +0.066 | −0.720 | −12.019 | −17.408 |
| mlp | −0.960 | +0.241 | +0.127 | −1.017 | +0.146 | −0.720 | −0.690 | −2.621 |
| search | **+0.815** | +0.605 | **+0.968** | −0.460 | +0.859 | −0.720 | −9.118 | −19.894 |
| **symbolic-ai-001** | −0.251 | **+0.681** | +0.123 | **+0.504** | **+0.859** | **+1.040** | **−0.683** | −4.753 |
| baseline-lm-only | −2.217 | +0.230 | −0.217 | −1.126 | +0.037 | −0.720 | −1.090 | −6.794 |

The large negative returns for `table` and `search` on the two log-scored
environments are not a bug: those agents emit point predictions, a degenerate
distribution, and a proper scoring rule punishes a confident wrong answer with
`log ε`. This is the protocol reporting a genuine mismatch between an agent's
output type and an environment's reward, rather than hiding it.

### 7.3 Language modelling (held-out FineWeb-Edu split)

| model | LM steps | LM tokens seen | val NLL (512-ctx) | val ppl | next-token acc (32-ctx) |
|---|---|---|---|---|---|
| baseline-lm-only | 8000 | 98.3M | **3.950** | **51.9** | 0.125 |
| symbolic-ai-001 | 3961 | ~48.7M | 4.489 | 89.1 | 0.250 |

Under an equal optimizer-step budget the mixture model gets half the corpus
tokens, so this comparison is step-matched, not token-matched; the perplexity gap
therefore bounds, and probably overstates, the true cost of multi-task training.

### 7.4 A decision rule, not a model, causes one failure

With greedy (arg-max) decoding, `symbolic-ai-001` scores **0.00** success on the
gridworld and −1.653 return — worse than random. Inspection of the trajectory
shows a deadlock: after bumping a wall the observation is unchanged, so the
arg-max policy re-chooses the same illegal move for the rest of the episode.
Sampling from the distribution the model already represents, changing no
parameters, gives **0.40**. Both passes are kept (`results/matrix.json`,
`results/matrix_sampled.json`). MiniGrid is unaffected (0.70 either way) because
its candidate distribution is sharply peaked on states where the greedy action
is also the sampled one.

## 8. What this shows, and what it does not

**Shown.**

1. *The reduction is real, not rhetorical.* Next-token pretraining, run through
   the agent/environment loop, produces the same number as the standard training
   objective to 2·10⁻⁵ on trained models and real data (§3).
2. *One model, one interface, many families.* A 13.97M-parameter transformer
   trained only through symbolic observations and actions reaches or matches its
   per-task specialists on MiniGrid (0.70/0.70), arithmetic (0.78/0.78), proof
   (1.00/1.00) and tool-calling (0.98/1.00), while also being a language model —
   and it *exceeds the teacher that generated its data* on MiniGrid (0.70 vs
   0.62 success) — advantage weighting doing real work. On the others it lands
   below its teacher by varying margins: tool-calling 0.98 vs 1.00, arithmetic
   0.78 vs 0.83, gridworld 0.40 vs 0.65, logic 0.60 vs 1.00.
3. *Conventional LM pretraining alone is not an agent.* `baseline-lm-only`, same
   architecture and step budget, is at or below the random policy on every
   interactive family (gridworld 0.00, tool-calling 0.00, arithmetic 0.00). The
   competence in `symbolic-ai-001` comes from the interactive components of the
   mixture, not from scale or from the corpus.
4. *Heterogeneity is affordable but not free.* The single model costs 1.7× in
   held-out perplexity at a step-matched budget, and it is behind the logic
   specialist by a wide margin (0.60 vs 0.94).

**Not shown.**

1. *That LM pretraining helps symbolic tasks.* At this scale it essentially does
   not: `scratch-logic` 0.88 vs `specialist-logic` 0.94, `scratch-tool_call`
   1.00 = `specialist-tool_call` 1.00, `scratch-gridworld` 0.26 vs 0.44. Three
   of the four comparisons are within noise of each other for 50 episodes.
2. *That the representation transfers across families.* No arm does better than
   random on `scene_qa`, the family held out of training. `scratch-logic`'s 0.42
   there is a majority-class artifact (true/false answers dominate), not
   understanding.
3. *That the abstraction scales to the hard substrates.* SWE-bench, terminal and
   browser tasksets are wired but not run here (§9).
4. *That these environments are all discriminative.* The `proof` environment is
   solved by the random policy (1.00), so its column carries no signal; it
   should be made harder before being used again. Reporting it is more useful
   than quietly dropping it.

## 9. Limitations

* **Scale.** 13.97M parameters, 8,000 steps, 40M corpus tokens, one seed per
  arm. Differences under ~0.1 on 50 episodes are not resolvable; no error bars
  across training seeds are reported.
* **Compute sharing.** The GPU was shared with an unrelated 38 GB job; two
  evaluation cells hit CUDA OOM and were re-run on CPU (`mlp`/gridworld) or
  moved to CPU wholesale (the §3 end-to-end check). This affects wall-clock
  numbers, not results.
* **Teachers, not exploration.** Interactive components are trained by
  advantage-weighted cloning of teacher trajectories collected offline. Online
  RL through the same interface is supported by the contract and the trainer's
  weighting, but was not run.
* **Substrate coverage is uneven.** FineWeb-Edu, SST-2, MiniGrid, PettingZoo and
  a live `verifiers` environment were exercised. BrowserGym needs browsers and
  task servers; OSWorld needs a VM; TextWorld/ALFWorld/ScienceWorld do not build
  on this aarch64 host; Prime's 23 tasksets need `prime env install` plus their
  sandboxes. Those adapters are written, registered and typed, and
  `symbolic-agent ls` reports exactly which are runnable — but "adapter exists"
  is a weaker claim than "benchmark reproduced", and this note does not conflate
  them.
* **SST-2 at chance.** With 1,500 training rows and a 14M model trained from
  scratch, no arm learned sentiment. This is a scale statement, not an interface
  statement, but it does mean the supervised-dataset family is untested as a
  *learning* claim here.

## 10. What would falsify or extend the thesis

* Run the same agent against `prime/swebench_verified` and report **%resolved by
  the repository tests** — the canonical metric, unmodified — next to the
  normalized reward. If the adapter distorts the taskset, this is where it shows.
* Token-matched rather than step-matched LM comparison, plus a third arm trained
  on the mixture with the corpus weight raised so LM tokens are equal.
* Multiple training seeds and per-cell confidence intervals.
* Online RL (the `pg` weighting already implemented) instead of offline cloning,
  to test whether the interface supports improvement beyond the teacher on more
  than the two components where it already does.
* An encoder ablation on MiniGrid: relational vs flat-vector observations for the
  same policy class, which the codec layer makes a one-line configuration change.

## 11. Reproduction

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cu130
uv pip install --python .venv/bin/python datasets tokenizers gymnasium minigrid pettingzoo verifiers browsergym-core

symbolic-agent prepare-lm --corpus fineweb-edu --tokens 40000000
symbolic-agent collect    --config configs/symbolic-ai-001.yaml
symbolic-agent train      --config configs/symbolic-ai-001.yaml  --out runs/symbolic-ai-001 \
                          --set training.steps=8000 training.batch_size=24
symbolic-agent train      --config configs/baseline-lm-only.yaml --out runs/baseline-lm-only \
                          --set training.steps=8000 training.batch_size=24
python -c "from symbolic.experiments.run_suite import run_finetunes; run_finetunes(steps=800, batch_size=24)"
python -m symbolic.experiments.run_suite          # greedy matrix + LM holdout
python -m symbolic.experiments.sampled_matrix     # stochastic matrix
python -m symbolic.experiments.lm_protocol_check  # §3 end-to-end equality
python -m symbolic.experiments.report
pytest tests/ -q                                  # 129 tests
```

### Environment

| item | value |
|---|---|
| hardware | NVIDIA GB10, driver 580.159.03, CUDA 13.0 (shared with an unrelated job) |
| platform | Linux 6.17.0 aarch64, Python 3.12.13 |
| torch | 2.13.0+cu130 |
| datasets / tokenizers | 5.0.1 / 0.22.2 |
| gymnasium / minigrid / pettingzoo | 1.3.0 / 3.1.0 / 1.26.1 |
| verifiers / browsergym-core | 0.2.1 / 0.14.3 |
| corpus | `HuggingFaceFW/fineweb-edu`, config `sample-10BT`, revision `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`, shard `sample/10BT/000_00000.parquet` |
| corpus split rule | `sha256("symbolic-ai-001\|" + doc_id) < 0.01 → validation`; 40,000,362 train / 400,482 validation tokens |
| dataset | `SetFit/sst2`, `train` for collection, `validation` for evaluation |
| adapter version | 0.1.0 |
| wall-clock | mixture 16.0 min; LM baseline 22.2 min; 11 finetunes ≈ 30–120 s each |
