---
date: 2026-08-14
author: lead
status: provisional
related: [2026-08-13-readout-is-a-knob,
          2026-08-13-a-parser-is-a-parameter-and-the-oracle-is-prefix-restricted,
          2026-08-13-core-owns-the-types-data-stays-vendored,
          2026-08-14-atomspace-metta-ir-preregistration,
          2026-08-14-lean-ir-preregistration]
---

# The third seam: the intermediate representation is a knob, and it is the one shared thing never varied

## The fork

Two seams around the reasoning have already been made parameters, and both paid:

| seam | package | what it bought |
|---|---|---|
| `text -> Graph` | `symbolic_ai_parsers` | `gparse-003`'s six rows differ in one thing, so their spread measures *parsing* rather than comparing models |
| `Graph -> scored prediction` | `symbolic_ai_core/readout.py` | the same fitted `corefer-001` lands on opposite sides of the `repair` floor depending only on what its output is read as |

Both hold the **middle term fixed**. `Graph` — `labels`, `types`, `parent`,
`slot`, `depth`, five parallel arrays in `symbolic_ai_core/data/graph.py` — is
the one representation every model, every parser, every readout, every floor and
every published number in this repo is defined over. It has never been varied,
and nothing here has ever measured what it costs.

That is precisely the shape this repo's most expensive lesson warns about.
`notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md`: the named
shared parts — `structural_fallback`, `type_backoff`, the calibrator, the
tokenizer — **each moved more than the entire model spread**. `Graph` is a shared
substrate of the same kind and larger, and it has had less scrutiny than any of
them.

## What is chosen

**An intermediate representation is a named, registered component**, on the same
footing as a parser and a readout. To be one, a candidate IR must supply three
things and nothing less:

1. **`Graph -> IR`**, so the curriculum's exact, unannotated ground truth
   transfers. This is what makes the whole line affordable: the generator hands
   over the term the text was rendered from, so an IR gets supervised targets for
   free and nothing has to be labelled.
2. **Native operations** — what the layer can do that the flat arrays cannot.
   This is the entire point. An IR that only re-encodes is a rename.
3. **`IR -> Graph`**, so the existing readouts, floors, metrics and the copy
   ceiling still apply and the numbers stay comparable to every published row.

Two candidates are opened as separate lines, because they differ on the axis
that actually matters — **what the representation can refuse**:

| | `005` AtomSpace / MeTTa | `006` Lean |
|---|---|---|
| native operation | pattern match and rewrite | **typecheck** |
| stance on a bad answer | scores it low | **rejects it** |
| holds contradictions | yes, by design | no |
| pre-registration | `notes/decisions/2026-08-14-atomspace-metta-ir-preregistration.md` | `notes/decisions/2026-08-14-lean-ir-preregistration.md` |

Neither replaces `Graph`. Both are registered beside it, exactly as a model
variant is, so one sweep prints the flat-graph row and the IR row against the
same floors and the difference is measured rather than asserted.

## Where the learning stays

Both lines still need the `vsa-003/004` machinery, and that is not a concession —
it is the load-bearing part. An IR gives you a place to *put* symbols and a
calculus over them; it does not tell you **which symbol goes in the hole**. That
is the masked-node task and it is learned.

So each IR needs the two directions the VSA family already has in hypervector
form, now against a richer structure:

- **extract** — the IR's state plus a hole -> a query -> a graded score over
  candidate symbols. `vsa_perm-002`'s permutation channel and `vsa_hks-004`'s
  heat-kernel signature are both *role constructions*, and an IR is a richer
  source of roles than `(ptype, slot, depth, arity)` ever was.
- **re-insert** — a chosen symbol -> a well-formed IR term, which is where `006`
  can refuse and `005` cannot.

## What would refute the design, stated before anything is built

- **The IR rows rank the models the way the flat graph does.** Then the
  representation is not a knob, the seam was already neutral, and the finding is
  a null of the same value as the parser and readout nulls. This is the outcome
  the design has to be able to report; the interesting result is disagreement.
- **The round trip is not the identity.** Then every difference is a translation
  artefact rather than an IR effect, and nothing downstream is attributable.
- **The lift is measured against the old floor.** A richer representation gets a
  free lunch from a floor fitted in a poorer one. Floors are refitted inside the
  IR or no lift is quoted — `notes/lessons/` has this as `rgt`'s +0.587 that was
  really +0.395.

## Three traps this repo has already paid for, and the guards

**The round-trip test must cover, not sample.** `test_encoding_is_lossless`
existed, passed, and missed that the tokenizer was deleting underscores, because
its fixture drew episodes containing none. Both IR round trips are asserted over
**every graph of all 179 lessons**, and on the alphabet of node types rather than
on a fixture — which is what the replacement tokenizer tests already do.

**A metric that is 1.000 by construction is a definition, not a result.**
`symbolic_ai_parsers` reported UAS 0.95 for a parser that did no parsing, because
the tree alignment made every aligned node's head correct by construction. Both
IRs will have a head that becomes trivially correct once the representation
carries it — `006`'s node type is the obvious one, since an elaborator *derives*
a type where this repo *predicts* one. Where that happens it is asserted as a
test and never quoted as a lift.

**No external toolchain in the hot path.** `hyperon` publishes no wheel for this
project's Python and Lean is not installed on this machine; more to the point,
`APPROACH.md`'s whole premise is a CPU cost budget, and a C extension or a
subprocess elaborator inside a 179-lesson sweep would break it. Both lines are
therefore **native in-repo implementations with the real system as an outside
conformance oracle**, run out of band and skipped when absent. That is the
`symbolic_ai_data` pattern (vendored verbatim, byte-identical test) and the WALS
pattern (an oracle nobody here wrote), and both have already worked.

## Rejected alternatives

- **Replace `Graph` with the better IR once one wins.** Rejected: it silently
  redefines every published number carrying a model's name, which this repo has
  done twice and written a naming convention to stop.
- **One IR abstraction with both backends behind it.** Rejected as premature. The
  two differ on whether the representation can refuse an answer, which is not a
  backend detail — it changes what a prediction *is*. Build both concretely,
  extract the common seam afterwards if there turns out to be one.
- **Skip the flat-graph control and compare the two IRs to each other.**
  Rejected: with no shared baseline row the comparison has no floor and reduces
  to whichever was tuned more recently.
