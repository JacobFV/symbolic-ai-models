---
date: 2026-08-13
author: lead
status: open
---
`template-002` keeps 0.60 of its English label F1 in Chinese against
`template-001`'s 0.16, after `layout_features` was found to be measuring
tokenisation rather than layout. But shape features could still be a *rendering
fingerprint* rather than grammar.

Cheaply distinguishable: perturb the rendering (bullets to numbers, `;` to
newline) and re-measure. Survives the perturbation means grammar; collapses means
fingerprint. Decides whether the cross-language test measures what we want.
