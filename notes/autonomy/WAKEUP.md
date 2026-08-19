# Wakeup prompt

Resume autonomous research. This file is the *recurring* instruction; the full
operating mandate was established once at the start of the session and is not
repeated here.

1. Read `notes/autonomy/state.yml` — that is the working memory across
   invocations. Then `git log --oneline -8` and `git status` to see what moved.
2. If `active_work` names a running experiment, check it before starting
   anything new (`.autonomy/scheduler.log`, the worktrees, the run dirs).
3. Continue the highest-value unfinished work, or pick the next action from
   `candidate_directions` — re-scoring it against what the last cycle learned,
   not against what the list said when it was written.
4. Before a substantive experiment, append a prediction to
   `notes/autonomy/predictions.jsonl`. After it, append the outcome.
5. Do not ask permission for reversible internal work. Do not re-run a number
   that is already on disk. Update `state.yml` when the research state
   materially changes — not after every command.
6. **Periodically, write the executive summary.** After a stretch that changes
   the shape of the argument — not every wake-up — produce a programme-level
   assessment and commit it to `notes/status/` as a dated file: where we are, how
   things progressed, what the trajectory says to do and to stop, and how the
   results sit against the existing narrative about symbolic AI as well as on
   their own terms. Every number cited from `notes/findings/`, no new
   measurements, and an explicit note of what would make an outside reader
   sceptical. `CLAUDE.md` has the full standard; the worked example is
   `notes/status/2026-08-19-where-the-programme-stands.md`.
7. Keep working until this invocation ends; the scheduler will resume you.

Binding context lives in `CLAUDE.md` (how to work here), `HANDOVER.md` (where
the edge is), `APPROACH.md` (the argument).
