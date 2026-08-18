---
title: Backticks inside `git commit -m "..."` silently delete the word they wrap
date: 2026-08-18
author: lead
status: settled
tags: [tooling, git, silent-failure]
---

## The mistake

A merge commit written as `git commit -m "... `exposure` spread collapses ..."`
inside double quotes. Bash ran command substitution on the backticks, printed
`exposure: command not found` to stderr, substituted the empty string, and
committed. The message in the history now reads

> Two things degraded worse than predicted.  spread collapses to 1.6x

with the identifier gone and a double space where it was. The merge succeeded,
so nothing failed and nothing was reviewed.

## Why it matters here rather than generally

`CLAUDE.md` says the git history is part of the research notebook and that the
message says what was *learned*. A message that silently loses exactly the
identifiers — which are the things worth naming, because backticks are how one
marks a symbol — degrades the notebook in the one place it cannot be corrected
without rewriting shared history, which is forbidden.

It is the same shape as the three `str.replace` incidents: a tool that does
something plausible instead of failing, so the damage is invisible at the moment
it is done.

## The guard

Write commit messages through a **quoted heredoc**, which is what the rest of
this session used and which is immune:

```bash
git commit -q -F - <<'EOF'
Backticks are `literal` in here, because the delimiter is quoted.
EOF
```

`<<'EOF'` with the quotes is the whole guard — an unquoted `<<EOF` expands
backticks and `$` just like a double-quoted string does. If `-m` really is the
right shape, single-quote the message and accept that it cannot then contain an
apostrophe.
