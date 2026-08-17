---
date: 2026-08-16
author: agent-premise-selection
status: idea
related: [2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]
---

# Is `frontier-001` buying the scope rather than the map?

The premise-selection ladder found that on the derived bucket the whole 0.833 is
free to a lookup **scoped to the object** and 0.714 of it is unavailable to one
scoped to the whole graph — the expensive thing is binding the premise to the
question's argument, not learning the six-pair map.

`frontier-001` scores 0.532 / 0.072 on the same slice with a learned guard, and
its write-up reads the win as a *hypothesis form* (the map form) taking the
channel. If the ladder is right, the map was never the hard part. So: **is the
guard doing scoping?**

Two ways to find out, neither expensive:

* Ablate the map form while keeping whatever restricts the guard's candidates to
  the object, and vice versa. Whichever half survives is what was bought.
* Score `frontier-001`'s chosen premise against the same `right node` /
  `a kind label` diagnostic the ladder prints. If it picks a kind label ~1.0 and
  the *right* object's kind ~0.53, its number is the scoping success rate and
  the map is free — which would be the same shape as the lookup's 0.999 / 0.233.

The second is the cheaper and the more falsifying, and it needs the run's
weights, which are not tracked — so it has to ride along with a re-run rather
than be done from `runs/`.

A third arm the ladder makes obvious and nobody has: **scope to the object but
across a scene with more objects.** The whole-graph selector lands at 1/4 = the
objects per scene. If that is really the mechanism, widening the scene to eight
objects should move the whole-graph rung to ~1/8 and leave the sibling rung at
1.000. That is a prediction with a number in it, and it would either confirm the
mechanism or kill it outright.
