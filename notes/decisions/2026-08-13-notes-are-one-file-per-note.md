---
date: 2026-08-13
author: lead
status: adopted
---

# Notes are one file per note, because worktrees are isolated

Parallel agents work in separate git worktrees. A single shared file
(`RESEARCH_LOG.md`, `ROADMAP.md`'s task list) conflicts on every concurrent
edit, and an agent cannot see another's uncommitted work at all.

One file per note makes the merge trivial — different filenames, no conflict —
and makes the record survive an agent that gets interrupted. `RESEARCH_LOG.md`
stays the curated view and is edited by the operator; `notes/` is the notebook
and is written by everyone.

**Rejected:** appending to `RESEARCH_LOG.md` from worktrees (conflicts), a
single `IDEAS.md` (same), and a live claim registry in git (does not work —
worktrees cannot see each other's uncommitted files, so claiming work stays the
operator's job).
