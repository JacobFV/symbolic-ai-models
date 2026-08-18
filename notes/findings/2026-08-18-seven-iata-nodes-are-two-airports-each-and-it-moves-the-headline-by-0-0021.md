---
title: Seven `kg:iata:*` nodes are two airports each — and the blast radius is 0.117% of one task, exactly zero of the other, and +0.0021 on the headline
date: 2026-08-18
status: provisional
tags: [openflights, data-integrity, airport_country, range_limited_routing, guard, blast-radius, circularity]
---

## The defect, and why it is worth an audit rather than a footnote

`notes/findings/2026-08-18-the-corpus-does-contain-a-two-source-property-conflict-four-airports.md`
found, incidentally, that **openflights merges distinct airports that share an
IATA code**. `kg:iata:AMN` carries Gratiot Community Airport's label, ICAO
`KAMN` and Michigan coordinates alongside `city=Kamloops country=Canada` — two
real airports collapsed into one body. That finding named the exposure and
stopped there: *"anything keyed on `kg:iata:*` — `airport_country`,
`range_limited_routing` — is carrying those seven rows with a country that
belongs to a different airport."* Both tasks carry published numbers, so the
open question was whether any of them has to be re-stated.

**It does not.** The numbers below are the reason.

Reproduce: `uv run python -u scripts/openflights_iata_merge_audit.py`.

## 1. The count, from an independent pair of instruments

The prior finding reached 7 through a **cross-source** join (openflights vs
geonames) plus an ICAO-prefix leave-one-out rule. This audit re-derives it from
**openflights alone**, with no second source anywhere, using two instruments
that must both fire:

1. **ICAO-prefix purity.** The first two letters of an ICAO location indicator
   are allocated by region, so the other airports on a prefix are a
   self-declared check. Leave-one-out: at least 4 other airports on the prefix,
   **none** asserting this row's country and **all** asserting one single other
   country.
2. **Coordinate displacement.** The coordinates must be ≥3x closer to the
   prefix country's nearest airport than to the asserted country's.

Neither is usable alone, and the numbers say so:

| rule | fires on | false positives |
|---|---|---|
| bare ICAO leave-one-out + support floor (the prior finding's rule, run corpus-wide) | 24 / 5,995 | **17** — Jersey on `EG*`, Christmas Island on `YP*`, Aruba on `TN*`: dependencies sitting on their administering state's prefix. **71%** |
| coordinate distance alone, at any threshold | — | cannot separate a merge from Easter Island (3,568 km from another Chilean airport, and not a defect) |
| **the conjunction** | **7 / 5,995** | **0**, after one adjudicated decline |

The seven: **AMN, BPE, EMP, LND, OCN, OEL, TZR** — byte-for-byte the same seven
the cross-source join reached. Two instruments sharing no input agreeing
exactly is the corroboration this rests on.

Hand-inspected, all seven plus the decline and the two nearest non-firing rows:

| iata | asserted | ICAO | prefix→ | d(asserted) | d(prefix) | ratio | label / city |
|---|---|---|---|---|---|---|---|
| OCN | AU | KOKB | US | 11,334 km | 12 km | 940.0 | Oceanside Municipal Airport / Fraser Island |
| BPE | MM | ZBDH | CN | 2,420 km | 66 km | 36.4 | Qinhuangdao Beidaihe Airport / Bagan |
| LND | DE | KLND | US | 1,169 km | 35 km | 33.1 | Hunt Field / Lindau |
| TZR | US | LHTA | HU | 1,485 km | 51 km | 29.0 | Taszár Air Base / Columbus |
| EMP | DE | KEMP | US | 1,169 km | 83 km | 14.1 | Emporia Municipal Airport / Kempten |
| OEL | US | UUOR | RU | 1,485 km | 126 km | 11.8 | Oryol Yuzhny Airport / Oakley |
| AMN | CA | KAMN | US | 183 km | 54 km | 3.4 | Gratiot Community Airport / Kamloops |
| *KGD* | *RU* | *UMKK* | *BY* | *578 km* | *267 km* | *2.2* | *Khrabrovo / Kaliningrad — **declined**, a real exclave on a Soviet-era shared prefix* |
| *HLE* | *GB* | *FHSH* | — | — | — | — | *St Helena — instrument 1 declines, prefix carries 1 other* |
| *SBH* | *FR* | *TFFJ* | — | — | — | — | *St-Barthélemy — instrument 1 declines, `TF*` is shared GP/MQ/BL* |

**The margin is thin and is stated rather than tuned away.** The lowest-ratio
merge is AMN at 3.4; the declined row sits at 2.2. Any cut in (2.2, 3.4) gives
this answer. The *ordering* is measured; the *cut* is a judgement, and KGD is
named in the code (`SCREEN_DECLINED_BENIGN`) so a later reader can see it was
adjudicated rather than never noticed.

**The blind spot, stated because a blast radius quoted off a detector with an
unstated blind spot is worthless.** 235 of 5,995 rows (**3.92%**) are
structurally invisible to the screen: 5 carry no 4-character ICAO, 191 sit on a
prefix with fewer than 4 other airports, 39 assert a country with fewer than 4
airports. A merge whose two halves land in the same country is also invisible to
both instruments and to the cross-source join. **7 is a floor on the count, not
a ceiling.**

## 2. Blast radius, as a fraction of each task

| task | instances | touching a merged node | fraction |
|---|---|---|---|
| `airport_country` | 5,995 | **7** | **0.117%** |
| `range_limited_routing` | 37,042 legs / 3,241 nodes | **0** | **0.000%** |

`range_limited_routing` is clean for **two independent reasons**, either of
which alone would settle it:

- **None of the seven carries a route.** All seven are general-aviation fields
  with `out=0 in=0`. `build_network` derives its adjacency from the edge list,
  so none of the seven is a node of the graph at all — 0 of 7 present, 0 legs
  measured from their coordinates.
- **The merge corrupts `city` and `country`; this task reads `lat`, `lon` and
  `flies-to`.** The geometry half of a merged body is internally coherent —
  Gratiot's label, Gratiot's ICAO, Gratiot's Michigan coordinates. Only the
  city/country half belongs to the other airport.

## 3. Touching a node is not changing an answer, and here the two differ by 2x

The repo has been burned by conflating these, so both were measured.

**a. The seven themselves: 7 of 7 scored wrong.** Not "at risk" — wrong, and
necessarily so, because the label comes from one airport and the coordinates
from another. 1-NN predicts the coordinates' country every time:

```
AMN truth=CA pred=US   BPE truth=MM pred=CN   EMP truth=DE pred=US
LND truth=DE pred=US   OCN truth=AU pred=US   OEL truth=US pred=RU
TZR truth=US pred=HU
```

**b. Seven *more* answers change, and they are other airports.** A merged node
is also a *neighbour*. Removing the seven from the reference set flips 7 of the
remaining 5,988 predictions (0.117%) — 6 become right, 0 become wrong, 1 stays
wrong for a different reason. BZK (Bryansk) was predicted US because Oryol next
door claims to be in the United States; CLD, MBS, PEV, RIW, SHP, SOB likewise.

**So the answer-level radius is 14 / 5,995 = 0.234% — double the
node-level 0.117%.** Counting contaminated nodes would have understated the
damage by exactly 2x. That is the distinction, quantified.

**c. What the published numbers become if the seven are cleaned:**

| metric | published | cleaned | delta | quoted tolerance |
|---|---|---|---|---|
| 1-NN over coordinates | 0.9078 | 0.9098 | **+0.0021** | ±0.002 |
| swept grid floor @5° | 0.7888 | 0.7897 | +0.0009 | ±0.002 |
| ground-truth anchor | 1.0000 | 1.0000 | 0.0000 | exact |
| modal floor | 0.2087 | 0.2086 | −0.0001 | ±0.0005 |

The lift moves 0.1190 → 0.1201. **No published number must be re-stated.** The
headline delta sits at the edge of its own quoted tolerance and every
conclusion — beats the swept floor, beats the modal floor by 5.9x less than it
looks, anchor exact, two controls below floor — survives unchanged in sign and
magnitude. The correction, if ever applied, would make the method look *better*,
which is the direction that matters least.

## 4. The guard

`symbolic_ai_adapters/openflights.py`, at the point the bytes become world
state. It **fails loudly and repairs nothing**:

- `MERGED_IATA_NODES` — the seven, with provenance.
- `detect_merged_iata_nodes(rows) -> (detected, eligible)`. Returning
  *eligible* as well as *detected* is load-bearing: a detector reporting an
  empty set because nothing was eligible is otherwise indistinguishable from a
  clean corpus.
- `check_iata_merges` raises `OpenflightsIntegrityError` on **two** conditions:
  a row trips the detector that the manifest does not name (unlooked-at
  contamination), or a manifest row is present *and eligible* and does not trip
  (the manifest has become a lie about the bytes). Restricting the second to
  eligible rows is what makes it correct under a partial load — a guard that
  fires on its own blindness is noise.
- **The seven load unchanged.** The guard refuses an *unrecognised*
  contamination; it does not correct a recognised one. Repairing on load would
  silently redefine every published `airport_country` number, which is the
  failure mode `CLAUDE.md` names twice.

`tests/test_openflights_merged_iata.py`, 11 tests. The one that matters —
`test_an_injected_merge_stops_the_load` — was **run against the pre-guard code
path and fails there** (`DID NOT RAISE OpenflightsIntegrityError`); a guard
whose test passes before the guard exists is not a test.

## 5. The circularity: `airport_country`'s ground truth is one side of the disagreement

Two separate problems, and the first is worse than the brief stated.

**a. The anchor is structurally incapable of catching this.** The task's
ground-truth anchor reads the body's `country=` **name string** and is scored
against the `in-country` **edge**. Measured: 223 distinct name strings map to
223 ISO codes with **zero** collisions. They are the same assertion rendered
twice. So the anchor scores an exact 1.0 on the contaminated task and an exact
1.0 on the cleaned one — it reads the merged-in half and is judged against the
merged-in half. The check the task ships as its integrity guarantee is blind to
the defect by construction. That is why this went unnoticed until a *second
source* was joined in.

**b. The labels are one side of a two-source disagreement.** Taken from the
prior finding, not re-derived: geonames contradicts openflights on **29** of
5,882 jointly-placed airports. All 29 are `airport_country` instances —
**0.484%** of the task. Four (EUN, SMW, VIL, PRN — Western Sahara and Kosovo)
are disagreements **no source is entitled to settle**, 0.067% of the task.

**Is the number still quotable? Yes, with its scope named.** 0.9078 is
*agreement with openflights' worldview*, not accuracy against the world, and
the method's neighbours are openflights rows too, so the circularity is
self-consistent rather than inflating: 1-NN reproduces openflights' own answer
on only 1 of the 4 unsettleable cases, so the task is penalising the model on
them, not rewarding it for sharing a bias. At 0.484% the effect cannot move a
number quoted to ±0.002 by more than two tolerances even if every one flipped.
**No re-statement required; the task's docstring should say "openflights'
`in-country` edge" where it currently says "ground truth", which it already
does.**

## What would refute this

- **A merge whose halves share a country.** Invisible to both instruments here
  *and* to the cross-source join, which only sees country disagreements. The
  count 7 is a floor.
- **The fitted cut.** 3.0 was chosen after seeing AMN at 3.4 and KGD at 2.2.
  A cut at 2.0 admits Kaliningrad and the count becomes 8.
- **The 3.92% blind spot.** A merge on a thin ICAO prefix would be missed, and
  191 rows sit on one.
- **`range_limited_routing` if openflights ever gains routes for a merged
  code.** The zero is a property of this snapshot's edge list, not a theorem —
  which is exactly what the guard now watches.

## What this changes

The prior finding's incidental half is confirmed by an independent instrument
and priced. The headline is that **the blast radius question had two different
right answers for two tasks over the same nodes** — 0.234% of answers for
`airport_country`, exactly zero for `range_limited_routing` — and the
difference is not about how contaminated the data is but about **which fields
each task reads**. A contamination audit that stops at "N nodes are dirty"
cannot produce either number.

The second-order effect is the one to carry forward: the merged nodes cost
twice as many answers as they occupy instances, because a bad row in a
neighbourhood method is also a bad *neighbour*. Any future contamination audit
over a kNN-shaped task should expect roughly 2x.
