# The semantic high-impact taxonomy — derivation receipt

`docs/taxonomies/semantic-high-impact/ACTIVE.json`, the file
`semantic-high-impact-error-rate-v1` has been failing closed on since it was registered on
2026-09-06. **It is a mechanical projection of the Earnings-22 semantic scan's committed
content-impact model, not a new judgement**: every level in it is produced by
`analysis.e22_error_taxonomy.semantic_impact`, and
`tests/unit/test_semantic_impact_taxonomy.py::test_the_projection_equals_the_e22_impact_function`
asserts that instance by instance by running the scan's own function on real one-word spans.

**Zero contacts of every kind** — model, GPU, tool, embedding, network, audio — and **no gold or
reference read of any kind**. The only inputs are two committed source modules and `git show`.

| | |
|---|---|
| generator | `scripts/build_semantic_impact_taxonomy.py` |
| projection | `src/speech_aware_evidence_acquisition/analysis/semantic_impact_taxonomy.py` |
| source module | `src/speech_aware_evidence_acquisition/analysis/e22_error_taxonomy.py` |
| source commit | `9ee2fb11e1669544283a4492dcdca60d8b7953ee` |
| source sha256 | `dfea875fbbfebb5ad3034f649cb1976bccbd32816abe5770248840bb96a28a1c` (blob bytes at that commit, `git show <commit>:<path>` — the repository's stated hash authority, never the working tree's) |
| taxonomy id | `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` |
| rules | 9,237 — HIGH 20, LOW 1, NONE 9,216 |

## What is projected, and what could not be

E22 tags every error span twice: `content_impact`, from the span's own tokens, and `impact`, that
reading after the category ruling of `IMPACT_NEUTRAL_CATEGORIES`. **This export projects
`content_impact`**, the half that is a function of tokens alone. The category ruling is decided by
the 32-rule cascade from the utterance's neighbours, the segment table and the clip boundary; a
`(reference word, hypothesis word)` key cannot see any of them.

`reproduction.semantic_impact` looks a rule up by exact key in one fixed order — `(ref, hyp)`,
`(ref, "*")`, `("*", hyp)`, `("*", "*")` — so a rule names an exact normalized word or "any word".
Two of E22's three HIGH triggers are not exact-word predicates and are therefore **absent from this
file entirely, rather than approximated**:

* **digits.** "the token contains a digit" is an open class after Whisper normalization (`2022`,
  `$1500000`, `14.9%`, `1st`). A partial enumeration would silently score an unlisted number as
  ordinary wording.
* **call-inventory named entities.** E22 rebuilds an entity inventory per call from that call's own
  reference sentences (64–192 forms). One static file cannot be per-call, and a union across calls
  would tag another call's names.

**So this taxonomy's HIGH tier is E22's NEGATION trigger alone, and the rate it produces is a strict
LOWER BOUND on E22's own content-impact HIGH rate.** It must be quoted as the negation-critical rate,
never as E22's 1.92 % agentic error rate. That limit is asserted by
`test_the_high_tier_is_exactly_the_negation_trigger`, and it is restated inside the emitted file
under `derivation.consequence`.

**On Earnings-21 the two missing triggers are not lost.** They are carried by two dedicated metrics
that are better anchored than E22's span tag was:

| E22 HIGH trigger | carried on Earnings-21 by | anchored on |
|---|---|---|
| a number or value changed | `numeric-value-accuracy-v1` | digit-bearing reference words, reported by kind |
| a named entity changed | `conec-entity-wer-official` | ConEC's own gold `wer_tags`, by published class |
| a negation changed | `semantic-high-impact-error-rate-v1` under this taxonomy | the E22 negation lexicon, verbatim |

One further deviation, in the LOW/NONE split only and never in a rate: `NONE` is a conjunction over
both sides ("*every* changed token is a stopword"), so it is emitted as the explicit product of the
E22 stopword lexicon against itself plus the deletion sentinel — exact for substitutions and
deletions, which are the operations that carry reference-word mass. An INSERTED function word is
looked up as `("*", hypothesis word)`, reaches the residual rule and is reported `LOW` where E22 says
`NONE`. Insertions carry zero reference mass by construction and are reported in their own
`insertions_by_level` map, so no rate moves.

## Files

| file | what it holds |
|---|---|
| `taxonomy-receipt.json` | the pinned source commit and blob sha256, the taxonomy's own sha256, its id, normalizer, levels, rule count and rule count per level, and the zero-contact record |
