# Native structured-action fixed-eight mechanism analysis

## Decision

The mechanism screen fails. Both strict cells parse all eight rows, but syntax
parsing is not complete hard validity: `HANDBOOK_STRICT_ACTION` repeats a call
on `tier3_multi_intent:002490`, so it is only 7/8 hard-valid even though all
eight rows use legal argument-key sets. Neither strict cell approaches the
registered task-quality thresholds, and the exact per-row oracle reaches only
3/8 exact, 6/8 tool correctness, and 0.714286 slot micro F1.

Do not promote this candidate into the OpenJiuwen engineering baseline. Keep
policy fitting, VW, scale, confirmation, test, Stage-3, and paper-scale work
closed while a new canonical-ground discovery cell is built.

## Whole-cell results

Task metrics are from the unchanged official `a2t-toolcall` scorer. Hard
validity and legal-key coverage are frozen label-free diagnostics.

| Cell | Exact | Tool | Slot P / R / F1 | Parse | Hard-valid | Legal keys |
|---|---:|---:|---:|---:|---:|---:|
| `REGISTRY_NO_SCHEMA` (M0) | 0/8 | 0/8 | 0.000 / 0.000 / 0.000 | 0/8 | 0/8 | 0/8 |
| `REGISTRY_STRICT_ACTION` | 2/8 | 4/8 | 0.300 / 0.375 / 0.333 | 8/8 | 8/8 | 8/8 |
| `HANDBOOK_NO_SCHEMA` | 1/8 | 5/8 | 0.364 / 0.500 / 0.421 | 8/8 | 7/8 | 7/8 |
| `HANDBOOK_STRICT_ACTION` | 1/8 | 3/8 | 0.200 / 0.250 / 0.222 | 8/8 | 7/8 | 8/8 |
| Frozen four-cell oracle | 3/8 | 6/8 | 0.833 / 0.625 / 0.714 | 7/8 | 7/8 | 7/8 |

The matched exact saves/harms/ties are 2/0/6 for registry strict versus
registry no-schema, and 1/1/6 for handbook strict versus handbook no-schema.
The best observed cell is `REGISTRY_STRICT_ACTION`; relative to M0 it gains
2 exact rows and 4 tool-correct rows, with 2 exact saves and no harms.

## Per-tier outcomes

Each entry is exact/tool/row-slot-F1. There is one frozen row per tier.

| Tier | M0 | Registry strict | Handbook no-schema | Handbook strict | Oracle source |
|---|---:|---:|---:|---:|---|
| Direct | 0/0/0.000 | 0/1/0.000 | 0/0/0.000 | 0/1/0.000 | Registry strict |
| Parametric | 0/0/0.000 | 0/0/0.000 | 0/1/0.667 | 0/0/0.000 | Handbook no-schema |
| Multi-intent | 0/0/0.000 | 0/0/1.000 | 0/1/0.500 | 0/0/0.250 | Registry strict |
| Implicit | 0/0/0.000 | 0/0/0.000 | 1/1/1.000 | 0/0/0.000 | Handbook no-schema |
| Needle | 0/0/0.000 | 0/1/0.667 | 0/1/0.667 | 0/1/0.667 | Registry strict |
| Correction | 0/0/0.000 | 1/1/0.000 | 0/1/0.000 | 1/1/0.000 | Registry strict |
| Multiturn | 0/0/0.000 | 1/1/1.000 | 0/0/0.000 | 0/0/0.000 | Registry strict |
| Intent blending | 0/0/0.000 | 0/0/0.000 | 0/0/0.000 | 0/0/0.000 | M0 by frozen-order tie |

The no-schema handbook hard-valid failure is an unknown argument key on the
correction row. Its distinct legal-key failure is on the multi-intent row.
The handbook strict hard-valid failure is the duplicated multi-intent call.
The oracle's intent-blending row is unparsable because all four rows tied at
zero and the frozen comparator selected M0 by cell order.

## Frozen 2x2 effects

Effects use the order exact rate, tool rate, slot micro F1, parse rate,
hard-valid rate, and legal-key rate.

- Knowledge main effect, mean handbook minus mean registry:
  `0.000, +0.250, +0.154971, +0.500, +0.375, +0.4375`.
- Structured-action main effect, mean strict minus mean no-schema:
  `+0.125, +0.125, +0.067251, +0.500, +0.500, +0.5625`.
- Interaction, handbook strict-minus-no-schema minus registry
  strict-minus-no-schema:
  `-0.250, -0.750, -0.532164, -1.000, -1.000, -0.875`.

The negative interaction is decisive: structured action fixes registry
syntax, but adding it to the handbook does not increase exact correctness and
reduces tool accuracy and slot F1.

## Oracle and gates

The frozen oracle selects five registry-strict rows, two handbook-no-schema
rows, no handbook-strict rows, and one M0 row. It passes only the maximum
one-row gap from the best strict cell: 3 minus 2 equals 1.

- Both strict cells parse 8/8: pass.
- Both strict cells are completely hard-valid 8/8: fail.
- Both strict cells have legal key-set coverage 8/8: pass.
- Oracle is 8/8 exact, 8/8 tool, and at least 0.90 slot F1: fail.
- At least one strict cell meets 7/8 exact, 8/8 tool, at least 0.90 slot F1,
  at least three saves, and no harms against its matched parent: fail.
- Oracle-to-best-strict exact gap is at most one: pass.
- Frozen strict-cell tie rule: not invoked because no strict cell qualifies.

The registered outcome is `failure`, with no selected strict cell.

## Next research move

Do not enlarge the global prompt or tune a candidate cutoff on these eight
rows. The 54,881-byte handbook and 91,407-byte, 338-branch global schema are
already broad enough to contain legal public actions, yet the frozen core does
not reliably select and compose them. The next cell must make the same public
knowledge executable:

1. Build canonical execution cards from the pinned registry, G4 semantic
   contrasts, and G5 exhaustive family contracts. Each card must state exact
   operation names, choose/avoid sibling distinctions, legal argument
   skeletons including `{}`, exact enum casing, omission rules, correction and
   ordering rules, and multi-intent cardinality. It must contain no evaluation
   utterance, label, observed output, or concrete task value.
2. Use OpenJiuwen to trace OBS, ORG, SUPPLY, and USE separately. Supply the
   complete compatible family union and compile a family-local strict schema;
   do not expose the global 338-way branch at the final USE step. The existing
   G5/G6 planner is not accepted as-is because its earlier discovery result did
   not cover the correct family reliably; only its public contract corpus is
   reused.
3. Run a new identity-only, disjoint fixed-eight screen before any scale-up.
   Require 8/8 parse, hard validity, legal keys, tool correctness, and oracle
   exactness, slot micro F1 at least 0.90, one treatment at least 7/8 exact with
   no M0 harms, and zero repair/retry contacts. A failure expands the
   representation again; a pass opens a separate OpenJiuwen information-gain
   experiment, not VW directly.

Only after a fixed AgentLoop produces held-out information gain over one-shot
does the upstream `vowpalwabbit==9.11.2` `cb_explore_adf` controller open on
approximately 100 rows. The repository will not implement its own learner.

## Audit boundary

The four cell scores are four whole-manifest jobs under outer parallelism;
there is no dataset sharding or shard-metric averaging. They completed in
9.600 seconds wall time versus 30.280 summed job-seconds, a 3.154-times
effective speedup. The oracle derivative reuses sealed response bytes and
records zero new model contacts. One initial
oracle scoring process stopped at the E0 frozen-source preflight before the
scorer ran because disposable Python bytecode caches existed. That failed
preflight record was preserved, the caches were removed, and the unchanged
oracle manifest was officially scored effectively once.

The authoritative hashes, exact external paths, and full gate record are in
`mechanism-result.json`. The focused post-seal suite passed all 16 tests. The
exposure ledger was not edited.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same four sealed cell `outputs.jsonl` files (8/8 rows each, v1
identity confirmed to 4 decimals overall for every cell) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).
The derived post-score four-cell oracle is not re-scored (a frozen selector over these four cells,
not an independent model contact).

| Cell | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| REGISTRY_NO_SCHEMA (M0) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| REGISTRY_STRICT_ACTION | 0.2500 | 0.5000 | 0.3750 | 0.5000 | 0.5000 | 0.4615 | 0.3333 | 1.0000 |
| HANDBOOK_NO_SCHEMA | 0.1250 | 0.6250 | 0.1250 | 0.6250 | 0.6250 | 0.4706 | 0.4211 | 1.0000 |
| HANDBOOK_STRICT_ACTION | 0.1250 | 0.3750 | 0.2500 | 0.3750 | 0.3750 | 0.2353 | 0.2222 | 1.0000 |

Paired contrasts, matching this doc's own two within-factorial comparisons (v1 and v2, CI90, 10,000
replicates, tier-stratified over n=8):

| pairing | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| REGISTRY_STRICT_ACTION vs REGISTRY_NO_SCHEMA | v1 exact | +0.2500 | 2 | 0 | 6 | [0.2500, 0.2500] |
| REGISTRY_STRICT_ACTION vs REGISTRY_NO_SCHEMA | v2 exact | +0.3750 | 3 | 0 | 5 | [0.3750, 0.3750] |
| REGISTRY_STRICT_ACTION vs REGISTRY_NO_SCHEMA | v1 tool | +0.5000 | 4 | 0 | 4 | [0.5000, 0.5000] |
| HANDBOOK_STRICT_ACTION vs HANDBOOK_NO_SCHEMA | v1 exact | +0.0000 | 1 | 1 | 6 | [0.0000, 0.0000] |
| HANDBOOK_STRICT_ACTION vs HANDBOOK_NO_SCHEMA | v2 exact | +0.1250 | 2 | 1 | 5 | [0.1250, 0.1250] |
| HANDBOOK_STRICT_ACTION vs HANDBOOK_NO_SCHEMA | v1 tool | -0.2500 | 1 | 3 | 4 | [-0.2500, -0.2500] |

(n=8 CI90s here are degenerate point intervals under this stratified bootstrap and should be read
descriptively, not as evidence of significance.) The strict-action format's benefit over no-schema on
the registry axis strengthens under v2 (saves/exact both grow); on the handbook axis, exact match
ties under v1 (saves=harms=1) but shows a positive v2 net (saves 2 vs harms 1) while tool accuracy
stays negative for strict-action either way -- consistent with this doc's own reading that the
strict-schema format trades tool accuracy for higher exact-match precision once a call is attempted.
This is a mechanism diagnostic, not a promotion decision; no gate outcome in `mechanism-result.json`
is reopened by this correction.
