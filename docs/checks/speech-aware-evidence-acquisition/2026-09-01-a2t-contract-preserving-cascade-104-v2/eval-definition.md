# Frozen evaluation definition

Experiment: `SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2`.
Status: design and cohort identity frozen before implementation or model contact. Receipt
`docs/receipts/a2t/A2T-CPV2-104.json` has SHA-256
`8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783`, split identity
`a0acb1672aa1d65517f050418c530cebce9946328d030f41af958ff1a946d42c`, and run identity
`401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1`.

## Evaluation questions

1. Does preserving the original exact Audio2Tool output envelope restore structurally valid USE?
2. Does self-transcript retrieval add gold-tool coverage over same-flight M0?
3. Does matched evidence outperform same-tier shuffled evidence under the identical output contract?
4. Does the full AgentLoop improve exact match over the single-call comparator?
5. Does cross-fitted training-free control improve beyond always-use while spending fewer final contacts?
6. Do four outer scorer workers reduce wall time without altering any full-manifest official metric?

## Required precontact evals

| ID | Capability or regression | Required behavior |
|---|---|---|
| E01 | Cohort construction | Reproduce 8×13 items from the parent receipt, prove query-block disjointness from A2T-G1-104, and reject any identity, media, duration, parent, or exclusion hash drift. |
| E02 | M0 byte preservation | The direct arm is byte-identical to the existing Audio2Tool prompt, including the exact final name/arguments example. |
| E03 | USE contract placement | Auxiliary state and evidence occur before the exact M0 output sentence, which remains the final system text; matched and shuffled contracts differ only in evidence provenance/content. |
| E04 | OBS isolation | OBS contains original speech and the frozen English ASR-only instruction but no registry, output schema, evidence, M0, gold, reference, score, or future turn. |
| E05 | OBS barrier | No USE call can start unless all 104 OBS rows seal and every frozen label-free liveness clause passes. |
| E06 | Structural canary | Only the fixed 8×2 canaries run first; the gate reads structure and frozen registry membership only, rejects fences/prefixes/extra keys/empty arrays/non-object arguments, and failure prevents all remaining USE, gold, and scorer access. |
| E07 | Canary reuse | Passing canary responses occupy their ordinary matched/shuffled rows and are never contacted again. |
| E08 | Retrieval and budgets | Deterministic BM25, 5/6/5 limits, own-state preservation, and tier-local total derangement reproduce exactly. |
| E09 | Runtime state safety | State contains only the five frozen structural buckets and none of the forbidden literal or outcome fields. |
| E10 | Grouped cross-fitting | Whole query blocks never cross folds; each decision reads other-fold returns only; support-four/saves-two/harms-zero and default-stop are exact. |
| E11 | Exact resend | Sixteen source payload hashes equal their matched request hashes while attempt and response identities remain fresh. |
| E12 | Contact accounting | M0/OBS/matched/shuffled/resend cannot exceed 104/104/104/104/16, canaries count inside USE, and cumulative use cannot exceed 440 or 2,700 speech seconds. |
| E13 | Complete manifests | M0, matched, shuffled, resend, and policy each contain exactly the frozen 104 unique ids; no missing output is invented. |
| E14 | Outer parallel wave | Wave 1 has four distinct complete manifests and four workers; one official process handles each whole manifest; shards and shard-score averaging are rejected. |
| E15 | Dependency wave | Policy construction cannot start before wave-1 verification and wave 2 scores exactly one complete policy manifest in default score mode without an unsupported flag. |
| E16 | Promotion conjunction | No report passes unless every liveness, structural, information, matched-control, agent, training-free-increment, fold, secondary-metric, resend, and state gate passes. |
| E17 | Terminal scope | Failure authorizes no support or scale; success authorizes only a separate support proposal and never test, approximately-1,000 execution, Stage-3, or paper-scale work. |

Tests must be written before implementation and targeted branch coverage must be at least 80%.
Gold and scorer remain closed until every permitted model response and complete prediction manifest
has sealed. A protocol-changing repair requires a new prospective registration and attempt identity.
