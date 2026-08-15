---
date: 2026-08-14
author: agent-lean-006
status: provisional
related: [2026-08-14-lean-ir-preregistration,
          2026-08-14-lean-gate-arms-and-the-arity-floor,
          2026-08-14-the-ir-is-a-knob,
          2026-08-13-abstention-on-repair-is-below-chance,
          2026-08-13-a-control-that-could-fail,
          2026-08-13-slices-have-inverted-results-eight-times]
---

# `006`'s gate closes: the kernel refuses candidates, and an arity check refuses more

**All 179 lessons, 537 held-out training episodes (seeds 500–502), 4,443 scored
holes, median 55 candidates each. Not a slice.** Reproduced on an independent
draw of 895 episodes (seeds 800–804, different mask seed); every number below
moves by less than 0.01 and no conclusion changes.

No model was built. That is the point: the gate was pre-registered in
`notes/decisions/2026-08-14-lean-ir-preregistration.md` as the cheapest possible
death for this line, and it ran first.

## The two numbers

| filter | prune (median) | gold survival | matched random | pre-registered verdict |
|---|---:|---:|---:|---|
| `open` — the sound kernel | **0.286** | **0.9878** | 0.6341 | prune < ~30% → **dead** |
| `declared` — Lean's own rule | **0.355** | **0.9843** | 0.4855 | both high → **build** |
| `closed` — the committing arm | 0.797 | 0.7967 | 0.2558 | survival < 95% → **worse than dead** |
| **`arity` — the floor** | **0.370** | **0.9884** | 0.5056 | — |
| `hybrid` (kernel ∧ floor) | 0.388 | 0.9812 | 0.4779 | not a kernel; see below |
| `shifted` — the control | 0.286 | 0.5783 | 0.6630 | must fail, and does |

The three arms are defined in
`notes/decisions/2026-08-14-lean-gate-arms-and-the-arity-floor.md`, fixed before
this run: they differ only in what the elaborator does with what it has *not*
seen. Applied literally, the pre-registered table kills two arms and passes one.

## Why the passing arm does not open the line

**The arity floor prunes more (0.370 vs 0.355) at higher gold survival (0.9884
vs 0.9843) than the best kernel arm.**

The floor is: *reject a candidate iff no visible occurrence of it has the hole's
number of children*. No types, no unification, no translation, no IR. Every one
of the nineteen models already in the sweep could compute it from the `Graph` it
already reads.

So the pre-registration's numeric thresholds are met by a filter that is
dominated on both axes by the cheapest thing that could produce the same number.
Its own row-one reasoning applies exactly — *"the signature is too weak to
discriminate and the IR is a re-encoding with no filter"* — even though the
prune arm passed. **The gate closes.** I am not moving a threshold; I am
reporting that the number cleared its threshold and did not clear its floor, and
this repo's standing rule is that a number without its floor is not a result
(`notes/lessons/`, `rgt`'s +0.587 that was really +0.395).

The increment is real but tiny. `declared` and the floor are not nested — the
kernel rejects 3,659 candidates the floor keeps and keeps 5,468 the floor
rejects — and taking both (`hybrid`) prunes 0.388 against the floor's 0.370.
**+0.018 of median prune for an entire intermediate representation.**

Set that against the measurement that motivated the line. Candidate recall
82.7% → 93.1% → 98.7% moved dev copy accuracy 0.4036 → 0.4043 → 0.4012. Sixteen
points of candidate-set change bought 0.000. A 1.8-point change is an order of
magnitude below the change already measured to do nothing.

## The controls, and what they establish

The mechanism is genuinely there. This is not a broken instrument reporting a
null:

- **`shifted`** — the same kernel, same episode, same signature, run against a
  *different hole of the same episode*. Prune is unchanged (0.286 vs 0.286) and
  gold survival collapses **0.9878 → 0.5783**, below the matched-random 0.6630.
  The filter is reading the hole, not the candidate set.
- **matched random** — a filter keeping the same *number* of labels, chosen
  meaninglessly, would keep the gold 0.634 of the time. The kernel keeps it
  0.988. The refusals are overwhelmingly correct refusals.
- **renaming invariance** — every verdict is identical, symbol for symbol, under
  a consistent renaming of every label, in all three arms
  (`tests/test_lean_elaborate.py`). No vocabulary is being read. This is the
  control that took `ensemble-001` from 0.467 to 0.038.
- **the hidden answer** — replacing every hidden label with `ZZZ_tampered`
  changes no verdict, in all three arms. Asserted rather than argued.

So the finding is not "a typechecker cannot refuse candidates here". It refuses
about a third of them and it is right to. The finding is that **the third it
refuses is the third an arity count already refuses**, and the curriculum
contains no further type structure to exploit.

## Why the type system has nothing left to say

The elaboration makes it visible. In `abstraction_ladder`, every one of the 32
declared symbols comes out as:

    action : ?m100      alice : ?m100      apple : ?m100      bob : ?m100
    event  : (?m100 → (?m100 → (?m100 → (?m100 → Prop))))

Every entity collapses into **one** metavariable component. The curriculum's
terms are first-order terms over a single sort with literals attached — `Nat`,
`Str`, `Chr` and `Prop` are rigid, and everything else is one undifferentiated
`Obj`. There is no `α`-vs-`β` distinction for a typechecker to enforce, because
the generator never made one.

What is left, therefore, is exactly: **kind** (`Nat` ≠ `Prop` ≠ `Chr`) and
**arity**. The reason breakdown says so directly — of the candidates `open`
refuses, 0.190 are `mismatch` and 0.137 `saturation`, and saturation *is* the
arity rule wearing a universe constraint ("the type of a value node is not a
`Pi`"). The `closed` arm exists precisely to manufacture the missing rigidity by
defaulting each component to its own base type; it prunes 0.797 and cuts **20%
of gold answers**, which is the pre-registered "worse than dead" row and, given
that abstention on `repair` scores 0.0431 against chance 0.1034, is negative
value rather than neutral.

## Cost: the line is right about affordability and it does not matter

640,662 candidate checks in **2.20 s** of CPU — **291,000 checks/s**. The sweep's
5,785 scored fills at 55 candidates each is ~318,000 checks, so a full
179-lesson sweep would pay about **1.1 s** for the kernel. A candidate check is
one unification against a small type with a rollback trail, not a re-elaboration
(`tests/test_lean_elaborate.py` pins that the elaboration is byte-identical
after every candidate has been checked).

The pre-registration asked for the case where the line is "right and
unaffordable". It is the reverse: **affordable and unnecessary.**

## Coverage, reported as coverage and never as a lift

97.75% of symbols kept a declaration; 99.87% of nodes were typed. The 2.25% are
symbols the elaborator gave up on because two occurrences demanded incompatible
types — `push` used both as a binary predicate and as a leaf argument, which is
a namespace collision the curriculum makes freely and Lean would not.

`type_acc` under this IR is not reported at all, as pre-registered. An
elaborator *derives* the type where the repo *predicts* one, so a near-1.000
would measure that a typechecker was implemented. This is the mistake
`symbolic_ai_parsers` made and retracted (UAS 0.95 for a parser that did no
parsing).

## What would have refuted this, and one thing that nearly did

Stated before the run, in the addendum note:

- the arity floor landing well below the kernel — it landed **above** it;
- the `shifted` control not collapsing — it collapsed;
- the round trip not being the identity — it is the identity on **every graph of
  all 179 lessons**, two seeds, plus an adversarial label alphabet
  (`tests/test_lean_translate.py`);
- gold survival near the matched-random level — it is 0.35 above it.

**The thing that nearly went wrong, and it is the reusable half.** The first
full run reported `declared` at gold survival **0.9151**, comfortably inside the
"worse than dead" row, and I nearly wrote that up as a fact about the
curriculum. It was a fact about one branch: a symbol the elaborator had
*demoted* — seen, but inconsistently, therefore carrying **no information** —
was being treated identically to a symbol that was never declared at all, and
rejected. That branch alone accounted for **221 of the 232** gold answers the
arm lost. Fixing it (no information may not be a rejection) moved the arm to
0.9843 and moved its verdict from "worse than dead" to "build" — which is to
say, the difference between two readings of the pre-registered table was a
five-line branch in `_verdict`, not the data. It is now pinned by
`test_a_symbol_the_elaborator_gave_up_on_is_possible_in_every_mode`.

## The one thing that could reopen the line

The gate measures prune over **all** candidates. It does not measure prune over
the candidates a fitted pointer actually ranks highly, and the pre-registration
deliberately fixed the cheaper question. If the kernel's ~35% of refusals were
concentrated on the candidates stage two would otherwise have *chosen*, it could
matter more than its size suggests — and if they are spread uniformly, it cannot.

Interpolating the `open`→`closed` frontier, a filter sitting exactly at 0.95 gold
survival would prune roughly 0.44, beating the floor by ~0.07. I am not building
it: a filter tuned to sit on its own pre-registered threshold is not a filter
anyone should trust, and 0.07 is still far below the candidate-set change that
moved accuracy by 0.000. Both are parked in `notes/questions/`.

## What is kept

The package stays, registered and tested, because the null is only worth what
its instrument is worth and because `005` (AtomSpace/MeTTa) is the sibling arm of
the same fork:

- a native, total, fuel-bounded kernel with adversarial tests;
- `graph_to_expr` / `expr_to_graph`, the identity on all 179 lessons;
- `symbolic-ai-lean gate`, a diagnostic that is not a sweep and says so;
- a Lean 4 emitter for the outside conformance oracle, **never run** — there is
  no toolchain on this machine and the test that would check it skips, on
  purpose, so that the absence of the check is on the record rather than absent.

**No `lean-006` model is registered and no sweep was run.** The gate exists so
that a model does not get built on the strength of a mechanism that a child
count already covers, and it did its job.
