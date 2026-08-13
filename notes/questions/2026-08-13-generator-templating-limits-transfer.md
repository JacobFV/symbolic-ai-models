---
date: 2026-08-13
author: lead
status: open
related: [2026-08-13-compositional-parser]
---
The curriculum carries 0.54 bits of long-range ORDER structure at d=128 where
real English prose has ~0 beyond d~16, because each lesson renders one rigid
template over one symbol pool. That is a property of the generator, not of
language, so any method that wins by exploiting long-range positional regularity
flatters itself here.

Once `symbolic_ai_data` lands we own the generator and can add a render mode that
varies surface realisation per episode. **It must be a new lesson variant
registered beside the existing one** -- editing generation in place invalidates
every published row at once, which is the model-edited-in-place failure with a
much larger blast radius.
