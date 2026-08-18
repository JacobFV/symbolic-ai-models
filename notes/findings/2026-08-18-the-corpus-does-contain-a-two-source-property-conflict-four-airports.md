---
title: The corpus does contain a genuine two-source property conflict — four airports, and 21 of the 29 disagreements are not one
date: 2026-08-18
status: provisional
tags: [federation, conflict, real-data, openflights, geonames, join, scouting]
---

## The question and what was expected

`HANDOVER.md` §4 records it as *believed, not measured*: three findings in a row
have said this corpus holds **no genuine two-source property conflict** — no
property where two independently authored sources both assert a value for the
same real-world subject and the values differ. The 251 filed-vs-filed and 4,992
closure-vs-filed conflicts are all *within* GLEIF. The named candidate was
airports: `openflights` and `geonames` may both carry a country for the same
place.

Written down before the numbers landed: expect a few thousand joined subjects,
agreement above 0.98, disagreements dominated by dependency-vs-sovereign
granularity, and genuine survivors in the 0–20 range concentrated in Western
Sahara, Kosovo, Taiwan and Crimea. Whether *any* survive was the unknown.

Reproduce: `uv run python -u scripts/two_source_country_conflict.py --all`.
This is a **scouting arm** — no permutation control, no floor audit, no
independent refuter. It is honest and reproducible, not bulletproof.

## The join, and every weakness it has

**Subject key: the IATA code.** openflights names airports `kg:iata:XXX`
directly. geonames reaches the same code through `code_bridges`
(`kg:geonames:N` ``same-as`` `kg:iata:XXX`). No coordinate tolerance, no fuzzy
name matching and no string normalisation anywhere in the join itself.

**Weakness 1 — IATA is not a key on the geonames side.** 9,086 of the 11,403
bridged codes reach more than one geonames record, because the code names both
the airport and the settlement it serves. Joining on the code alone compares
openflights' *airport* with geonames' *city*. Handled by restricting the
geonames side to a single record with an aerodrome feature code (`S/AIR*`);
74 codes reach two aerodromes and are dropped rather than guessed at.

**Weakness 2 — the bridge itself is sometimes wrong.** Measured, not assumed,
against two keys the join never used: **ICAO agrees on 0.9763** of the 5,828
pairs where both sides carry one, and **airport names match on 0.9113**. So
roughly 2.4% of these joins land on a different airport. That is the number that
could have manufactured this whole finding, and it is why the headline is quoted
on the confirmed tier below.

**Weakness 3 — the name filter is blunt.** It rejects 8.9% of the pairs that
*agree* on country, so it is a disqualifier of last resort, used only where ICAO
is absent. It disqualified exactly 2 of the 29 disagreements, and both were
confirmed by hand (Fontaine/Belfort, France vs Bokeo International, Laos;
Barysiai, Lithuania vs Beidahuang General, China).

**What the comparison does not need.** Both sources state the country as an ISO
3166-1 alpha-2 code — openflights via its `in-country` edge to
`kg:iso:country:XX`, geonames in the place body as `country=XX`. There is no
"US" vs "United States" normalisation problem available to explain a
disagreement away with. openflights *also* carries a country name string; it was
used only to audit openflights against itself, never in the comparison.

## The numbers

| | |
|---|---|
| openflights airports | 6,072 |
| IATA codes bridged by geonames | 11,403 |
| **subjects where both sources assert a country** | **5,882** |
| agree | 5,853 |
| **disagree** | **29** (rate 0.00493) |
| confirmed tier (ICAO agrees **and** names match) | 5,209 subjects, 25 disagree (0.00480) |

Country is the **only** property both sources assert. openflights carries
lat/lon, city, ICAO; geonames' place body carries only feature code, country and
population. There is no second property to cross-check, and no timezone or
elevation on the geonames side of this snapshot.

## What the 29 disagreements are

Rules fire in order; the first two remove pairs that are not a disagreement at
all, the next two remove pairs that are two renderings of one fact.

| n | category | what it is |
|---|---|---|
| 2 | join error: ICAO codes differ | ACF, HGI — different airports |
| 2 | join error: different airport names | BOR, HLJ — different airports |
| 7 | **openflights merged two airports sharing an IATA code** | AMN, BPE, EMP, LND, OCN, OEL, TZR |
| 5 | retired ISO code (vocabulary vintage) | BON, CUR, EUX, SAB, SXM — `AN` vs `BQ`/`CW`/`SX` |
| 5 | dependency vs sovereign (granularity) | HLE, LYR, MHQ, SBH, SFG |
| 3 | successor state (one source stale) | MAK, RBX, WUU — `SD` vs `SS` |
| 4 | **contested sovereignty** | EUN, SMW, VIL (`EH`/`MA`), PRN (`RS`/`XK`) |
| 1 | unexplained | AKT (`CY`/`GB`) |

**The category that nearly produced a false finding.** `kg:iata:AMN` carries the
label, ICAO (`KAMN`) and coordinates (43.322, -84.688 — Michigan) of Gratiot
Community Airport, and `city=Kamloops country=Canada`. openflights has merged
two airports that shared an IATA code, taking name/ICAO/coordinates from one and
city/country from the other. It is not asserting a country for the subject it
named, so a disagreement there is not a two-source conflict — it is one source
having merged two subjects. Seven of the 29 are this, and on the first pass all
seven read as candidate conflicts.

Detected with no external authority, from openflights alone: an ICAO 2-letter
prefix is regional, so an airport whose asserted country is asserted by no
**other** airport on its own prefix is one openflights contradicts itself about.
Leave-one-out, and the prefix needs 4 airports before the rule may fire. Those
two guards are what keep it off Western Sahara (three `GM*` airports vouching
for each other against Morocco's own prefix) and off Kosovo (`BK*`, one
airport). The rule fires on **0.27%** of the pairs that agree, which is its
measured false-positive rate.

## The verdict

**This corpus does contain a genuine two-source property conflict.** Four
airports, on the confirmed tier, where openflights and geonames assert different
sovereigns for the same aerodrome, agree on its ICAO code and its name, and
neither source is entitled to settle it:

- **EUN** Hassan I Airport, El Aaiún — `EH` vs `MA`
- **SMW** Smara Airport — `EH` vs `MA`
- **VIL** Dakhla Airport — `EH` vs `MA`
- **PRN** Priština International Airport — `RS` vs `XK`

Western Sahara and Kosovo. Both are live sovereignty disputes; both sources are
stating a position, not making an error; and the ICAO prefixes (`GM*` Moroccan,
`BK*` Kosovan) show the third-party allocator taking a side too.

**Broadest defensible count: 8**, adding the three Sudan/South Sudan airports
(MAK, RBX, WUU — openflights is stale by the 2011 secession) and AKT, RAF
Akrotiri, where openflights says Cyprus and geonames says United Kingdom. AKT is
left in the unexplained bucket deliberately rather than being added to the
contested table after seeing it: a British Sovereign Base Area is territory on
the island of Cyprus under UK sovereignty, so both answers are defensible and it
is arguably the cleanest conflict of the lot. It is one airport either way.

**21 of the 29 are not a conflict**: 4 bad joins, 7 openflights self-contradictions,
5 retired ISO codes, 5 granularity choices.

## What would refute this

- **A better join.** The strongest attack is that EUN/SMW/VIL/PRN are join
  errors. They are not: ICAO agrees on all four, names agree on all four, and
  the coordinates put them in the disputed territory. Someone should still check
  the geonames records by hand.
- **A coordinate authority.** This snapshot's geonames `place_nodes` body carries
  no lat/lon, so there is no independent way to place the airport on the sphere
  from the geonames side. Every claim about *where* an airport is here comes
  from openflights.
- **The taxonomy.** `DEPENDENCY_OF`, `RETIRED` and `CONTESTED` are hand tables in
  the script. They were written before the disagreements were listed, but they
  are a judgement about what counts as one fact rendered twice, and someone who
  drew the line differently would get 4, 8 or 13.

## What this changes

The three findings that said the corpus has no two-source property conflict were
right about *GLEIF*, and the generalisation was too strong. There are now four
subjects on which `fuse` can be asked to hold a disagreement that no source is
entitled to settle and where the two claimants are genuinely independent
organisations — which is a different and stronger case than 251 filings by the
same registry. It is a **small** case: four subjects, one property, and an
existing `airport_country` task whose ground truth is openflights' own
`in-country` edge, i.e. one side of the very disagreement. Whether four subjects
is enough to price a capability against is the open question; the number for
comparison is that the GLEIF arm has 4,992.

The incidental finding is worth as much: **openflights' airport nodes merge
distinct airports that share an IATA code, in at least 7 of 5,882 cases.**
Anything in this repo keyed on `kg:iata:*` — `airport_country`,
`range_limited_routing` — is carrying those seven rows with a country that
belongs to a different airport.
