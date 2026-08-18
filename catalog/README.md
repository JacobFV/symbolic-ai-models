# `catalog/` — what each source **is**

One YAML file per source, hand-authored, authoritative. A source card answers
*what is this resource, who publishes it, under what terms, what streams does it
emit* — and answers **nothing** about what bytes this machine happens to hold.

That separation is the point, and it is the refactor that pays for itself
fastest. `openalex` is not intrinsically "held": *this checkout* holds a
particular snapshot of it, and a second machine that has none of the bytes
disagrees with the snapshot manifest's `locations` list while agreeing
completely with the card. Putting `held_inventory:` on a source card makes the
card a claim about a disk, and a claim about a disk is wrong on every other
machine.

```
catalog/sources/<id>.yaml       what the source IS          <- here
manifests/snapshots/<src>/…     what bytes we got, and when
manifests/artifacts/…           what we manufactured from them
```

## `status` was four variables wearing one name

An earlier design in a sibling project used a single `status` enum holding
`repo-held`, `p0`, `restricted`, `ref`, `watch`. Those are not alternatives —
`p0` and `restricted` are simultaneously true of plenty of sources — so the enum
forced false exclusivities and then quietly lost whichever fact lost the fight.
Here they are separate fields, and local possession is not a field at all:

| field | question |
|---|---|
| `access.class` | how may it be reached — `public`, `registration`, `agreement`, `commercial`, `internal`, `unresolved` |
| `license.redistribution` | may the bytes be passed on |
| `lifecycle` | is it still published and still updated |
| `priority` | how much do we want it |
| *(snapshot `locations`)* | **is it on this disk** — never a source field |

## `unresolved` is a real value, not a to-do

Several cards here say `attribution_confidence: hypothesis` and
`license.redistribution: unresolved`. That is honest and it is load-bearing:
`unresolved` sorts as *more restrictive than anything known* in
`symbolic_ai_core/source/license.py`, so one unresolved parent makes a derived
artifact's closure unresolved. The alternative — defaulting an unknown licence
to permitted — produces a closure that is wrong in the direction that gets
something published it should not have been.

The concrete case: seven staged directories (`appcite`, `cite`, `cpc`,
`inventor`, `assignee`, `patents`, `wipo`) carry `kg:patent:` namespaces and
PatentsView's published table shapes, but the pull recorded no upstream release.
The card is `patentsview`, `attribution_confidence: hypothesis`, licence
unresolved. If someone establishes the attribution, the licence becomes CC-BY-4.0
and every downstream closure loosens automatically. Until then it does not.

## Streams have one id, used everywhere

A stream id is declared once on the source card and then used unchanged by the
snapshot inventory, by any view over it and by any run that consumes it. The
alternative — stream names spread across a modality list, an evidence binding
and an inventory — produces near-synonyms (`eeg` and `eeg_64ch` naming one
thing) that nothing downstream can reconcile.

## Editing

Add a source: add `catalog/sources/<id>.yaml`, filename matching the `id`.
Then `uv run python -c "from symbolic_ai_core.source.build import write_catalog;
write_catalog()"` to refresh `generated/catalog.json`.
`tests/test_source_catalog.py` validates every card against
`ontology/schema/source.schema.json` and every enum against
`ontology/vocab.yaml`.
