# Working agreements

Standing instructions for autonomous work in this repo. `ROADMAP.md` holds the
task list and the experimental rules; this file holds the workflow ones.

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
