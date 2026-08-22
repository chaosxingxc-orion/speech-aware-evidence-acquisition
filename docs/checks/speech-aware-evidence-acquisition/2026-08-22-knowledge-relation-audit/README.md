# Relation-level speech-native knowledge audit

## Scope

This model-free check audits whether the frozen Omni decoder would receive the
task information available in the query-isolated SLURP train corpus. It makes no
model request, reads no development or test label, changes no model parameter,
and does not authorize a new model contact. The resident llama.cpp decoder was
not restarted or reconfigured.

The audited parent binding is
`b7bca06170b44234975ae97df2c6e648d8a97edaf93058dbc2ce21620e288ceb`.
Its 540 registered query utterances and all matching normalized sentences are
removed before the audit. The remaining corpus contains 10,973 real-speech
SLURP train utterances.

## Corrected unit of completeness

The historical audit treated a scenario pair as the unit of residual knowledge.
That was too coarse. The 55 stable shared-action pairs contain 117 stable
`(left scenario, right scenario, action, entity signature)` relations. The
historical v3 graph covers all 55 pairs but only 55 of the 117 relations. Its
graph remains byte-identical at SHA-256
`5c858eed0f909ea75b9340646a4444aa13cf3882c35d3e79d04e394fed0d2b64`
and is now correctly blocked by the relation-level audit.

The successor keeps one boundary object per scenario pair while preserving all
117 relations inside those objects. Every relation binds its bilateral support
counts, one query-isolated prototype per side, and up to eight repeated
unigram/bigram cues per side. Provenance without the corresponding text in the
boundary is rejected.

## Local optimization evidence

All variants below use only the isolated train corpus. They are diagnostics for
knowledge construction, not SLU task results.

| Variant | Mean relation-balanced accuracy | Minimum | Relations below 0.5 | Decision |
| --- | ---: | ---: | ---: | --- |
| One raw prototype per side | 0.716 | 0.353 | 5 | Reject: unstable and semantically narrow |
| Two raw prototypes per side | 0.731 | 0.343 | 5 | Reject: prompt growth without minimum improvement |
| Three raw prototypes per side | 0.740 | 0.333 | 5 | Reject: prompt growth without minimum improvement |
| Relation-local top-5 cues, leave-one-sentence-out | 0.767 | 0.273 | 6 | Reject in favor of top-8 |
| Action-conditioned global top-5 cues | 0.695 | 0.234 | 16 | Reject: global frequency masks local object information |
| Local cues with action-conditioned stability backoff | 0.759 | 0.250 | 9 | Reject: added evidence is net noise |
| Relation-local top-8 cues, leave-one-sentence-out | 0.807 | 0.273 | 3 | Select as the compact lexical supply |

The full-data top-5 estimate appeared stronger than its leave-one-sentence-out
result. This difference is why the selected audit excludes every copy of the
evaluated normalized sentence before rebuilding its cues.

## Dataset-level semantic gaps

The remaining three top-8 failures exposed information that exact lexical
matching cannot represent cleanly:

- `calendar / datetime / query / event_name`: SLURP distinguishes a user's
  stored meeting or appointment from a general date, day, or time question about
  a public or named event. The datetime side has only five isolated examples.
- `news / social / query / date`: the social side has five examples spanning
  likes, status, basketball, social media, and one nearly unidentifiable generic
  utterance.
- `lists / social / query / date`: the same sparse social side must be separated
  from explicit task/list language.

Three bilateral semantic boundaries encode these dataset conventions in English.
Each side is bound to two or three isolated train utterance ids, and both the
source provenance and the rendered boundary text must be present. The semantic
boundaries cover four residual relations; the extra relation is the related
`calendar / datetime / query / (date, event_name)` signature.

The selected graph therefore supplies:

- 117 of 117 relation records;
- cross-validated lexical signal for 114 of 117 relations;
- source-bound semantic signal for the remaining three lexical failures;
- combined discriminative supply for 117 of 117 relations.

The graph is [slurp-signature-complete-decision-graph-v5.json](../../../../configs/knowledge/slurp-signature-complete-decision-graph-v5.json),
SHA-256 `58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc`.
Independent generation was byte-identical. The full audit is
[slurp-signature-complete-information-audit-v2.json](slurp-signature-complete-information-audit-v2.json),
SHA-256 `c4c1b4654bac3056887db32c554fd3a4c0d074b48ccab4fbaa5d157d3eb4de11`.

## Prompt geometry and remaining gates

The historical graph is 118,489 bytes, with median/maximum single-side boundary
lengths of 309/380 characters. The successor is 205,714 bytes, with 770/4,089
characters. The increase is bounded but material. Exact llama.cpp tokenizer
fit for the complete runtime prompt remains a required pre-contact check; this
report does not infer token fit from character counts.

The audit status is `admitted`, but its receipt explicitly leaves
`new_model_contact_authorized=false`. The strict GPU-utilization gate, a new
execution plan, protocol hash, and exposure registration remain independent
requirements. Log probabilities remain outside the method: generated-token
probabilities are not a speech-feature-to-fixed-key sequence score.
