# Working agreements

Standing instructions for autonomous work in this repo. `ROADMAP.md` holds the
task list and the experimental rules; this file holds the workflow ones.

## What we are here to do

**Build a language-understanding substrate whose cost per correct answer is a
different order of magnitude from neural inference, and whose reasoning is
inspectable rather than inferred.** `APPROACH.md` is the argument. Read it
before the task list, because the task list is a record of what looked worth
doing when it was written and the argument is the thing being tested.

This is a **frontier bet, not a benchmark chase.** Nobody has run the pure
symbolic direction at this scale with this tooling, so the failure mode to avoid
is not losing to a transformer — it is spending the year proving what was already
known. Every session should be able to name the thing it now knows that nobody
knew when it started. If the answer is "we confirmed a number that was already on
disk", the session was spent wrong.

Three consequences that outrank almost everything below:

- **Rigour is the guard on the work, not the work.** The apparatus in this file
  was written after a run of confident wrong readings and it earned its place.
  It has also, twice, become the activity. A control, a refuter and a floor audit
  belong on a headline going into `RESEARCH_LOG.md` and nowhere else.
- **Price the capability, not the token.** The north star is
  `$ / solved episode above floor`, computed by `symbolic_ai_core/cost.py` and
  printed by `symbolic-ai-models cost`. A throughput number is an *input* to it
  and is never a headline — this repo led with one for months and it said
  nothing, because a system can be arbitrarily fast and understand nothing.
  Cost is charged to the **system**: if a reasoner only works because something
  upstream produced a graph, that upstream component is in the ledger whether or
  not it exists yet.
- **The 179-lesson curriculum is a development harness, not the benchmark.**
  It is teacher-forced, position-level, and 98.6% scaffolding. It is an
  excellent instrument for forming a hypothesis and the wrong one for reporting
  it. Work that moves the benchmark toward the five properties in `APPROACH.md`
  outranks work that moves a model up the existing table.

## You are the overseer. Decide, do not ask.

Standing instruction from the user: **do whatever you judge needs doing, and do
not ask questions to get permission.** Judgement calls are yours — which
experiment is worth running, what to refactor, when to delegate, what to fix on
sight. Presenting a menu of options and waiting is the failure mode to avoid;
so is asking "shall I?" about work you already believe in.

This does not license carelessness, and it does not repeal anything below. The
bar stays: state what you expect before you run it, keep the tests green, put a
new model beside the old one, and report what you actually found — including
when it contradicts what you said an hour ago. Autonomy is about not needing
permission, not about not needing evidence.

Two things still go to the user rather than being decided alone: anything
outward-facing or hard to reverse (publishing, deleting work, rewriting shared
history), and a genuine fork in the *research direction* where the evidence does
not pick a side — say which way you lean and why, then proceed on your own
recommendation unless told otherwise.

## Breadth first. Build all of them, then follow the one that moves.

Standing instruction from the user, 2026-08-16, after a session that got this
exactly backwards: **given N candidate directions, build N cheap arms and get a
number on each, then pick the live one and go deep.** Do not take candidate 1,
polish it to publication standard, and report back having never touched 2, 3 and
4. That is the failure mode to avoid, and it is expensive in the way that
matters — it spends the session's wall clock on certainty about something that
was already mostly known instead of on finding out which direction is real.

The session that prompted this: four papers came in, one was built to a full
finding with controls, refuters and a merged write-up, and the other three got
three-paragraph notes. The one built was the one whose experiment the repo had
*already set up*. So the whole session bought a confirmation, and the three
directions nobody had a number for stayed at zero.

What this looks like in practice:

- **Fan out before you go deep.** Each candidate gets the smallest thing that
  produces a comparable number — a registered model, a sweep row, one arm. Hours
  each, not a session each. Run them in parallel, in their own worktrees.
- **Rank on the numbers, then commit to one.** The second pass is where controls,
  refuters, floors and the write-up go, and it goes on the arm that earned it.
- **A dead arm is a result and costs one note.** `notes/findings/` with the
  number and the reason, `status: provisional`, move on.
- **Verification is proportional to the claim.** A number that is going into
  `RESEARCH_LOG.md` or a merged headline gets the full bar below — floor,
  control, renaming, the refuter. A number that is deciding *which arm to chase
  next* does not; it needs to be honest and reproducible, not bulletproof. Do not
  spend an hour proving a scouting number to four decimals when its only job is
  to be bigger or smaller than three other scouting numbers.
- **Two rules do not relax, ever, at any depth:** say what you expect before the
  number lands, and report what you actually found. Cheap and fast is not licence
  to be wrong, and a scouting arm that is wrong sends the deep pass down the
  wrong hole, which costs far more than it saved.

### Do not re-run to confirm. Build the next thing.

Standing instruction from the user, 2026-08-17, said with some force: *"why do
you constantly re-run everything? we don't care about being 'scientific', we
care about making progress."* The rigour apparatus below was written after a
run of confident wrong readings and it earned its place — but it has become the
work rather than the guard on the work. Concretely, stop doing these:

- **Re-running a sweep to confirm a number that is already on disk.** It is on
  disk. Read it.
- **The full 2,500-test suite before every commit.** Said again on 2026-08-18,
  interrupting a full run: *"we need to stop testing so much."* Run the subset
  that could possibly notice what you touched, and only that. A new module with
  its own passing test file is the whole answer. Once per branch at the very
  end, if at all — and never as a ritual before committing.
- **A refuter, a permutation control and a floor audit on a scouting number.**
  Those belong on a headline going into `RESEARCH_LOG.md` and nowhere else.
- **A written finding for every intermediate step.** One note when an arm
  resolves, not one per measurement inside it.
- **Census and audit passes that produce no new capability.** Counting what is
  registered versus scored is not progress; building the next model is.

The trade being made explicitly: we will publish some things that turn out
wrong, and we will find out because the next experiment contradicts them, not
because a control caught it in advance. That is the user's call and it is the
right one at this stage — the repo has 51 scored models and a shortage of
*directions*, not a shortage of decimal places.

## Automate the loop. Do not hand-drive it.

The user's phrase is **"automate the RSI loop"** — propose, implement, evaluate,
keep what wins, propose again, without a human turn between each step. Sitting in
the loop hand-driving one model at a time is the thing being replaced.

`scripts/rsi_loop.py` is the driver. It reads a candidate list, builds each arm
in its own worktree, sweeps them against the same config and floors, ranks the
rows, writes a `notes/findings/` entry per arm, and emits the next round's
candidates from what survived. Extend the candidate generator rather than running
arms by hand.

When you find yourself about to run a fifth sweep by typing a fifth command,
that is the signal to put it in the loop instead.

## Edit files with the Edit tool, not with `str.replace` in a heredoc

Learned three times in one day, at a cost of hours:

- `frontier-009` was silently turned into an unregistered hybrid because the base
  class's assignment was a **prefix** of the subclass's, and `str.replace` hit
  both. Its `type_acc` moved 0.8652 → 0.8540 and the model under test read as a
  failed experiment.
- The `corefer` gate patch tripped the same prefix trap —
  `self.gate_map = MassCalibrator()` inside
  `self.gate_map = MassCalibrator().fit(...)`.
- `_type_atoms_at` was written into **both** `node_votes` implementations, one of
  which had no `vals` in scope. 36 tests failed.

`str.replace` replaces **every** occurrence and tells you nothing. The Edit tool
requires the match to be unique and fails loudly when it is not, which is the
property that was missing all three times. **Use it.**

When a heredoc really is the right shape — several coordinated edits, or
generated text — then `assert s.count(old) == 1` before every single one. That
assert caught the second of the three and cost one line.

And the guard that catches what neither does, because two of the three were
invisible to the suite: **after touching anything shared, re-run one unchanged
model and diff its row.** See
`notes/lessons/2026-08-17-a-default-computed-in-init-captures-the-base-classs-values.md`.

## Delegation: what may be handed off, and to what

Parallel agents are how this repo gets through a wide front, and two of them have
already produced findings the lead would not have had time to run. The rule is
about *which cognition* the work needs, not about how much of it there is.

- **Mass-research and implementation fan-outs run on Opus.** When a workflow or a
  batch of subagents is doing the *research* — designing an experiment, choosing
  a control, deciding what a number means, writing a model — every agent in it
  gets Opus. The ideas here are novel enough that a cheaper model does not fail
  loudly; it fails by producing a plausible experiment with the wrong control,
  and this repo's whole cost history is confident wrong readings that looked
  fine. A weaker model is not a cheaper version of this work, it is a different
  and worse experiment.
- **Directly managed subagents are fine at whatever fits.** Work whose result you
  will read and check yourself — find every call site, run this sweep and report
  the table, port this test — does not need the strong model, because you are the
  one doing the judging.
- The test is *who decides*. If the agent's judgement lands in a finding, it is
  research and it runs on Opus. If your judgement is between it and the record,
  it is managed work.

Give every parallel agent **its own worktree**. An agent told to "make a branch"
makes it in this checkout and moves your HEAD mid-task — see rule -0.3 in
`ROADMAP.md`.

## This is research, not a queue of tickets

The task list is a record of what looked worth doing when it was written. It is
**not** an instruction to execute the next item. Before running anything, say
what you expect and why — and if the honest answer is "the next item is not the
best experiment available", say that instead and do the better one. An
experiment nobody could have predicted the outcome of is worth ten that confirm
what the list already assumed.

What that means concretely, all of it learned here the expensive way:

- **State the hypothesis and what would refute it, before the number lands.**
  This repo has twice had a reading drift toward flattering the write-up — the
  `gru` curve was recorded as "flat" from six noisy points because flat was the
  answer already written down. Fixing the interpretation in advance is the only
  known defence, and it is cheap.
- **Ask what the measurement is actually measuring.** `label_acc` and
  `label_bits` are both in every `summary.json` and they rank these models
  close to inversely. A ranking is a property of a metric, never of a set of
  models, and a result quoted without saying which metric produced it is not a
  result. Where two defensible metrics disagree, that disagreement *is* the
  finding — report it rather than picking the flattering one.
- **Suspect the harness before the architecture.** The largest measured effects
  in this repo's history are not differences between models. Models span about
  0.1 lift; harness decisions span 0.15 to 2.0 — abstention falling back to the
  structural prior, held-out calibration, the type head getting its own
  calibrator, strengthening the floor. When something moves a lot, the first
  hypothesis is that the contract changed, not that the reasoning improved.
- **A negative result is a result, and a null is worth publishing.** Three
  candidate features in a row failing is a finding about the combiner. Record
  what did not work and why it was expected to, in `RESEARCH_LOG.md`.
- **Prefer the experiment that could embarrass you.** Renaming invariance,
  copy ceilings, per-question rather than pooled AUC, floors that use every
  feature the model does — each of these overturned something. Reach for the
  measurement that could show the work is not doing what it claims.
- **Do not tune against evaluation.** Seeds >= 1,000,000 are eval only. Form
  and settle design choices on held-out *training* episodes. There is now a
  **development split** to do that on — `configs/rsi_dev.toml`, scored seeds
  from 500,000, runs landing in `runs/rsi/` — because until `eval_seed0` became
  a field there was no way to obey this rule while scoring anything, so every
  knob ever fitted by reading a sweep was fitted against evaluation without
  anybody choosing to. `scripts/rsi_loop.py` refuses to rank on evaluation
  seeds; `--final` is the one door, it takes an already-chosen candidate, and it
  ranks nothing.
- **Rank on the number a memoriser cannot buy.** Any search ranked on
  `label_acc` walks into this repo's oldest trap, because accuracy here rewards
  memorising the vocabulary. The loop's default objective is `equivariant` — the
  accuracy that survives permuting every symbol — and it prints `acc`, `bits`,
  `renamed` and `drop` side by side whatever it ranks by.
- **The sweep is the authority.** Scratch scripts have contradicted
  `symbolic-ai-models sweep` twice, both times flattering the write-up. Use
  them to form hypotheses, never to report.

## Write it down in `notes/`, even when you are not going to chase it

`notes/` is the lab notebook; `RESEARCH_LOG.md` is the paper. **One file per
note** — several agents work in separate worktrees at once, and a shared file is
the one thing that cannot survive that. Two agents appending to
`RESEARCH_LOG.md` conflict; two agents creating different filenames merge
silently.

- `notes/questions/` is a **parking lot**. Pile ideas up without opening a thread
  on each. A three-line note with `status: idea` is a complete note — capture is
  meant to be cheap, and the rigour bar applies to findings, not to hunches.
  Ideas that live only in one agent's context die there, and several already have.
- `notes/findings/` needs the floor, the control, and what would have refuted it.
- `notes/decisions/` records a fork *before* the work, including what was rejected.

- `notes/lessons/` records **how we go wrong** — the mistake, what it cost, and
  the guard that stops it recurring. `RESEARCH_LOG.md`'s "believed and false"
  table lists claims that died; this lists the *mechanisms* that killed them,
  which is the reusable half. A claim is wrong once; a mechanism keeps producing
  wrong claims until something structural stops it. Read these first when
  arriving cold — six entries cover eight slice inversions, four silent-property
  failures, and the substrate that outweighs every model.

Read `notes/README.md` before writing one. Findings get promoted into
`RESEARCH_LOG.md` — rewritten, not copied — once something independent has tried
to break them.

## New models go beside the old ones, never in place of them

Register a variant as `name-002` or `name-noprose` and leave its predecessor
registered, so one sweep prints both rows against the same floors and the
difference is measured rather than asserted. Editing a model in place silently
redefines every published number carrying its name; that has already happened
twice. See `RESEARCH_LOG.md` for the convention.

## Branches: always merge, never ask

Work done on a branch gets **merged into `master` when it is green**. Do not
park it, do not ask for approval, do not leave it for the user to decide. A
finished branch sitting unmerged is unfinished work that looks finished.

The bar is the same as any commit: `uv run pytest tests/` passes. If it does
not, fix it or say plainly that it is broken — but the default is merge.

**Run it without `-q`.** `pyproject.toml` already sets `addopts = "-q"`, so
passing it again makes `-qq` and pytest prints **no summary line at all** — you
get an exit code and no test count. The exit code is a real signal (non-zero on
any failure, 5 if nothing was collected), but it cannot tell a green suite from
a silently shrinking one. Report the count: it is **2,433** as of 2026-08-17 (10 skipped). That number goes stale every time a test is added — if yours disagrees, check that it disagrees *upward* and update this line, because a count that fell is the signal this sentence exists to give you.

Two traps this repo has already hit:

- **A modify/delete conflict resolves silently in the wrong direction.** If
  `master` deleted files that the branch only *added* and never touched again,
  git takes the delete without a conflict and the branch's work vanishes from
  the merge. Only the file that was modified on both sides conflicts loudly.
  After merging, check that what the branch was *for* is actually present —
  `symbolic_ai_models models` should list its models, not just compile.
- **A parallel agent given "make a branch" makes it in this checkout**, which
  moves your own HEAD onto it mid-task. Give the agent its own worktree, or
  accept it owns the checkout and work from one of your own
  (`git worktree add`). See rule -0.3 in `ROADMAP.md`.

## Committing

- Never commit with tests failing.
- One coherent change per commit; the message says what was *learned*,
  including negative results and refuted hypotheses.
- Never `git add -A` in a checkout something else is writing to. It has already
  swept a parallel agent's untracked files into an unrelated commit. Stage
  explicit paths.

### Green at every commit, without paying for the whole suite every time

"Never commit with tests failing" is not "run `pytest tests/` before every
commit". The suite is minutes of wall clock and the user's time is the scarce
resource here — the point of this repo is research, not re-running results that
already passed twenty minutes ago.

The `symbolic_ai_core` refactor got this wrong: six commits, the full suite run
before each, when almost all of them touched a handful of modules whose tests
run in seconds. Roughly an hour of waiting bought nothing that this would not
have:

- **Between commits in a series, run the tests that could possibly notice.**
  Pick them from what the commit touched — a registry change runs
  `test_registry.py test_models.py test_graph_parsers.py`, not the training
  loop. Say which subset you chose and why, so the choice is reviewable.
- **Run the full suite once**: before the *first* commit of a series, to
  establish the baseline is green, and after the *last*, which is the run that
  actually licenses the merge.
- **A green subset is not a green suite.** If a series ends and the full run has
  not happened, the branch is not merge-ready however many subsets passed.
- The expensive tests are the ones that generate the curriculum —
  `test_curriculum_fingerprint.py` draws 179 lessons x 5 seeds x 7 languages.
  Run it when generation or the data plumbing could have moved, which for most
  commits is never.

## Scope

The **symbolic models are the subject**. The neural half is a control, kept for
comparison and off by default (`SYMBOLIC_AI_MODELS_NEURAL=1`). Do not spend
effort on it beyond what is needed to keep the control honest, and never let it
take the GPU — the machine has real training on it, and everything here runs on
CPU.
