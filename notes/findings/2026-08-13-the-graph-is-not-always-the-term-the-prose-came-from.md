---
date: 2026-08-13
author: agent-a8d3c1e7
status: provisional
related: [2026-08-13-vendoring-the-generator-is-byte-identical, 2026-08-13-is-the-chinese-score-grammar-or-a-fingerprint]
---

# The `instance_id` guard cannot fail, and outside English it should have

## The claim that was wrong

`symbolic_ai_models/data/curriculum.py::generate` calls the generator twice —
`example(seed, language=)` for the prose and `structured(seed)` for the term —
and pairs the results. Its docstring said:

> the `instance_id` on both is what certifies they match, and a mismatch raises
> rather than passing a mislabelled pair downstream

It certifies nothing of the kind. `instance_id` is
`blake2b(f"{lesson}|{seed}|{difficulty}")` — a pure function of three arguments
both calls are given. It is equal whatever the two calls returned. The guard has
never been able to fail, and the whole repo's premise that "for each text there
is a true structure" was resting on it.

It does still catch the two calls being handed *different seeds*, which is
probably the mistake it was really written for. It has been left in place, with
the docstring corrected to say what it does.

## Whether it costs anything: measured, not argued

179 lessons × 5 seeds × 6 non-English languages, comparing the term the
generator builds with the language in force against the term it builds without
it — which is exactly the difference between the two calls, because
`Lesson.example` sets the `ACTIVE_LANGUAGE` context variable before building and
`Lesson.structured` does not.

| | |
|---|---:|
| English: lessons whose two builds disagree | **0 of 179** |
| non-English: (lesson, language) cells that disagree | **6 of 1,074** |

The six: `center_embedding`, `event_semantics`, `long_range_agreement`,
`thematic_roles` and `pronoun_coreference` in Spanish; `pronoun_coreference` in
Chinese. The mechanism is four generators in `generators/extra.py` that draw
material from the active language's lexicon.

**No published number is affected.** Every run in this repo is English, where
the two builds agree on all 179 lessons. What is affected is anything
cross-language — the transfer section of `RESEARCH_LOG.md`, and the
cross-language probe in `symbolic_ai_parsers`.

## What it looks like when it bites

`center_embedding`, seed 0, Spanish: the episode's answer is `saludó`, and the
graph shipped alongside it was built in English and contains `greeted`. A
masked-node model asked for that node is graded against a symbol that does not
appear in the prompt it was shown.

`long_range_agreement` is worse than a translation difference: the Spanish build
tokenises *el granjero* as one token where the English build has *the* + *farmer*
as two, so the two graphs differ in **node count**, not just in labels.

## What would refute it

A run of the same comparison finding zero divergent cells — which is what my
first version of it reported, and it was wrong.

## Why this is `provisional`, and the mistake worth copying down

The first measurement used **one seed and one language** and returned **0 of
179**. I nearly wrote that down as "the term is language-independent, confirming
`tests/test_language.py`". Widening to five seeds and six languages found six
cells. Same failure mode as the seven slice artefacts already in this repo, at
small scale, caught only because widening the grid was cheap.

So the six is a lower bound on a five-seed grid. More seeds, or the several
hundred database-derived languages if that path is ever switched on, could find
more. The exact set is pinned in `tests/test_graph_text_agreement.py` and the
test fails in **both** directions — fewer cells means someone fixed it and owes
a re-recorded fingerprint; more means something spread it.

## Deliberately not fixed

A fix changes generation. Generation may not change without re-recording the
fingerprint and re-running everything downstream of it, and this branch's job
was to vendor without moving a byte. The test pins the current behaviour
*including the part that is wrong*, which is the cheapest way to make sure the
next person finds out.
