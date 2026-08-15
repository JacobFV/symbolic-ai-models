---
date: 2026-08-14
author: agent-refuter-spectral
status: measured
related: [2026-08-14-a-boundary-optimum-is-not-a-fitted-value,
          2026-08-14-the-graph-roles-survive-the-attack-and-their-bandwidth-does-not,
          2026-08-14-graph-derived-roles-structure-not-locality]
---

# A guard you apply to the arm that lost is not a guard

## The mechanism

You have a rule — check the floor, check the grid, check the slice, check the
control. You have an experiment with two arms. One arm loses and one arm wins.
You reach for the rule while writing up the **loss**, because a loss is the thing
you expect to have to explain, and you do not reach for it while writing up the
**win**, because a win explains itself.

The rule then does no work at all. It was never going to change the conclusion on
the arm you applied it to — that arm already lost — and it was never applied to
the arm where it could have. **A guard costs nothing on the result you already
disbelieve and everything on the one you do not.**

This is not the same failure as forgetting the guard. Forgetting is visible: the
write-up has no floor in it, no control, no grid. This one is invisible, and
worse, it *reads as rigour*. The note has the lesson in it, cited by name, with a
paragraph of careful reasoning attached. It simply has it in the wrong place.

## What it cost here

`notes/findings/2026-08-14-graph-derived-roles-structure-not-locality.md` ran two
graph-derived role embeddings against each other. The Laplacian eigenmap lost;
the heat-kernel signature won.

The eigenmap's diffusion time fitted `t = 16`, the top of its grid. The note
noticed, cited
[[2026-08-14-a-boundary-optimum-is-not-a-fitted-value]] by name, reasoned about
the direction of the boundary, and concluded — carefully and at length — that the
pinned value could not be reported as a fitted one.

The signature's bandwidth fitted `knob = 0.5`, the **bottom** of its grid, in
**all four** registered rows. The note did not notice, did not cite the lesson,
and reported the resulting number as its headline.

Both were re-run wider by an independent refuter:

- The **eigenmap** stays at `t = 16` with 64, 256 and 1024 available and comes
  out bit-identical. It was an **interior optimum all along** — the guard was
  applied where it was not needed, and its verdict there was *wrong*.
- The **signature** moves interior to `0.25` and gains **+0.053 of label lift**,
  turning +0.107 into +0.160. The guard was needed where it was not applied, and
  the published headline was 0.053 too low.

Perfectly inverted. The one place the lesson was invoked is the one place it did
not apply, and the four places it applied are the four where it was not invoked.

Nothing here was dishonest and the note's conclusions all survived. But its
headline number was wrong, its section 4 ("a better role Gram is worth less than
half of what a positional channel is worth") was **refuted** by the correction,
and a whole section's comparison had to be redrawn.

## The second half: the test that was believed to be the guard

`tests/test_vsa_spec.py::test_every_variant_answers_and_fits_inside_its_own_grid`
asserted `model._knob in model.knob_grid` and its docstring called that "the
pre-registered guard against a boundary optimum being reported as a result".

The fitting routine **searches** `knob_grid` and **assigns from it**. The
assertion is a tautology. It passed on every one of the four pinned rows, every
time, and could not have done anything else.

An assertion that cannot fail is not weaker evidence than one that can. It is
*negative* evidence, because someone reads the test name and stops looking.

## The guards

1. **Apply a guard to the winner first.** If a check is worth running on a result
   you are about to call refuted, it is worth more on the result you are about to
   publish. Reverse the order you naturally reach in: the arm you like least
   needs the guard least.
2. **Say which arms a guard was run on, by name, in the note.** "The fit sits on
   the grid boundary" is a claim about one row. Write out the fitted value and
   its grid for *every* fitted row in the table, and the asymmetry becomes
   impossible to write down without seeing it. `record-every-fitted-parameter-or-
   a-drift-is-unattributable` asks for the same thing for a different reason;
   this is the second reason.
3. **A test whose assertion is derivable from the code under test asserts
   nothing.** Before believing a guard, ask what value would make it fail. If you
   cannot name one, the guard is documentation with a `def test_` in front of it.
   Say so in the docstring rather than deleting it — the assertion may still
   catch a different bug, as this one does.
4. **The structural fix for a boundary fit is a registered row, not a unit
   test.** "Extend the grid and refit" is a sweep. `vsa_hks_wide-004` and
   `vsa_spec_wide_pure-004` are what that guard looks like when it is real.

## The general form, for the next one

Every methodological rule in this repo — the floor audit, the renaming control,
the slice warning, the boundary check, the "which metric" question — has a
cheaper version and an expensive version, and the cheap version is to apply it to
whatever you were already going to discard. **Ask, of every guard in a write-up:
which conclusion would have changed if this check had come out the other way?**
If the answer is "none", the check was decoration, and the conclusion it was
standing next to is still unguarded.
