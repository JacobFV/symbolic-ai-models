# `ontology/` — the controlled vocabularies, in one place

Every enumerated vocabulary this repo's data layer uses is defined **here and
nowhere else**, and everything that needs one — Python literals, JSON Schema
`enum` fragments, a TypeScript union in a sibling project — is generated from it.

The reason is a failure that has already happened in a sibling project: a
TypeScript `vocab.ts` hand-copied its enums from the JSON schemas, drifted, and
ended up with ten values where the schema had twelve. Nobody noticed, because
two allegedly-identical vocabularies fail silently — the consumer with the short
list simply never matches the two missing cases, which reads exactly like those
cases never occurring.

## Authoring format vs canonical format

```
  vocab.yaml / *.yaml          AUTHORITATIVE, hand-written, comments welcome
        |  parse (YAML 1.2, safe_load)
        v
  plain JSON-compatible object
        |  validate against ontology/schema/*.schema.json
        v
  canonical JSON  (sorted keys, no whitespace, UTF-8, NaN rejected)
        |
        v
  sha256  -> the identity
```

YAML is what a person edits. **Canonical JSON is what is hashed**, so a comment,
a reordered key or a reflowed string cannot change an identity. `generated/` is
the compiled form and is never edited by hand.

## Files

| file | holds |
|---|---|
| `vocab.yaml` | every enumerated vocabulary: access classes, lifecycles, evidence roles, alignment relations, licence redistribution terms |
| `schema/source.schema.json` | what a source card must contain |
| `schema/snapshot.schema.json` | what a snapshot manifest must contain |
| `schema/artifact.schema.json` | what an artifact manifest must contain |
