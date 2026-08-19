---
title: A verification that uses the mechanism's own predicate decides the experiment
date: 2026-08-19
status: lesson
---

## What happened

An arm was built to test whether a declared vocabulary can be **worse than
none**, by misfiring on a sentence it was not written for. It shipped with a
verification step, which is normally the sign of a careful experiment:

```python
def _verify_adversarial():
    """No adversarial variant may contain a declared anchor. Checked, not eyed."""
    for role, forms in ADVERSARIAL.items():
        for form in forms:
            tokens = re.findall(r"[a-z]+", form.lower())
            for r, words in ROLE_ANCHORS.items():
                hit = [w for t in tokens for w in words if t.startswith(w)]
                assert not hit
```

And the mechanism under test:

```python
def _anchor_role(sent, anchors):
    tokens = re.findall(r"[a-z]+", sent.lower())
    hit = {role for role, words in anchors.items()
           if any(t.startswith(w) for t in tokens for w in words)}
```

**The same predicate.** The verification asserts that the mechanism does not
fire, so the experiment measures what happens when it does not fire. The
misfiring it was built to look for was excluded by its own assert.

The result read as a striking convergence — the arm landed on the emptied-anchor
floor "to three decimals", which was written up as evidence that the anchors
never misfire. It agrees **case by case**, 252 of 252, because it is the same
computation.

## Why it was invisible

The verification looks like rigour, and in the direction it was written it *is*
rigour: it stops an adversarial phrasing accidentally containing an anchor and
making the experiment easy. Nothing about it announces that it also makes the
second question unanswerable. Two coinciding numbers then supplied the
confirmation, and coinciding numbers are the most persuasive thing an experiment
can produce.

## The guard

**Ask what your verification step asserts about the mechanism under test.** If it
constrains the mechanism's own predicate, it is not a control — it is a
precondition, and every result downstream is conditional on it.

The concrete test: *could this experiment have come out the other way?* Write
down the input that would have produced the opposite result, and check that the
verification admits it. Here it does not, in one line, and that line is above the
experiment rather than inside it.

The repair is usually the **inversion**: a second arm whose verification asserts
the mechanism **does** fire. `scripts/misfiring_vocabulary.py` is that arm, and
the answer it gives is −0.290 — larger than the effect the original arm existed
to measure.

## Related

- [[2026-08-19-a-detector-experiment-needs-a-baseline-arm-for-every-check]] —
  the same day, the same shape: numbers that mean nothing without the
  counterfactual beside them.
- The standing rule *send an independent refuter before absorbing a win* exists
  for exactly this: an author-designed control can be constructed-to-pass without
  anybody intending it.
