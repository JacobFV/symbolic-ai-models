# notes/ — the lab notebook

`RESEARCH_LOG.md` is the paper: curated, argued, and edited deliberately. This
is the notebook underneath it — where work gets written down as it happens, by
whoever is doing it, before anyone has decided what it means.

## Why one file per note

Because several agents work in **separate git worktrees at the same time**, and
a single shared file is the one thing that cannot survive that. Two agents
appending to `RESEARCH_LOG.md` conflict on every merge; two agents *creating*
`notes/findings/2026-08-13-permutation-fixes-the-copy-head.md` and
`notes/findings/2026-08-13-seeding-is-a-null.md` merge silently and correctly.

So: **never append to a shared file from a worktree. Create a new one.** The
filename carries the date and a slug, which makes collisions essentially
impossible and the directory listing chronological.

## What goes where

| directory | holds | written when |
|---|---|---|
| `findings/` | one measured result, with its floor, control and refutation status | after a sweep, not after a scratch script |
| `questions/` | one idea, hunch or open question — **the parking lot** | the moment it is noticed, whether or not anyone will chase it |
| `decisions/` | one choice and the reasoning, including what was rejected | when a design fork is taken, *before* the work |
| `lessons/` | one **mechanism** that produces wrong claims — the mistake, what it cost, and the guard | after a wrong reading is caught, whatever caught it |

### `lessons/` records mechanisms, not claims

`RESEARCH_LOG.md` has a "believed and false" table listing claims that died.
This directory lists the **mechanisms that killed them**, which is the reusable
half: a claim is wrong once, and a mechanism keeps producing wrong claims until
something structural stops it. Twenty-nine entries so far, covering slice
inversions, silent-property failures, and the substrate decisions that outweigh
every model.

Read these first when arriving cold, and write one whenever a wrong reading is
caught — including when it was caught by reading the code rather than by a test,
which is how the most recent one was found.

### `questions/` is a parking lot, and capture must stay cheap

The point is to **pile ideas up without opening a thread on each one**. Most of
what gets noticed mid-experiment is worth writing down and not worth doing now,
and the alternative to a parking lot is that it lives in one agent's context and
dies there. Several good ideas have already been lost that way.

So the rigour bar below applies to **findings, not to ideas**. A question note
can legitimately be three lines:

```markdown
---
date: 2026-08-13
author: lead
status: idea
---
Cluster to ~334 classes and see whether it recovers the measured effective rank.
If it does, the class count stops being a hyperparameter.
```

That is a complete, useful note. Do not let "I have not thought it through"
stop you writing it — unthought-through is what the directory is for. A note
matures from `idea` to `open` when someone adds what would answer it, and to a
`findings/` entry when someone measures it. Never delete an idea for being bad;
mark it `status: rejected` with one line saying why, because the next person
will otherwise have it again.

## Frontmatter

```markdown
---
date: 2026-08-13
author: <lead | agent-slug>
status: measured | provisional | refuted | superseded
related: [other-note-slug, ...]
---
```

`status` is the load-bearing field. **`provisional` is the default for anything
whose only controls were designed by its own author** — this repo has had
author-designed controls pass while being hollow. A note earns `measured` when
something independent has tried to break it.

## The three rules that make a note worth reading

1. **Say what would have refuted it, and say it in the note.** Preferably
   written before the number arrived. A finding with no stated refutation
   condition is an anecdote.
2. **A number without its floor is not a result.** Quote the floor, and for
   label numbers quote the copy ceiling too. Same bar as `RESEARCH_LOG.md`.
3. **Name the slice.** If it is not the full 179-lesson sweep, say so in the
   first sentence. Slice artifacts have produced confident wrong readings
   **seven times** here — a note that hides its slice will be the eighth.

## What this does not do

It does not coordinate agents in real time. Worktrees are isolated: an agent
cannot see another's uncommitted files, so there is no live "who is working on
what" registry that actually works. **Claiming work is the operator's job**, not
a file's. What `notes/` gives you is durability and ordering — a later agent
reads an earlier one's findings instead of rediscovering them, and nothing is
lost to a merge.

## Promotion

Notes are cheap and are not curated. When a finding survives independent
challenge and changes what the repo believes, it gets **promoted** into
`RESEARCH_LOG.md` — rewritten, not copied — and the note is marked
`status: superseded` with a pointer. `RESEARCH_LOG.md` stays short enough to
read cold; `notes/` is allowed to be long.
