# A2T-ORG-1: domain-grouped tool registry (knowledge organization, zero rollouts), v1 preregistration (DRAFT, not registered)

Status: drafted 2026-09-05 after the owner confirmed the mechanism order (A2T-ORG-1 first). Not registered, not
authorized to fly until the owner's GO is recorded in section 8.

## 1. Question and hypothesis

Every official-population verdict of 2026-09-04 placed the Audio2Tool gap in one stratum, smart_home, where 889 of
908 misses name another real registry tool. The registry evidence splits those misses into two classes:

- cross-domain functional twins, where the missing cue is the domain of the device (a smart_home lighting request
  answered with `setAmbientLighting` from smart_car; `setFanMode` answered with smart_car's `setFanSpeed`);
- same-domain functional twins whose descriptions are semantically equivalent (`rebootDevice` / `restartDevice`,
  `setSecurityMode` / `armSecuritySystem`, `activateScene` / `activateRoutine`, `getApplianceState` /
  `getApplianceStatus`, `setLighting` / `setLightState`).

The official protocol renders the registry with `format_tools_compact`: one line `- {signature}: {description}`
per tool, sorted by name. It drops the registry's `domain` and `category` columns entirely; only 11 of the 53
smart_home descriptions and 28 of the 86 smart_car descriptions mention a domain word, so the model is never told
which domain a tool belongs to. The registry carries 86 smart_car, 53 smart_home and 13 wearables tools, and the
per-domain accuracy ranking (wearables 93, smart_car 92, smart_home 56 on tier 1) follows the count of confusable
neighbours.

Hypothesis H1: supplying the domain structure of the registry, with no other change, recovers a measurable share
of the cross-domain twin misses and therefore of the smart_home gap. The same-domain twins are expected NOT to
move; that residual is the target of A2T-ORG-2 (contrast-note rollouts).

This is a knowledge-organization (ORG) mechanism in the study's terms: the knowledge is the registry's own
structure, supplied at zero contact cost, no retrieval, no second contact.

## 2. The manipulation, taken from the released code, not invented

The released code (`audio2tool/Audio2Tool` @ b9d5383c, `audio_benchmark/utils/tools_schema.py`) ships a second
renderer beside the compact one, `format_tools_for_prompt(tools, include_constraints)`: tools grouped by domain
(domains sorted; header `## {DOMAIN}` with underscores replaced by spaces and upper-cased), within each domain
sorted by name, each tool as `### {signature}` on its own line followed by `{description}`, and, when
`include_constraints` is true, a `Constraints: {argument_constraints}` line. No system in Table 3 was run with it
(the HF adapter hard-codes the compact form), so it is a legitimate organization of the same registry rather
than a claim about the paper's protocol.

Arm ORG-1 renders the tool block with `format_tools_for_prompt(..., include_constraints=False)`. One factor is
varied: the grouping and headers. Constraints are deliberately withheld (they add argument knowledge that would
confound the domain-cue question; they are reserved for a later cell if the owner wants them). Everything else
is byte-identical to the sealed official-protocol cells: the system prompt sentence, the `\n\n## Available
Tools:\n` wrapper, the user turn (audio, then "Convert this voice command to a tool call."), greedy decoding,
`max_tokens` 256, raw audio through the bf16 mmproj, build 04ccc72a, Q4_K_M.

Implementation: a registered instruction fill `audio2tool-registry-grouped` in `core/instructions.py` beside
`audio2tool-registry-compact`, whose renderer is a port of the released function with a unit test asserting
byte equality against the official function imported from the pinned clone
(`SPEECHRL_DATA_DIR/repos/audio2tool`, skipped with a stated reason where the clone is absent); a probe template
`configs/probes/r1_audio2tool_official_grouped.txt`; a baseline fragment `configs/baseline/a2t-org1-domain-grouped.json`
(`arm: bare-core`, scorers `["a2t-toolcall-official", "a2t-toolcall-v2", "a2t-toolcall", "cost"]`,
`task_instruction_template_active: true`). No new module under `rails/probes/`, no controller subclass.

## 3. Population and pairing

The three sealed official-population rosters, unchanged: tier 1 (500 queries, `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1`),
tiers 2/5/8 (1,500, `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1`), tiers 3/4/6/7 (2,000,
`SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1`): 4,000 rows, first successful speaker per query (tier 7 = first user
turn), all already exposed. One roster, one split identity hash, one run id; strata = tier and domain. Every row
is paired with its sealed official-protocol output; nothing is re-flown on the baseline side (greedy decoding is
not bitwise reproducible across batch shapes on this runtime, so the sealed bytes are the only comparator).

## 4. Pre-contact prerequisites

1. Fill, template, fragment and the byte-equality test committed; `engineering_base_check` passes.
2. Prompt-fit receipt (zero generated tokens): the grouped block is longer than the compact one (headers,
   `###` lines, blank lines); record its token count and re-derive `-np` by the section 8.1 rule against the
   longest wav of the roster (the 654-s synthesis-defect rows are kept for pairing fidelity, as before).
3. Wire check on a clean committed tree; 4-row smoke with its own ledger row; ledger row for the flight before
   the first contact.

## 5. Budget (ExecutionPlan)

| field | planned | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 4,008 | 4,200 | 4,000 rows + 8 canaries |
| speech audio seconds | the three rosters' measured sum (1,668.9 + 9,784.3 + 11,964.8 = 23,418.0) | 24,600 | one pass |
| GPU hours | 1.2 | 2.0 | 0.78 to 0.83 s per call at -np 3 on the same rows |
| paid API spend | 0 | 0 | |

## 6. Analysis and decision (fixed before takeoff)

Primary: pooled official tool accuracy, ORG-1 minus baseline, paired over 4,000 rows (`analysis.paired`:
saves / harms / ties, exact sign test, 10,000 replicates stratified by tier, seed 20260903, CI90); reported on the
natural mixture and on equal-domain weighting, per tier and per domain, with the paper column beside every tier.
Secondary: exact match and param F1 (macro, micro) and `a2t-toolcall-v2`; parse rate; the confusion-pair table
before and after (counts of the named cross-domain and same-domain twins); the cross-domain share of the gain =
(baseline cross-domain-twin misses corrected) / (all misses corrected).

- ADMITTED: the pooled CI90 lower bound is above 0 AND the per-domain table shows the gain concentrated on
  smart_home cross-domain twins. ORG-1 becomes the study's first admitted knowledge-organization mechanism on
  Audio2Tool, and A2T-ORG-2 is registered on top of it (same roster, ORG-1 as its comparator).
- NULL: the CI90 includes 0. Domain structure alone is not the lever; A2T-ORG-2 is registered against the
  official-protocol baseline instead, and the domain cue is folded into its notes rather than tested again.
- HARMFUL: the CI90 upper bound is below 0. ORG-1 is dropped and the reason (longer prompt, header tokens)
  is recorded before ORG-2.

No outcome changes the direct baseline: the official-protocol cell stays the comparator every mechanism is paired
against. Gates are relative to the published ceiling, never above it.

## 7. What this preregistration does not authorize

No test contact; no fresh roster; no rollouts; no constraints line; no retrieval or second contact; no change to
the direct baseline; no Q8_0; no superiority or Stage-3 claim. At most one recovery re-registration.

## 8. Owner decision and execution log

Pending.
