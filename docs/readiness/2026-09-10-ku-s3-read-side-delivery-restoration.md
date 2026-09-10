# KU-S3 read-side delivery restoration

Record this scope after the recovered trio's registered as-sealed analysis and before deriving any joined delivery. This is a restoration of the inherited KC-S1b read convention, not a pre-generation registration.

## Observed gap and existing rule

All three new 1,000-row generations are finalized and scored once. The registered entity-side row-SLU-F1 contrasts pass their two numerical thresholds. The raw component outputs do not satisfy full intent equality: 456 sample IDs have different parsed scenario/action tuples across arms because the slot phase is allowed to return entities only. This is not evidence that predecessor conditioning changed.

The historical `scripts/slurp_kc_s1_read.py::project_joined` supplies the sealed closed-list predecessor's scenario/action and takes only the slot arm's parsed entities. The shared phase runtime preserves raw last-phase responses and did not register a joined read-side output in the recovered configuration. Restore this existing rule uniformly for control, speech and form twin; do not tune it using results.

## Bounded work

Extract the historical pure join into a reusable shared implementation. Prove exact historical output bytes and statistics on synthetic valid, malformed and extra-label cases. Reject duplicate, missing and extra sample IDs, and preserve both inputs.

Bind each existing finalized parent manifest and the identical sealed closed-list predecessor from the parent's actual frozen baseline. Verify source hashes. Write a new derived read artifact outside Git with both source hashes, implementation identity, output hash and explicit zero generation/scoring cost. Do not replace any manifest output, response, trace or official score. Apply the join to all 1,000 rows of all three arms.

Assert every derived intent is identical to the same predecessor and to the other arms. Assert every entity sequence is unchanged from the as-sealed response. Retain the already-computed entity-side contrasts; this diagnostic cannot alter them and must not rerun the official evaluator or bootstrap. Do not call this derived read a new model run, independent replication, or live complete-system result. Preserve missing/invalid response counts and the control's one 256-token length stop.

Complete the component verdict only after this protection evidence is reviewed. Live intent-to-slots assembly and complete-system performance/cost remain G6 work. No inference, tokenizer, encoder or official scorer contact is authorized by this restoration.
