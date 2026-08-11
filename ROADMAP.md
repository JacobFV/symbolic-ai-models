# Roadmap

State for autonomous continuation. Read `git log --oneline | head -20` first;
this file says what the work *is*, the log says how far it got.

## Now: decouple parsing from reasoning

Every symbolic model currently has its parser welded on. `syllogism` owns a
categorical fragment, `symbolalg` a clause regex, `grammar` a class induction.
That makes "which parser" and "which reasoner" one choice when they are two, and
it means a better parser cannot be dropped under an existing reasoner.

The split:

- `parsers/` — a `Parser` is `text -> ParseResult` (tokens, classes, brackets,
  facts). Registered by name, fitted on training episodes only.
- `models/` — a reasoner declares `extra.parser` and gets whatever it names.
  Reasoners must work with *any* parser, including `none`.

## Why parsers can be scored exactly here

`langcurriculum` renders every episode from a typed term it also hands over, so
for each text there is a true structure. A parser's classes can be scored
against the roles the generator actually used — no annotation, no judge, and an
unbounded supply of fresh episodes, so a parser cannot be tuned to a test set.

Metric: pairwise clustering F1 between "same induced class" and "same true
role", where a word's true role is the multiset of (parent label, slot) it
occupies in the term graph.

## Task list

- [x] `parsers/base.py` — Parser, ParseResult, registry
- [x] `parsers/evaluate.py` — gold roles from the graph, clustering F1
- [ ] parsers: `none`, `regex`, `categorical`, `induced`, `chunker`
- [ ] `symbolic-ai-models parsers` and `parse-eval` CLI
- [ ] reasoners accept `extra.parser`; sweep the parser x reasoner matrix
- [ ] scale test: parser quality vs number of training episodes (the curriculum
      is unbounded, so this curve is free and is the point of the exercise)

## Rules for autonomous work

1. Never commit with tests failing. `uv run pytest tests/ -q`.
2. One coherent change per commit, with a message saying what was learned.
3. Report negative results. A parser that does not help is a finding.
4. Do not tune against the evaluation set; seeds >= 1_000_000 are eval only.
