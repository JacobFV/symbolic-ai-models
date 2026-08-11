# symbolic ai language curriculum

> working curriculum for training a symbolic agent to acquire language, reasoning, abstraction, and eventually the ability to construct and revise its own symbolic machinery.

## research thesis

this curriculum treats language learning as a special case of learning to operate over arbitrary symbol systems embedded in environments. the target is not a fixed parser, a fixed ontology, or even a fixed reasoning procedure. the target is an agent that can acquire symbols, infer their semantics, compose them, use them to act, invent new abstractions, and eventually modify the representational and reasoning substrate through which it learns.

natural-language modeling is therefore one environment family among many. next-token prediction can be represented as an environment with a prefix observation, a token action, and a log-likelihood-style reward, but it should not define the ontology of the entire system.

### relation to recursive language models and prime agent

prime intellect's prime agent is useful evidence for the broader architectural direction. prime agent combines a recursive language model (RLM) interface with a continual harness. the RLM treats context as an external variable that the model can inspect and recursively operate over; the continual harness exposes prompts, sub-agents, skills, and memory as state that can be created, read, updated, and deleted from the agent's own trajectory. prime intellect reports 95.5% RHAE Best@1 on ARC-AGI-3 with opus 5 in prime agent and completion of all 183/183 levels at Best@3. importantly, they also state that no model has yet been trained around prime agent itself and argue that model-harness co-learning should unlock additional capability.

our proposed symbolic analogue is stronger than merely implementing an RLM with symbols. the symbolic agent should eventually be able to operate over and revise:

- lexical systems;
- parsers and grammars;
- ontologies and type systems;
- memories and indexes;
- symbolic programs and reusable skills;
- proof procedures and search strategies;
- sub-reasoners and specialized agents;
- representations themselves;
- the composition graph connecting those modules.

thus the curriculum has two increasingly interleaved levels:

```text
object-level curriculum
    learn facts, rules, meanings, programs, plans, and theories
    inside a currently available representation

meta-level curriculum
    learn which representations, languages, abstractions, tools,
    memories, procedures, and reasoning architectures should exist
```

prime agent demonstrates the value of turning what would normally be fixed scaffolding into an action space. this curriculum asks what happens when the same move is made at the symbolic-representation level.

references:

- prime intellect, "prime agent: a self-improving rlm agent": https://www.primeintellect.ai/blog/prime-agent
- zhang, kraska, khattab, "recursive language models": https://arxiv.org/abs/2512.24601
- karten et al., "continual harness: online adaptation for self-improving foundation agents": https://arxiv.org/abs/2605.09998
- arc-agi-3: https://arcprize.org/arc-agi/3

## standardized environment contract

every environment should expose approximately the same interaction contract so that curricula differ in semantics rather than integration plumbing.

```text
reset() -> observation
step(action) -> observation, reward, terminated, info

observation:
    symbols
    | symbol_graph
    | event_stream
    | structured_state
    | optional raw modality

act:
    symbols
    | symbol_graph
    | query
    | assertion
    | proof_step
    | program
    | environment_action
    | architecture_edit

info:
    evaluator-only grammar
    evaluator-only ontology
    hidden ground truth
    proof / causal trace
    generation seed
    curriculum metadata
    capability tags
```

`grammar`, `ontology`, hidden state, proofs, causal structure, and generation metadata should generally be withheld from the learner and available to the evaluator. environments may selectively expose them when the lesson itself is explicit rule learning.

## curriculum dimensions

rather than hard-code difficulty into environment names, parameterize environments along orthogonal axes:

- lexical novelty;
- vocabulary size;
- grammar complexity;
- recursion depth;
- compositional depth;
- sequence length;
- discourse horizon;
- world-state size;
- relational arity;
- partial observability;
- perceptual noise;
- semantic ambiguity;
- ontology novelty;
- ontology drift;
- number of agents;
- communication bandwidth;
- reasoning depth;
- planning horizon;
- action irreversibility;
- reward sparsity;
- uncertainty;
- adversariality;
- tool availability;
- computational budget;
- representation freedom.

an environment should therefore be understood as a generator over tasks, not as a static benchmark dataset.

## evaluation principles

1. **procedural train/test separation.** held-out evaluation should use unseen combinations of grammar, ontology, task structure, surface vocabulary, world dynamics, and objectives.
2. **semantic intervention tests.** rename symbols, permute entities, reorder syntax where grammar permits, or replace the surface language entirely. competence that vanishes under renaming was probably memorization.
3. **representation-transfer tests.** the same latent problem should appear under multiple encodings.
4. **inverse-task tests.** where possible train and evaluate both directions: parse/generate, program/explain, formalize/deformalize, teach/learn.
5. **sample-efficiency curves.** measure adaptation as a function of environment interactions, not merely final reward.
6. **reasoning-cost curves.** measure reward or correctness against tokens, symbolic operations, wall-clock compute, memory, and environment actions.
7. **calibration.** score whether the agent knows when a result is proved, probable, unsupported, contradictory, or unknowable.
8. **architecture ablations.** because modules are intended to be interchangeable, evaluate which capabilities truly require which forms of memory, parsing, search, abstraction, or self-editing.
9. **anti-reward-hacking checks.** symbolic tool construction and architecture modification create enormous exploit surfaces; evaluators need hidden constraints and causal audits.
10. **developmental transfer.** later courses should test whether earlier representations become reusable primitives rather than isolated competencies.

## curriculum overview

```text
symbols
→ syntax
→ semantics
→ grounding
→ compositionality
→ discourse
→ inference
→ action
→ abstraction
→ ontology
→ causality
→ mathematics
→ science
→ metareasoning
→ communication
→ multi-agent coordination
→ institutions
→ self-modeling
→ representation invention
→ open-ended epistemology
```

---

# i. symbols, grounding, and elementary language

## 1. `symbol-grounding`

- world: finite objects with discrete properties.
- input includes symbols such as `red`, `cube`, and `left_of`.
- tasks bind symbols to entities, properties, and relations.
- teaches denotation, reference, and primitive predicates.

## 2. `symbol-equivalence`

- multiple symbols can denote the same thing.
- examples: `scarlet ≡ red`, `automobile ≡ car`.
- tasks include synonym matching, canonicalization, and alias induction.
- teaches many-to-one lexical semantics.

## 3. `symbol-discrimination`

- distinguish near-neighbor concepts such as `red` vs `orange`, `inside` vs `overlapping`, or `dog` vs `wolf`.
- generated worlds make minimal semantic contrasts explicit.
- teaches category boundaries and discriminative features.

## 4. `sequence-copy`

- observe a symbolic sequence and reproduce it.
- vary sequence length, distractors, delays, and corruption.
- teaches exact symbolic transmission and sequence memory.

## 5. `next-symbol`

- procedurally generated languages with known stochastic or grammatical structure.
- predict or choose the next valid symbol.
- language modeling stripped to its minimal sequential form.
- teaches local statistical regularities.

## 6. `finite-state-language`

- generate and recognize strings from regular languages.
- include parity, repetition constraints, bounded dependencies, and arbitrary finite automata.
- teaches stateful syntax and automata induction.

## 7. `context-free-language`

- balanced brackets, nested expressions, arithmetic grammars, and recursive toy languages.
- tasks include accept/reject, parse, generate, and complete.
- teaches hierarchy, recursion, and stack-like state.

## 8. `parse-tree`

- input: token stream.
- output: explicit symbolic tree or graph.
- grammars vary across episodes and should not assume english.
- teaches constituency and structural decomposition.

## 9. `tree-to-sequence`

- inverse of parsing.
- symbolic AST or semantic structure becomes a grammatical surface sequence.
- teaches realization and generation.

## 10. `variable-binding`

- manipulate structures such as `give(x,y,z)` and quantified variables.
- tasks include substitution, alpha-renaming, capture avoidance, and identity tracking.
- teaches variable identity independent of token identity.

## 11. `unification`

- prolog-like term matching over recursively structured expressions.
- example: `parent(x,bob)` unified with `parent(alice,bob)` gives `x=alice`.
- include occurs checks and incompatible structures.
- teaches structural symbolic matching.

---

# ii. compositional semantics and logical language

## 12. `predicate-logic`

- facts, predicates, rules, and queries.
- example: `bird(tweety)`, `bird(x) -> can_fly(x)`.
- output answers, bindings, or proof traces.
- teaches compositional propositional semantics and inference.

## 13. `quantification`

- `all`, `some`, `none`, `exactly three`, `most`, and generated generalized quantifiers.
- worlds make truth conditions explicit.
- teaches quantifier semantics and cardinality.

## 14. `scope-ambiguity`

- expressions admit multiple logical forms.
- agent enumerates, ranks, or resolves interpretations using context.
- teaches syntax-semantics ambiguity and scope.

## 15. `compositional-reference`

- commands such as `the red object left of the blue cube`.
- progressively deeper relational descriptions.
- teaches recursive denotation and referring expressions.

## 16. `spatial-language`

- 2d or 3d symbolic worlds.
- concepts include `left`, `inside`, `near`, `behind`, `between`, and coordinate-frame changes.
- include egocentric, allocentric, object-relative, and learned frames.
- teaches grounded relational semantics.

## 17. `temporal-language`

- event traces plus `before`, `after`, `until`, `while`, `always`, and `eventually`.
- later variants add tense and aspect.
- teaches temporal semantics and ordering.

## 18. `event-semantics`

- represent events explicitly, e.g. `eat(e1, agent=john, patient=apple, time=t2)`.
- map surface descriptions to and from event graphs.
- teaches argument structure and event composition.

## 19. `thematic-roles`

- agent, patient, instrument, source, goal, experiencer, etc.
- vary active/passive constructions and word order.
- teaches role extraction independent of surface position.

---

# iii. language as action

## 20. `instruction-following-micro`

- executable commands such as `move a left`, `pick up b`, `put a inside c`.
- world state changes after each action.
- teaches language-to-action grounding.

## 21. `instruction-composition`

- instructions such as `pick up a, then place it beside b unless c is red`.
- include sequencing, branching, conjunction, and nested conditions.
- teaches compositional control flow.

## 22. `pronoun-coreference`

- discourse entities persist across utterances.
- generated ground truth determines valid referents.
- teaches anaphora and entity continuity.

## 23. `discourse-state`

- facts enter and leave salience over multiple turns.
- later utterances rely on earlier mentions.
- teaches language as state update rather than isolated strings.

## 24. `ellipsis`

- recover omitted symbolic structure.
- example family: `alice likes tea and bob does too`.
- teaches latent structural reuse.

## 25. `presupposition`

- distinguish asserted content from background commitments.
- examples include definite descriptions and change-of-state verbs.
- teaches layered semantic commitments.

## 26. `implicature`

- cooperative games where literal truth is insufficient.
- generated speaker policies make pragmatic inference measurable.
- teaches inference from communication policy and alternatives.

## 27. `speaker-listener-game`

- one agent observes a world state and sends symbols; another acts.
- symbols may initially have no predefined meaning.
- teaches emergence and coordination of communication protocols.

## 28. `lexicon-induction`

- unknown language paired with grounded situations.
- infer meanings from use rather than explicit dictionaries.
- teaches language acquisition.

## 29. `grammar-induction`

- demonstrations sampled from randomly generated grammars.
- infer production rules or an equivalent recognizer/generator.
- teaches abstraction over linguistic systems.

## 30. `few-shot-language-learning`

- every episode introduces a new miniature language.
- support demonstrations are followed by held-out commands or questions.
- teaches meta-learning of language.

## 31. `translation`

- map between independently generated symbolic languages.
- neither side needs to be english.
- teaches invariant semantics under surface-form change.

## 32. `paraphrase`

- many surface structures map to the same logical form.
- teaches semantic equivalence classes.

## 33. `semantic-entailment`

- given proposition set `p`, determine whether `q` is entailed, contradicted, or unknown.
- world-model-backed labels are generated exactly.
- teaches disciplined inference.

## 34. `knowledge-update`

- initial knowledge base plus utterance yields a modified knowledge base.
- distinguish assertion, correction, retraction, qualification, and uncertainty.
- teaches conversational epistemics.

## 35. `belief-state`

- multiple agents know different things.
- represent nested beliefs such as `alice believes bob has the key`.
- teaches intensional semantics and theory-of-mind structure.

## 36. `question-answering`

- queries over explicit symbolic worlds.
- include who/what/where/when/why/how-many and generated query operators.
- teaches mapping interrogative form to reasoning operation.

## 37. `question-generation`

- agent must identify information missing for a task and formulate a useful query.
- teaches active information acquisition.

## 38. `interactive-reference`

- instructions may be ambiguous.
- agent can ask clarifying questions at a communication cost.
- teaches pragmatic disambiguation and value-of-information reasoning.

## 39. `definitions`

- introduce novel concepts explicitly, e.g. `a dax is any red triangle adjacent to a circle`.
- later tasks require applying them compositionally.
- teaches symbolic concept installation.

## 40. `concept-invention`

- recurring structures can be compressed by inventing reusable predicates.
- reward future utility, not merely shorter current descriptions.
- teaches abstraction and vocabulary growth.

---

# iv. analogy, causality, planning, and programs

## 41. `analogy`

- map relational structures between domains.
- move beyond token analogies toward graph-structural correspondence.
- teaches role-preserving structural mapping.

## 42. `causal-language`

- worlds permit interventions.
- distinguish causation from correlation and temporal precedence.
- represent claims such as `a caused b` and conditional interventions.
- teaches causal semantics.

## 43. `counterfactuals`

- explicit structural-causal-model-like worlds.
- answer questions about alternative interventions and histories.
- teaches subjunctive reasoning.

## 44. `planning-language`

- textual or symbolic goal becomes a plan.
- use STRIPS/PDDL-like domains as one family, not the universal representation.
- teaches goal decomposition and executable semantics.

## 45. `procedural-language`

- instructions specify algorithms: loops, branches, variables, termination conditions.
- teaches procedural abstraction.

## 46. `program-synthesis`

- natural or symbolic specification becomes an executable program in a small DSL.
- DSLs vary across episodes.
- teaches language as specification.

## 47. `program-explanation`

- executable program becomes a symbolic or natural description.
- inverse direction prevents one-way translation hacks.
- teaches semantic serialization.

## 48. `dialogue-game`

- multi-turn cooperative objective requiring negotiation, correction, reference, confirmation, and shared state.
- teaches language as interactive control.

## 49. `negotiation-game`

- agents have private utilities or resources.
- communicate offers, constraints, commitments, and counteroffers.
- teaches speech acts and strategic pragmatics.

## 50. `deception-detection`

- speakers may issue false claims according to explicit incentives.
- reason jointly about utterance content, world state, and speaker state.
- teaches separation of statement content from truth.

## 51. `social-convention-learning`

- semantics depends on an arbitrary shared convention learned within the episode.
- teaches socially coordinated rather than externally fixed meaning.

## 52. `document-world`

- persistent corpus with entities, events, and relations distributed across passages.
- tasks query, update, navigate, and reconcile it.
- bridges toy language environments and realistic textual memory.

## 53. `compressed-language`

- communication bandwidth is explicitly penalized.
- agents invent concise compositional protocols.
- tests pressures toward syntax, reusable abstractions, and compression.

## 54. `noisy-channel-language`

- symbols may be dropped, corrupted, inserted, or reordered.
- infer intended meaning using syntax, semantics, and world state.
- teaches error correction and redundancy.

## 55. `multimodal-symbolization`

- image, audio, or sensor observations map into symbols and symbolic hypotheses.
- perception can remain modular and expose uncertainty.
- teaches coupling language to nonlinguistic representations.

## 56. `open-world-language`

- unknown entities and properties can appear.
- distinguish `false` from `unknown`.
- teaches epistemic hygiene.

## 57. `continual-language`

- vocabulary, grammar, and conventions drift over episodes.
- old knowledge remains partially useful.
- teaches continual adaptation without wholesale overwrite.

## 58. `language-culture`

- populations transmit language across generations.
- new learners receive examples produced by previous agents.
- study emergence of compositionality, regularization, syntax, and convention.

## 59. `general-language-agent`

- procedurally compose prior environment families.
- each episode may contain a new grammar, lexicon, world, and task.
- agent must infer the symbolic communication contract.

## 60. `natural-language-bridge`

- attach real corpora only after general symbolic learning is established.
- natural text maps to/from induced symbolic structures and executable actions.
- next-token prediction becomes another standardized environment rather than the master ontology.

---

# v. ontology and representation

## 61. `ontology-construction`

- receive observations and propositions without a fixed ontology.
- invent entities, types, relations, inheritance, and constraints.
- optimize predictive/explanatory utility plus representational economy.
- teaches that ontology itself is learnable.

## 62. `ontology-revision`

- previously useful categories become inconsistent with new evidence.
- split, merge, weaken, or qualify concepts and axioms.
- teaches non-monotonic conceptual development.

## 63. `ontology-alignment`

- two agents independently developed ontologies.
- infer correspondences, partial mappings, incompatible decompositions, and translation rules.
- deeper than lexical translation because the conceptual partitions can differ.

## 64. `representation-selection`

- the same task can be encoded as graph, sequence, set, program, algebra, automaton, geometry, etc.
- agent chooses representation before solving.
- reward includes correctness and computational efficiency.

## 65. `representation-invention`

- existing vocabulary makes a task family cumbersome.
- agent may define a new representational primitive.
- evaluate systematic compression or computational advantage on future instances.

## 66. `abstraction-ladder`

- concrete episodes become recurring relations, abstract schemas, and schemas over schemas.
- example: `alice gives bob apple` → `transfer` → `resource-transfer` → `state-transition-with-conserved-object`.
- teaches explicit abstraction depth.

## 67. `conceptual-chunking`

- repeatedly used proof, planning, or parsing fragments become callable symbolic macros.
- measure search reduction and transfer.
- teaches reusable cognitive chunks.

---

# vi. scientific induction and model discovery

## 68. `latent-rule-discovery`

- world follows hidden laws.
- infer compact executable rules from trajectories.
- include cellular automata, arithmetic systems, graph dynamics, and toy physics.

## 69. `scientific-model-induction`

- observations and interventions support competing theories.
- agent generates candidate models and predicts held-out outcomes.
- reward explanatory and predictive performance.

## 70. `experimental-design`

- uncertainty over hypotheses plus a limited intervention budget.
- choose experiments maximizing expected information or downstream decision value.
- teaches active epistemology.

## 71. `theory-comparison`

- several symbolic theories explain observed data.
- compare predictive accuracy, simplicity, scope, falsifiability, and compute cost.
- distinguishes fitting from understanding.

## 72. `falsification`

- construct observations or interventions that discriminate hypotheses.
- reward minimally sufficient counterexamples and informative tests.

## 73. `anomaly-resolution`

- established theory works except for anomalous observations.
- possibilities include noise, hidden variables, boundary conditions, corrupted measurement, or theory failure.
- teaches disciplined revision rather than reflexive ontology explosion.

## 74. `mechanism-discovery`

- distinguish predictive law from causal mechanism.
- hidden intermediate states may be exposed experimentally.
- agent must explain how effects arise.

## 75. `multiscale-modeling`

- microscopic and macroscopic descriptions coexist.
- derive coarse variables and determine when each scale is sufficient.
- examples: particles → pressure; local agents → population statistic.

## 76. `emergence-discovery`

- detect stable high-level regularities absent from the primitive vocabulary.
- invent macrostates or operators with predictive closure.
- tests genuine higher-level concept discovery.

## 77. `invariance-discovery`

- identify transformations under which relevant structure is unchanged.
- permutation, rotation, renaming, translation, scaling, and generated transformations.
- teaches equivalence classes from invariants.

## 78. `symmetry-reasoning`

- reason using discovered transformation groups.
- infer missing states, equivalences, or conserved structures.
- bridges symbolic reasoning with geometry and algebra.

## 79. `conservation-law-discovery`

- search for expressions invariant under environment dynamics.
- include conserved quantities, parity, flow constraints, and graph invariants.
- teaches symbolic compression of dynamics.

## 80. `dimensional-analysis`

- quantities carry symbolic dimensions.
- identify impossible equations, constrain candidate laws, and discover dimensionless combinations.
- teaches algebra with semantic constraints.

---

# vii. mathematics and formal reasoning

## 81. `mathematical-definition-learning`

- novel objects are introduced through axioms, examples, or counterexamples.
- infer consequences and membership.
- tests whether definitions create operational concepts.

## 82. `conjecture-generation`

- given structures and observations, propose claims likely to be both true and informative.
- evaluate novelty, truth, generality, and downstream usefulness.

## 83. `theorem-proving`

- deductive symbolic environments with proof search, rewriting, induction, and lemma application.
- support multiple formal systems rather than a single prover.

## 84. `lemma-invention`

- target proofs require useful intermediate propositions not supplied by the environment.
- reward reusable lemmas and reduced future proof cost.

## 85. `proof-compression`

- transform long derivations into shorter conceptual proofs by introducing abstractions or stronger lemmas.
- teaches proof structure rather than mere validity.

## 86. `proof-translation`

- translate proofs between logical systems or representational styles where mappings are valid.
- tests representation-independent understanding of derivation structure.

## 87. `counterexample-generation`

- given conjecture, construct a small or illuminating violating model.
- provides strong anti-hallucination pressure against false universality.

## 88. `logic-discovery`

- inference rules are not given.
- environment's epistemic dynamics instantiate a logical regime which the learner must induce.
- variants can include classical, intuitionistic, paraconsistent, modal, temporal, and probabilistic logics.

## 89. `logic-selection`

- different domains require different inference semantics.
- agent selects an appropriate calculus or composes several.
- teaches that reasoning is not one universal operator.

## 90. `uncertain-symbolic-reasoning`

- propositions carry probabilities, confidence sets, intervals, or distributions.
- symbolic derivations propagate uncertainty.
- bridges strict symbolic and probabilistic representations.

## 91. `default-reasoning`

- rules hold by default but admit exceptions.
- infer defeasible conclusions and retract them when contrary evidence appears.
- teaches non-monotonic logic.

## 92. `belief-revision`

- inconsistent evidence enters the knowledge base.
- restore coherence while minimizing unnecessary destructive changes.
- AGM-like worlds are one useful formalization.

## 93. `contradiction-tolerance`

- sources can conflict without immediate resolution.
- continue useful reasoning without logical explosion.
- trains paraconsistent behavior.

---

# viii. epistemics, argument, and teaching

## 94. `source-provenance`

- every proposition has an origin.
- `x said p` is represented separately from `p`.
- teaches provenance-aware epistemics.

## 95. `source-reliability-learning`

- infer which agents and sensors are reliable in which domains and conditions.
- reliability should be conditional rather than a single global score.

## 96. `argumentation`

- claims, evidence, warrants, rebuttals, defeaters, and dependencies form explicit graphs.
- score logical support rather than rhetorical persuasion.

## 97. `adversarial-argumentation`

- another agent actively searches for weaknesses in a theory.
- success means surviving valid criticism or revising appropriately.

## 98. `explanation`

- answer `why?` at the appropriate abstraction level.
- distinguish causal explanation, proof, mechanism, purpose, and historical account.
- reward audience-relative sufficiency.

## 99. `explanation-repair`

- listener indicates which part of an explanation failed.
- revise based on inferred missing prerequisite or ambiguity.
- teaches pedagogical adaptation.

## 100. `teaching`

- student agent has an unknown knowledge state.
- teacher chooses examples, definitions, questions, or exercises.
- reward improvement in student competence.

## 101. `curriculum-design`

- agent chooses learning experiences for another learner or itself.
- optimize ordering, spacing, difficulty, and information value.
- teaches meta-pedagogy.

## 102. `knowledge-gap-detection`

- before answering, classify information as known, inferable, uncertain, unknowable from current evidence, or malformed.
- reward calibrated refusal to collapse distinctions.

---

# ix. problem formulation and hierarchical agency

## 103. `problem-formulation`

- raw scenario contains no explicit variables or objective.
- agent identifies state, actions, constraints, objective, and unknowns.
- one of the central advanced competencies.

## 104. `problem-reformulation`

- current representation produces pathological search or ambiguity.
- transform the problem into an equivalent but more tractable form.
- teaches intelligence through representational change.

## 105. `decomposition`

- complex goal requires discovering subproblems and dependencies.
- subgoal graph is not supplied.
- evaluate decomposition correctness and computational advantage.

## 106. `hierarchical-planning`

- invent reusable abstract actions and recursively instantiate them.
- HTN-like structure may emerge rather than being given.

## 107. `long-horizon-projects`

- thousands of steps with persistent memory, interruptions, failures, prerequisites, and changing state.
- teaches maintaining coherent intent across long temporal scales.

## 108. `resource-bounded-reasoning`

- computation, time, environment actions, and memory have explicit costs.
- decide whether to reason, query, approximate, cache, delegate, or act.

## 109. `anytime-reasoning`

- produce progressively better solutions as more computation becomes available.
- evaluate quality-vs-compute curves.

## 110. `metareasoning`

- reasoning operators themselves have costs and expected values.
- choose among search, proof, simulation, memory lookup, experiment, delegation, or action.
- teaches reasoning about how to reason.

## 111. `strategy-discovery`

- repeated problem families reward induced reusable strategies rather than independent instance solving.

## 112. `strategy-transfer`

- learned reasoning strategy reappears under new symbols, ontology, or domain.
- tests structural rather than surface learning.

## 113. `algorithm-discovery`

- infer procedures from I/O demonstrations or reward.
- include sorting, traversal, dynamic programming, search, compression, and novel generated algorithms.

## 114. `algorithm-analysis`

- compare candidate algorithms by time, memory, approximation error, stability, and robustness.
- teaches reasoning about computation.

---

# x. reflective computation and language design

## 115. `recursive-self-application`

- symbolic procedures operate on symbolic descriptions of procedures.
- interpreters, compilers, and theorem provers can reason about similar systems.
- controlled route toward reflective computation.

## 116. `metalinguistic-reasoning`

- language can describe syntax, semantics, ambiguity, grammar, and reference in other languages or itself.
- language becomes an object of language.

## 117. `language-design`

- given task distribution and communication constraints, invent a language.
- choose lexicon, grammar, compositional operators, and redundancy.
- score learnability, expressivity, ambiguity, and transmission cost.

## 118. `dsl-invention`

- invent domain-specific languages that make recurring computations or plans concise.
- score downstream program synthesis and reasoning efficiency.

## 119. `compiler-construction`

- map an invented high-level symbolic language to executable primitive operations.
- enables self-extensible computation.

## 120. `interpreter-learning`

- infer the semantics of a novel symbolic language from demonstrations of program behavior.
- output or instantiate an interpreter.

---

# xi. protocols, institutions, and distributed intelligence

## 121. `protocol-discovery`

- multi-agent systems must invent structured interaction protocols.
- requests, responses, acknowledgments, retries, transactions, locks, and ownership can emerge.

## 122. `institution-learning`

- population operates under roles, permissions, contracts, rules, and penalties.
- infer institutional machinery from interaction traces.

## 123. `institution-design`

- given agent incentives and system-level objectives, invent rules that induce desirable collective outcomes.
- bridges symbolic ai, governance, and mechanism design.

## 124. `norm-reasoning`

- distinguish facts from obligations, permissions, prohibitions, and exceptions.
- include conflicting and hierarchical norms.

## 125. `contract-reasoning`

- promises create future obligations conditioned on events.
- track fulfillment, breach, cancellation, delegation, transfer, and expiry.

## 126. `mechanism-design`

- agents possess private information and incentives.
- design interaction mechanisms to achieve system objectives under strategic behavior.

## 127. `coalition-formation`

- reason about groups, shared goals, bargaining, commitments, entry, exit, and defection.

## 128. `distributed-knowledge`

- no agent sees enough to solve the task alone.
- communication is costly.
- decide what information must be transmitted, when, and to whom.

## 129. `collective-theory-building`

- several agents independently investigate one world.
- combine partially incompatible hypotheses into a shared theory.
- synthetic scientific community.

## 130. `cultural-evolution`

- languages, concepts, procedures, tools, and norms transmit across generations.
- evaluate which symbolic structures survive bottlenecks and why.

---

# xii. history, narrative, perspective, and identity

## 131. `historical-reconstruction`

- observe present state plus incomplete records.
- infer plausible histories while representing underdetermination explicitly.

## 132. `narrative-modeling`

- compress long event sequences into causal, intentional, and thematic structure.
- characters, goals, conflicts, reversals, and consequences become explicit symbols.

## 133. `multi-perspective-modeling`

- the same event is described by agents with different information or incentives.
- maintain perspective-relative beliefs without discarding shared ground truth where available.

## 134. `identity-continuity`

- entities change names, roles, properties, parts, and locations.
- infer whether they remain the same entity according to domain-specific identity rules.

---

# xiii. self-modeling and architecture adaptation

## 135. `self-model`

- agent receives symbolic observations of its own state, memory, capabilities, and actions.
- predict its own behavior and performance.
- this is operational self-modeling, not a consciousness claim.

## 136. `capability-estimation`

- before attempting a task, estimate success probability, resources, and likely failure modes.
- score empirical calibration.

## 137. `self-error-diagnosis`

- after failure, classify source: perception, parsing, memory, representation, inference, planning, execution, communication, or objective misunderstanding.
- teaches causal attribution over internal failures.

## 138. `self-repair`

- modify rules, memories, strategies, or modules after diagnosis.
- compare local patching against structural replacement.

## 139. `architecture-selection`

- several parsers, memories, reasoners, planners, or representations are available.
- agent chooses the architecture appropriate to the task.
- directly exercises an interchangeable lexer/parser/reasoner stack.

## 140. `architecture-composition`

- compose reasoning modules into a temporary computation graph.
- examples: parser → geometric reasoner → theorem prover → planner.
- teaches dynamic modular cognition.

## 141. `tool-construction`

- available tools are insufficient.
- agent builds a reusable symbolic tool and subsequently invokes it.
- tool use becomes tool creation.

## 142. `external-memory-design`

- choose schemas, graphs, indexes, caches, summaries, and retrieval policies for persistent knowledge.
- reward future retrieval efficiency and fidelity.

## 143. `knowledge-refactoring`

- large symbolic memory becomes redundant, inconsistent, or badly organized.
- reorganize it without losing behavioral competence.

## 144. `semantic-compression`

- compress accumulated observations and rules into a smaller generative theory.
- reconstruction or prediction error bounds are explicit.

## 145. `minimum-description-learning`

- explicit MDL-style objective balances theory complexity and unexplained data.
- encourages reusable abstractions rather than arbitrary lookup tables.

---

# xiv. open-ended epistemology

## 146. `open-ended-concept-discovery`

- no externally specified concept vocabulary.
- invent latent concepts that improve prediction, compression, control, or communication.

## 147. `open-ended-question-generation`

- agent decides which questions are worth asking.
- value questions by expected downstream epistemic or decision benefit.

## 148. `research-program`

- persist unresolved questions, theories, experiments, results, dependencies, and confidence.
- autonomously choose the next research action over many episodes.

## 149. `paradigm-shift`

- incumbent framework becomes progressively awkward or wrong.
- learner must replace high-level assumptions rather than endlessly patch local failures.
- teaches structural theory revision.

## 150. `world-model-synthesis`

- integrate objects, relations, processes, causal laws, agents, beliefs, institutions, uncertainty, and temporal history.
- maintain a queryable and revisable symbolic world model.

## 151. `cross-domain-unification`

- separate domains instantiate isomorphic structure.
- discover a common abstraction that improves transfer.
- examples can include electrical flow, fluid flow, information flow, or resource flow.

## 152. `theory-transfer`

- reuse abstractions or mechanisms discovered in one world to accelerate theory formation in another.

## 153. `formalization`

- input: informal claim, description, or task.
- output: explicit ontology, definitions, assumptions, variables, and propositions.
- bridge from human language to rigorous symbolic reasoning.

## 154. `deformalization`

- formal theory becomes explanations at different technical levels or surface languages.
- ensures internal structures remain communicable and semantically interpretable.

## 155. `ambiguity-preservation`

- evidence may support several interpretations.
- maintain a set or distribution instead of prematurely selecting one.

## 156. `underspecification-reasoning`

- distinguish explicitly determined content from conventional or contextual inference.
- particularly important for natural-language interfaces.

---

# xv. values and goal cognition

## 157. `value-learning`

- infer preferences or objective structure from choices, demonstrations, instructions, and corrections.
- keep descriptive beliefs separate from utilities.

## 158. `multi-objective-reasoning`

- goals conflict.
- represent pareto fronts, lexicographic priorities, constraints, thresholds, and tradeoffs without forcing premature scalarization.

## 159. `goal-inference`

- infer another agent's plausible objectives from behavior.
- compare competing goal hypotheses.

## 160. `goal-revision`

- new evidence changes which objectives remain appropriate or feasible.
- update goals rather than merely replanning toward obsolete ones.

## 161. `goal-generation`

- persistent high-level preferences plus world state generate useful intermediate objectives.
- advanced autonomous agency.

## 162. `reflective-goal-reasoning`

- reason symbolically about the origin, consistency, conflicts, dependencies, and consequences of goals.
- intentionally late in the curriculum.

---

# xvi. civilization-scale symbolic learning

## 163. `civilization-simulator`

- many agents with language, technology, institutions, resources, partial information, and generations.
- symbolic culture and technology accumulate over time.
- capstone for social-symbolic intelligence.

## 164. `scientific-civilization`

- agents discover theories, publish symbolic artifacts, critique claims, replicate experiments, establish standards, and accumulate knowledge.
- objective is cumulative epistemic progress rather than individual score.

## 165. `symbolic-world-builder`

- instead of solving an environment, create one.
- define ontology, dynamics, language, tasks, and evaluation criteria.
- other agents must subsequently learn within it.

## 166. `curriculum-invention`

- given a target capability, generate a sequence of environments likely to induce it.
- symbolic intelligence learns to engineer symbolic intelligence.

---

# xvii. ultimate transfer and open-world capstones

## 167. `universal-interface-transfer`

- randomly generated environment with unknown observation language, action language, state structure, and task semantics.
- agent bootstraps all four from interaction.
- minimal prior is the standardized environment interface itself.

## 168. `unknown-game`

- zero task-specific semantic priors beyond the generic interaction protocol.
- infer what exists, what observations matter, what actions do, what reward means, what regularities hold, and what representations should be constructed.
- artificial epistemogenesis.

## 169. `symbolic-generalist`

- held-out mixtures of new languages, ontologies, dynamics, reasoning regimes, agents, objectives, and interfaces.
- no curriculum component appears verbatim at test time.
- score transfer slope, sample efficiency, asymptotic competence, and reasoning cost.

## 170. `open-world-research-agent`

- capstone agent must:
  - discover ontology;
  - acquire language;
  - form and compare theories;
  - design experiments;
  - construct representations and tools;
  - communicate findings;
  - revise models under criticism;
  - manage uncertainty and provenance;
  - plan and act over long horizons;
  - modify its own symbolic scaffolding when useful.
- at this point, `language model` is no longer an adequate description of the trained system.

---

# training architecture notes

## interchangeable symbolic pipeline

an initial implementation can expose a modular stack:

```text
environment
    ↓
lexer / observation encoder
    ↓
typed symbols / tokens
    ↓
parser / structure inducer
    ↓
symbol structures / graphs / programs
    ↓
reasoning engine(s)
    ↓
planner / policy / generator
    ↓
symbolic action encoder
    ↓
environment
```

however, later curriculum stages should deliberately violate the assumption that these boundaries are fixed. the agent should be able to choose among or construct encoders, parsers, reasoners, memories, and intermediate representations.

## capability registry

each environment should annotate which capabilities it exercises, for example:

```text
lexical_grounding
sequence_memory
finite_state_induction
recursive_syntax
variable_binding
unification
quantification
spatial_reasoning
temporal_reasoning
causal_reasoning
belief_modeling
planning
program_synthesis
abstraction
ontology_learning
scientific_induction
proof_search
metareasoning
multi_agent_coordination
self_modeling
architecture_adaptation
open_ended_discovery
```

this allows curriculum sampling to be driven by measured capability deficits rather than a fixed linear syllabus.

## curriculum scheduler

use several scheduling regimes during research:

1. **strict developmental schedule** — advance only after competence thresholds.
2. **interleaved rehearsal** — retain earlier tasks to detect catastrophic forgetting.
3. **frontier sampling** — concentrate probability near tasks with intermediate success rates.
4. **competence-gap sampling** — select tasks maximizing expected improvement on weak capability dimensions.
5. **transfer probes** — continuously inject unseen compositions and renamed representations.
6. **open-ended generation** — later agents generate environments or curricula for themselves and other agents.

## language-model datasets as environments

ordinary language-model corpora can be wrapped in the same interface:

```text
observation = prefix / context / symbolic memory
act         = next token | span | parse | semantic structure | program | query
reward      = log-likelihood | exactness | semantic equivalence | execution success
```

variants should include:

- next-token prediction;
- masked reconstruction;
- syntactic parsing;
- semantic parsing;
- translation;
- question answering;
- tool invocation;
- program synthesis;
- document-state updating;
- dialogue;
- long-context retrieval;
- language-conditioned environment control.

this prevents the architecture from splitting into a special `language model` subsystem and a separate `agent` subsystem. both are policies over standardized environments with different observation/action semantics.

## symbolic rlm / continual-harness direction

once the basic learner is functional, expose portions of its own working context and symbolic machinery as environment state.

candidate actions include:

```text
create_symbol(...)
merge_symbols(...)
split_symbol(...)
define_predicate(...)
define_type(...)
revise_ontology(...)
create_rule(...)
retract_rule(...)
create_macro(...)
create_parser(...)
select_parser(...)
create_reasoner(...)
compose_reasoners(...)
create_memory_index(...)
refactor_memory(...)
spawn_subagent(...)
delegate(...)
create_tool(...)
create_environment(...)
create_curriculum(...)
```

this should not initially mean unrestricted self-modifying source code. start with a typed, auditable architecture-edit DSL. every edit should be attributable to a trajectory, reversible, and evaluable on held-out tasks. later research can relax those boundaries.

## progression from object-level to meta-level learning

one useful staged progression is:

```text
stage 0: fixed language + fixed ontology + fixed reasoner
stage 1: learned language
stage 2: learned grammar / parser
stage 3: learned ontology
stage 4: learned abstractions / macros
stage 5: learned reasoning strategy
stage 6: learned module selection
stage 7: learned module composition
stage 8: learned symbolic tools / DSLs
stage 9: learned architecture edits
stage 10: learned curriculum / environment generation
```

crucially, each transition should be evaluated by whether the newly exposed degrees of freedom improve generalization and sample efficiency, not by whether the agent merely uses them.

# central research question

can reinforcement learning over a sufficiently diverse curriculum cause an agent to progress from **using symbols** to **learning symbolic systems**, and finally to **constructing the symbolic machinery by which it learns and reasons**?

if yes, the interesting unit of intelligence is not a fixed symbolic calculus and not a fixed neural sequence model. it is the adaptive process that discovers which symbols, structures, programs, memories, abstractions, and reasoning operators are useful for a changing environment.
