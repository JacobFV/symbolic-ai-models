# Working agreements

Standing instructions for autonomous work in this repo. `ROADMAP.md` holds the
task list and the experimental rules; this file holds the workflow ones.

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
  and settle design choices on held-out *training* episodes.
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

The bar is the same as any commit: `uv run pytest tests/ -q` passes. If it does
not, fix it or say plainly that it is broken — but the default is merge.

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

## Scope

The **symbolic models are the subject**. The neural half is a control, kept for
comparison and off by default (`SYMBOLIC_AI_MODELS_NEURAL=1`). Do not spend
effort on it beyond what is needed to keep the control honest, and never let it
take the GPU — the machine has real training on it, and everything here runs on
CPU.
