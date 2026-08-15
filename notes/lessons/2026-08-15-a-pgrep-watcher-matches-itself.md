---
date: 2026-08-15
author: lead
status: measured
related: [2026-08-14-a-sandboxed-test-reports-environment-faults-under-its-own-name]
---

# A watcher that greps for a process name matches the shell that greps

## The mechanism

Wait for a job to finish by polling for its name:

```bash
until ! pgrep -f "kg_normalize.py" >/dev/null; do sleep 180; done
echo "finished"
```

The string `kg_normalize.py` is in **this shell's own command line**, so
`pgrep -f` matches the watcher itself. The condition can never become false. The
loop runs forever and the completion never fires.

Worse than a hang: `pgrep -cf` from a *third* shell then reports 3 processes and
they look like the job still running. The watcher does not merely fail to
report — it manufactures evidence that there is something to report on.

## What it cost

`kg_normalize.py` finished at **14:10:57** and wrote its manifest. Two watchers
kept spinning, and a status check at 14:33 read "3 procs running" and reported the
job as in flight. It was 22 minutes stale, and would have stayed stale until the
600-second harness timeout, or forever if the timeout had been longer.

The tell that broke it: **every output file was already written** — 23 edge
tables, 11 node tables, and the manifest — while `pgrep` still claimed the
producer was alive. Artefacts and process state disagreed, and the artefacts were
right.

## The guards

1. **Watch the artefact, not the process.** `until [ -f out/manifest.json ]` has
   no self-reference and is what the job actually promises. Where a process check
   is unavoidable, exclude self: `pgrep -f "[k]g_normalize.py"`, or match on the
   interpreter path rather than the script name.
2. **When process state and output state disagree, believe the output.** A file
   with content is evidence; a `pgrep` count is an inference about command-line
   strings.
3. **A status report should name the evidence it read.** "3 procs" and "manifest
   written 14:10" are different claims and only one of them was checked.

## The general form

This is the same shape as
[[2026-08-14-a-sandboxed-test-reports-environment-faults-under-its-own-name]]:
a monitoring construct that fails in a way indistinguishable from the condition
it monitors. There the sandbox's own breakage was reported under the test's name;
here the watcher's own process is reported as the job. **Whenever a check can
observe itself, its negative result means nothing** — and the fix in both cases
is to make the observation narrower than the thing being observed, not to trust
the check harder.
