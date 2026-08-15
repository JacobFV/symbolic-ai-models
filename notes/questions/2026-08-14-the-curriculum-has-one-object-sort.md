---
date: 2026-08-14
author: agent-lean-006
status: idea
related: [2026-08-14-the-lean-gate-closes-the-kernel-loses-to-an-arity-check,
          2026-08-14-the-ir-is-a-knob]
---

The `006` elaboration turned up a property of the **curriculum**, not of the
kernel, and it is probably worth more than the gate result: every entity symbol
in an episode collapses into a single metavariable component. `alice`, `apple`,
`action` and `manipulate` all get the same type, because nothing in the
generated term ever distinguishes them. The rigid types are only `Nat`, `Str`,
`Chr` and `Prop`, and those come from literals rather than from structure.

Two things follow that nobody here has measured:

1. **Any type-based method is capped by this**, not only Lean. `005`'s
   AtomSpace arm will hit the same wall wherever it wants to match on a type.
2. **The generator could be asked for the sorts it already knows.**
   `langcurriculum` builds a scene of objects, a taxonomy, a set of agents — it
   *has* the sorts and throws them away when it renders the term. If
   `Lesson.structured` exposed them, the gate would be a different measurement
   entirely, and so would every model's `type_acc`.

The second is the interesting one and it is a change to shared machinery, so it
goes here rather than getting made.
