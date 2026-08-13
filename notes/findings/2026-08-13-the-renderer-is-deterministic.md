---
date: 2026-08-13
author: agent-a8d3c1e7
status: measured
related: [2026-08-13-generator-templating-limits-transfer, 2026-08-13-vendoring-the-generator-is-byte-identical, 2026-08-13-is-the-chinese-score-grammar-or-a-fingerprint]
---

# Where the curriculum's 0.54 bits of long-range order come from: the renderer cannot vary

An answer to the open question in
`questions/2026-08-13-generator-templating-limits-transfer.md`, from reading the
generator while vendoring it. Not a new measurement of the bits — that number is
`asymptotics.py`'s and stands — but a mechanism for it, and a seam for changing
it that does not touch a single existing episode.

## The mechanism

`Lesson.example` ends in one line that matters:

```python
observation = lang.render(obs)
```

and the render path performs **no random draw at all**. Across `grammar/`,
`languages/`, `presentation.py` and `_structure.py`, three files mention
randomness: two in prose comments, and the third is an unused `import random` in
`grammar/compile.py`. `grammar/linearize.py` — the module that turns a term into
a word sequence for any of the seven languages — has none.

So surface realization is a **pure function of (term, language, presentation)**.
Every bit of within-lesson variation is variation in the term, and the term comes
from one generator function per lesson. The token 128 positions back is the same
slot of the same template every episode because there is exactly one template and
nothing downstream is allowed to vary it.

That is the whole explanation for 0.54 bits of order structure at d=128 against
~0 for prose beyond d≈16. It is not a subtle statistical property; it is a design
decision, and a defensible one — a deterministic renderer is what makes the
graph/text pairing exact.

## The seam, which already exists

`Presentation` carries `language`, `answer_format` and `surface`; it is part of
an episode's address through `Presentation.key()`; `ANSWER_FORMATS` already holds
eight formats. A new realization mode is therefore **a new presentation or a new
lesson registered beside the existing ones**, which produces a *new address*
rather than a new rendering of an old one.

That matters more than it sounds. It means the templating experiment can be run
without invalidating anything: the fingerprint pins the default presentation,
which is exactly the set of episodes every published number was drawn from, and a
new presentation leaves all 1,432 digests untouched. The registered-beside rule
is not a discipline tax here, it is the only version of the experiment that is
even measurable — you need both the rigid and the varied corpus in one sweep to
say what the variation bought.

## What would refute the mechanism

A random draw somewhere on the render path that I missed — which would show up as
a fingerprint that is not reproducible across processes. It is: checked under
`PYTHONHASHSEED=1` against `999`, identical.

## It also unblocks the Chinese-fingerprint question

`questions/2026-08-13-is-the-chinese-score-grammar-or-a-fingerprint.md` asks
whether `template-002`'s cross-language score is grammar or a rendering
fingerprint, and proposes perturbing the rendering — bullets to numbers, `;` to
newline — to find out. That perturbation is now a local edit rather than an
upstream request: bullets and separators live in `Typography` in
`grammar/linearize.py` and in the `AnswerFormat` list in `presentation.py`, both
of which are already keyed into the address. Registering a perturbed format
beside the eight existing ones is the whole experiment, and it changes no
existing episode.

## What this does not say

Nothing about whether varying realization would *help*. The prediction implied by
`asymptotics.py` is that a paraphrasing render mode should pull the d=128 order
term toward zero, and that models which currently score by exploiting it should
lose more than models that do not. Both halves are measurable in one sweep with
the variant registered beside the original, and neither has been run.
