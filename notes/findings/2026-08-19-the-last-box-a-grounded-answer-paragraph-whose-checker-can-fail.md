---
title: The last box of the pipeline, built — a grounded answer paragraph whose checker can fail, and which caught two false assertions my first renderer made
date: 2026-08-19
author: lead
status: provisional
tags: [renderer, pipeline, grounding, text-to-world]
---

## What was missing

The programme's pipeline is

```
text -> world IR -> multi-kernel flow -> structured output + text
```

and the last box was unbuilt. Two domains had surfaces, readers and kernels; none
had a paragraph.

## The design commitment

A renderer is only worth having if its output is **checkable**:

> Every factual assertion in the paragraph carries a citation to a claim in the
> world or a named kernel output, and an unsupported assertion is detectable
> mechanically.

Two consequences, and they are the point rather than niceties.

**The structured answer stays canonical.** `Answer.structured` is exactly what
the flow returned; the paragraph is strictly downstream. So generation quality
cannot contaminate reasoning evaluation — a renderer that writes badly costs the
task score nothing, and one that writes *falsely* is caught by `ungrounded()`
rather than by a reader's impression of the prose. A test pins this: a renderer
emitting the empty string changes no structured answer and is trivially grounded.

**The negative answer is the hard one.** "No vehicle can make the delivery" is
easy to assert and hard to justify. `load_report.per_vehicle` carries `edges`,
`limits`, `feasible` and `outcome` for *every* vehicle including the failures, so
the refusal can be explained rather than announced.

## It works

40/40 cases fully grounded, both polarities explained.

```
One vehicle can make the delivery: truck_0. The requirement is 1400 kg into
region_3. truck_0 runs region_0 to region_5 to region_4 to region_3 and clears
the tightest posted limit on it, 4500 kg. truck_1 cannot: on region_0 to
region_5 to region_4 to region_3 the binding limit is 4500 kg, and the solver
returned proved_impossible. Some facts remain unresolved (15), so this answer is
conditional on them.
```

```
No vehicle can make the delivery. The requirement is 900 kg into region_3. No
route reaches it at all: the network is cut by flooding in region_2 and
region_4. Some facts remain unresolved (5), so this answer is conditional on
them.
```

## The checker caught two false assertions I wrote

**A false route *ordering*.** The flow reports a route as an unordered **set** of
edges. My first renderer printed the endpoints in list order and produced
*"truck_0 runs region_0 to region_3 to region_4 to region_5"* for a route that
actually runs `region_0 → region_5 → region_4 → region_3`.

**Every token in that sentence is grounded** — they are all real regions — so
token-level grounding passed a false ordering. That is a real limitation of
naive groundedness and it is why `ungrounded()` now also checks **adjacency**:
every consecutive pair stated as a route must be an edge of some reported route.
A test forges a chain of real regions that is not a walk and requires it to be
caught.

**A verdict with no reason.** When the demand site is unreachable, no vehicle has
any route, `per_vehicle` is empty, and the paragraph fell silent — asserting
*"No vehicle can make the delivery"* and stopping. It now names the cut, cited to
the `flooded` claims. Found by a test requiring that a refusal explain itself.

## The tests that matter are the ones where the checker fails

A groundedness metric that cannot detect an invented fact measures nothing, so
three tests exist to make it fail: an invented quantity (`9999 kg`), an invented
entity (`truck_77`), and the false ordering above. All three are caught.

## TIGHTENED, 2026-08-19: the paragraph cannot contradict the decision

The gap this note named — *"a real number asserted about the wrong entity would
pass"* — has a sharper form than role bindings. **Token grounding and adjacency
both pass a sentence that asserts the opposite of the structured answer**, using
only real tokens on a real route: *"truck_1 runs region_0 to region_5 to
region_3 and clears it"* when `truck_1` is not in the decision.

That matters because the whole separation between reasoning and generation is
that the structured answer is canonical and the paragraph is downstream. **The
separation is worth nothing if the paragraph can disagree with the decision and
nothing notices.**

`ungrounded()` now checks polarity against the structured answer: every
`<vehicle> runs` / `<vehicle> cannot` must agree with whether that vehicle is in
it. Three tests make the check fail — claiming a refused vehicle runs, denying an
able one, and confirming an honest paragraph is not flagged.

**The renderer passes unchanged, 40/40**, so the milestone's `grounded 1.000`
column was not overstated. What changed is that the checker can now see a class
of falsehood it could not.

## What would refute it

- **Grounding is token-and-adjacency, not semantic.** A sentence asserting a real
  number about the wrong entity — *"truck_1 clears 4500 kg"* when it does not —
  would pass, because both tokens are real and no route claim is made. Extending
  the check to role-level bindings is the obvious next tightening, and it is the
  same shape of gap that the ordering bug was.
- **Templates, not generation.** This is a deterministic renderer. Its value is
  that it establishes the checkable contract; a learned renderer would be scored
  by the same `ungrounded()` and that is the point of building the checker first.
- **One domain.** Solvency has a surface and a reader and no renderer.

## Reproduce

```bash
uv run pytest tests/test_flood_render.py
```
