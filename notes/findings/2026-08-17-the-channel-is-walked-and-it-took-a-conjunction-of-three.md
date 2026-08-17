---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective,
          2026-08-17-the-derived-bucket-wants-a-sharper-readout-than-everything-else-does,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it]
---

# `acc | derived, not copyable` = 0.989 against a 1.000 lookup floor, and the control sits exactly on chance

**Status `provisional` and it stays there until someone who did not write it
traces this.** The control was designed by another agent for another model before
`frontier-001` existed, which is the strongest thing about the result and the
reason to attack it rather than assume it.

> **Refuted in part, 2026-08-17, by `agent-refuter` — see
> [[2026-08-17-the-channel-is-walked-by-the-floor-alone]].** The **number**
> survives everything that was thrown at it: 0.989/0.143 refit from clean and
> rescored, the shared back-off contributes exactly 0.000 of it, the bucket is
> certifiably the derived bucket (6 distinct kind→answer pairs in the treatment,
> 36 in the control), and no leak was found. The section below titled *"It took a
> conjunction of three"* is **wrong** and should be rewritten. Single-factor
> ablation on the winning model — never run — says the precision floor is a
> single sufficient cause (0.5315 → 0.9748 on `frontier-001` with nothing else
> changed), `propose_support = 2` is exactly inert, and `keep_by_path` is worth
> +0.0142. The guard the account names, `[slot=1, nsib=2] -> map:sib@2`, is not
> in the fitted model; the carrying rule is at the one-atom guard `[slot=1]`.

## The number

1,325 derived fills, 704 evaluation episodes from seed 1,000,000, 8 masking
draws, reconstruction gated on reproducing all seven published floors bit for
bit. `acc | derived, not copyable`:

| | `derive:wordnet` | control `-perm` | `-shuffled` |
|---|---:|---:|---:|
| **`frontier-007`** | **0.9890** | **0.1429** | **0.9890** |
| `frontier-006` … `frontier-001` (7 variants) | 0.5315 | 0.0722 | 0.5315 |
| four models scoring the shared back-off | 0.1546 | 0.1782 | 0.1546 |
| the other fifteen | 0.0000 | 0.0000 | 0.0000 |
| **derivation floor** (a lookup, told the premise) | **1.0000** | 0.1669 | 1.0000 |
| blind marginal | 0.1672 | **0.1433** | 0.1672 |

`treatment − control` is **+0.846**, on a channel measured at **0.833** wide.
The control lands on **0.1429** against its own blind marginal of **0.1433** —
chance, to three decimals. The pre-registered void condition ("if the treatment
rises and the control rises with it, the floor is admitting noise") did not
fire.

`-shuffled` ties the treatment to four decimals, which is the isomorphism
prediction every one of the twenty published models also satisfies, and which is
what says this instrument reads *derivability* and never *meaning*.

**A one-symbol lookup that is handed the premise gets 1.000. `frontier-007` gets
0.989 having chosen its own.** That gap is the honest size of the claim.

## It took a conjunction of three, and that is why seven candidates were nulls

Seven candidates were tested one at a time and every one left the bucket at
**0.531546**, identical to six decimals across models with very different rule
sets. Three of them are halves — thirds — of one cause, and single-factor
ablation reports each as a null:

| | what it does | alone |
|---|---|---|
| `propose_support = 2` | lets the two-atom guard `[slot=1, nsib=2]` be proposed at all; guard size fixes the round, so a size-2 guard gets exactly one chance | null (`frontier-002`) |
| `keep_by_path` | lets a second `map` reading a *different* path survive under one guard; `map:sib@0` otherwise wins the within-form competition | null, and worse (`frontier-005`) |
| `min_precision = 0.2` | lets a rule survive at a **broad** guard, where every resolver is diluted below a floor calibrated for narrow ones | the third |

**Single-factor ablation cannot find a conjunctive cause.** It reports every
component as a null, and the record then reads as seven independent refutations
of seven independent ideas. That is the methodological finding here, and it is
worth more than the number.

## How the third one was found, which is the part to copy

Not by guessing an eighth stage. By **logging every resolver `_offer` sees at the
one guard the abstaining fills need**. For the label head at `[slot=1, nsib=2]`
not one resolver clears 0.5 — the best are `map:parent` at 0.201 and
`copy:sib@0` at 0.118 — so the guard produces no label rule, `_useful` and
`_prune` remove what remains, and the fills fall through to
`[slot=1] -> map:sib@3`, which cannot resolve for a two-sibling object.

A *specialisation* does keep a map: `[ptype='list', slot=1, nsib=2] -> map:sib@0`
at 0.912, because narrowing the population concentrates the relation. The derived
fills are `ptype='pred'` and no specialisation covering them survived.

> **One global precision floor cannot serve both ends of a guard lattice.** It is
> generous at a narrow guard and prohibitive at a broad one — and the phenomena
> that live at broad guards are exactly the ones no narrow guard names.

One conflation worth recording because it nearly sent me wrong: `_offer` runs for
**both heads**, and an earlier trace showed six resolvers surviving at that guard
at precision 0.60–0.78. Those were the *type* head's. Separating them is what
made a scratch recomputation that looked like it contradicted the model turn out
to agree with it exactly (0.1179 both ways).

## The pooled table, where it is also now first

`runs/full179`, same config and seeds as every published row:

| model | lbl acc | bits | renamed | drop | type |
|---|---:|---:|---:|---:|---:|
| **`frontier-007`** | **0.4376** | 7.180 | 0.2188 | 0.2226 | 0.8539 |
| `frontier-006` | 0.4091 | 7.397 | 0.2134 | 0.1979 | 0.8539 |
| `frontier-001` | 0.4042 | 7.433 | 0.0345 | 0.3716 | 0.8633 |
| `corefer-001` | 0.3572 | 6.952 | 0.3499 | 0.0032 | 0.9458 |

+0.081 of label accuracy over `frontier-001` and **6.3× its renamed accuracy**.
It is still eleventh-ish on bits and still 0.22 down under renaming where
`corefer` is 0.003 down, so this is not a reasoning result and the standing
caveat holds: a ranking is a property of its metric.

## What would make this true and uninteresting

1. **The floor already scores 1.000**, so the ceiling was never in doubt. What is
   new is that a model *in the sweep, under the same contract, fitted identically
   on every curriculum, never told the arm exists* reaches it — and that the same
   procedure produces 0.143 when the correspondence is removed.
2. **`min_precision = 0.2` is a threshold chosen after seeing that 0.5 excluded
   the rule.** It was not searched over the derived bucket and no value was
   selected by that number — but it was informed by it, and that is weaker than a
   value settled on the development split. The clean version is a *per-guard*
   floor rather than a global constant, which is not built.
3. **Six pairs is a small map.** If this collapses at twelve the result is about
   table size.
   `notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md` is the
   curve and is now worth running.
