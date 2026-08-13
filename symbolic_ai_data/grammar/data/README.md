# Language data

Two kinds of thing live here, and the split is the tier system rather than an
accident of history.

## `packs/` — the hand-written grammars

One file per language somebody wrote and checked: English, Spanish, Chinese,
Turkish, Swahili. Each holds that language's whole pack — its vocabulary, its
closed class, its relational phrasings, its section lead-ins — and is keyed by
the pack's name, because a pack is an implementation and `english_synonym`
shares English's ISO code while being a different pack.

Five files is not the language count. It is the number of languages a person
has verified. Everything else is derived.

## `tables/` — one parameter across many languages

Keyed by ISO 639-3, because these are facts about languages rather than
implementations of them:

| file | what it records |
| --- | --- |
| `articles.json` | definite and indefinite articles by class and number |
| `copulas.json` | the present third-person copula, empty where a language writes none |
| `field_intros.json` | idiomatic lead-ins for the commonest section headings |
| `instructions.json` | what the learner is told to do |
| `lemmas.json` | curriculum words that are inflected English, and the citation form |
| `paradigm_seeds.json` | English lemmas the morphology lessons build sentences from |
| `predicates.json` | predicate heads and the English words that mean them |
| `sandhi.json` | what two words do to each other at the boundary |

A language absent from a table is derived from WALS, Wiktionary and UniMorph
instead, and says so through `DerivedGrammar.gaps()`. Four hundred and four
languages have no file anywhere and are not meant to.

## Why one directory

There were three, and two of them for historical reasons: the original packs
kept their vocabulary under `languages/data/`, later packs shipped beside
their grammar under `grammar/grammars/data/`, and English, Spanish and Chinese
had a file in each that was merged at load time. Same kind of content, three
places, so counting the files told you nothing about how many languages the
package has.

`languages.db` is the built lexicon and morphology — 2GB, gitignored,
reproducible from cited sources with `scripts/build_langdb.py`.
