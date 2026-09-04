# Slice S1 -- zero-contact scorer-v2 study verdict (2026-09-03)

Model-free re-scoring of three already-sealed Audio2Tool discovery-split outputs sets (A0 direct
baseline n=400; semantic-AgentLoop-104, 5 arms; select-fill-AgentLoop-104, 4 arms -- 1,336 rows
total) against the unchanged v1 scorer (`reproduction.toolcall_scoring`, `a2t-scorer-v1`) and
unchanged v1 gold parser (`reproduction.toolcall_gold`, `a2t-gold-v1`). Zero model, GPU, embedding,
or network contact. Full tables, the failure taxonomy, and the candidate-rule table live in
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-zero-contact-study/README.md`;
the machine-readable output is `summary.json`/`per_row.jsonl` in the same directory. Suite:
`src/speech_aware_evidence_acquisition/analysis/a2t_scorer_v2_study.py`.

## 1. Why this study ran

The paper (arXiv:2604.22821, Table 3) reports, for the same frozen Qwen3-Omni-30B core, Tier 1
tool accuracy 92.4 with EM 92.4 (Tier 1 is argument-free, so EM equals tool accuracy). This repo's
frozen A0 read (n=400) scores Tier 1 tool acc 58.0 / EM 12.0 -- a ~80pp EM gap where the paper
shows none. The paper defines Tool Accuracy as an ORDERED sequence match and EM as exact match
after "deterministic normalization"; the repo's v1 scorer is order-insensitive and has no
default/omission normalization. Before any scorer-v2 decision, this study measured how much of the
gap is scorer semantics versus genuine model error.

## 2. Identity check (Step 1)

All 10 located arms reproduce their sealed target tool_accuracy and exact_match to 4 decimals under
the unchanged v1 functions:

- A0 (400 rows): tool_acc 0.5425, EM 0.2425 -- matches `docs/readiness/2026-08-18-pa2t-a0-verdict.md`
  section 2 overall AND every one of its 8 per-tier rows.
- semantic-AgentLoop-104, all 5 arms -- matches `postseal-result-summary.json`'s `arms` block
  exactly (e.g. `direct_m0` EM 0.2404, `transcript_top16_use` EM 0.2596).
- select-fill-AgentLoop-104, all 4 arms -- matches `result-summary.json`'s `arms` block exactly
  (e.g. `DIRECT_M0` EM 0.1731, `SELECT_THEN_FILL` EM 0.2500).

Zero mismatches, zero arms skipped. This study's own independently-computed paired saves/harms/
ties under V1 also reproduce the already-sealed bootstrap paired-contrast wins/losses/ties in both
September flights' own postseal analyses exactly (see the README's "cross-check" note) -- two
independent confirmations that the re-scoring pipeline agrees with the flights' own official
scoring before any candidate rule is applied.

## 3. Failure taxonomy (Step 2) -- headline

Over A0's 303 v1-failing rows (400 - 97 exact): `TOOL_SET_WRONG` 142 (46.9%, unfixable by any
argument-level scorer change), `EXTRA_KEYS_NONDEFAULT` 39 (12.9%), `VALUE_WRONG` 38 (12.5%),
`PARSE_FAIL` 24 (7.9%), `EXTRA_KEYS_DEFAULT_ONLY` 26 (8.6%), `EMPTY` 17 (5.6%), `MIXED` 12 (4.0%),
`TOOL_ORDER_ONLY` 3 (1.0%), `MISSING_KEYS_ONLY` 2 (0.7%), `CASE_OR_TYPE_ONLY` 0. Full tier x
category tables (A0 and both September flights) are in the README.

Tier 1 specifically: 44/50 rows fail under v1. 20 (45%) are genuine tool-selection failures
(`TOOL_SET_WRONG`) plus 1 `EMPTY`; 23 (52%) are extra-key issues, of which 14 carry ONLY
registry-default-valued extra keys and 9 carry at least one non-default extra key. Tier 1 has zero
`TOOL_ORDER_ONLY` and zero `CASE_OR_TYPE_ONLY` rows.

## 4. Candidate v2 semantics (Step 3) -- verdict

**Adopt V2e = V2a (ordered tool accuracy, matching the paper's own wording) + V2b (drop predicted
extra keys whose value equals the tool's registry default) + V2d (numeric-string/boolean-string
type coercion) as `a2t-scorer-v2`.** Every component is a semantics correction, never a lenience
that could hide a real model error.

**Reject V2c** (forgive every extra key regardless of default-ness): `EXTRA_KEYS_NONDEFAULT` is a
real, substantial category (39/303 A0 v1-failures, present in every September arm too); V2c would
silently score every one of those as exact.

Effect sizes:

- A0 Tier 1 EM: V1 12.00 -> V2b/V2d/V2e **40.00 (+28.00pp)**, exactly the 14 `EXTRA_KEYS_DEFAULT_ONLY`
  rows. V2c reaches 58.00 (= Tier-1 tool accuracy) -- the "too lenient" outcome flagged in advance.
  Tier 1 has no `TOOL_ORDER_ONLY`/`CASE_OR_TYPE_ONLY` rows, so V2a/V2d add nothing further there.
- A0 overall (400 rows): V1 tool_acc/EM 54.25/24.25 -> V2e 53.00/31.25 (EM **+7.00pp**, tool_acc
  **-1.25pp** -- V2a's ordered-tool-accuracy rule strictly costs 3/400 rows their tool-accuracy
  credit; it never grants any).
- **Even under V2e, A0 Tier-1 EM (40.0) is still ~52pp short of the paper's 92.4.** Scorer
  semantics close at most ~28 of the ~80pp gap; the rest is `TOOL_SET_WRONG`/`EMPTY` (genuine
  tool-selection failures) plus `EXTRA_KEYS_NONDEFAULT`/`VALUE_WRONG` (genuine argument errors) --
  none of which any defensible scorer-semantics change should paper over.

## 5. September paired-conclusion check

- **select-fill-104**: all three treatment arms stay net-positive (saves > harms) over DIRECT_M0
  under both V1 and V2e -- no sign flips; the sealed "not promoted" call is unaffected by this
  scorer question.
- **semantic-104**: `transcript_top16_use` and `same_stratum_shuffled_fused_use` keep their V1
  direction under V2e (net +2->+8 and -21->-27 respectively). **`model_query_top16_use` (net
  -1 -> +3) and `rrf_fused_top16_use` (net 0 -> +6) flip from "no advantage/net harm" under V1 to
  "net save" under V2e.** Both are small-N flips (n=104) and no significance test was rerun here --
  this is a directional finding for the NEXT semantic-AgentLoop iteration's scoring choice, not a
  reopening of the sealed promotion decision.

## 6. Recommendation

Adopt V2e (V2a+V2b+V2d) as the `a2t-scorer-v2` semantics for any future re-read or new flight that
wants a paper-comparable EM. Do not adopt V2c. Do not read V2e's Tier-1 EM improvement as closing
most of the v1-vs-paper gap -- it closes the scorer-artifact slice only; the dominant residual is
genuine tool-selection and argument-value performance, per the taxonomy above. Full evidence:
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-zero-contact-study/`.
