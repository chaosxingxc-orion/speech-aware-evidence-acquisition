# A2T-ORG-1: domain-grouped tool registry (knowledge organization, zero rollouts), v1 preregistration (REGISTERED)

Status: drafted 2026-09-05 after the owner confirmed the mechanism order (A2T-ORG-1 first); REGISTERED the same
day on the owner's GO, recorded verbatim in section 8. The exposure rows for the prompt fit, the smoke and the
flight were written before the first contact.

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

### 8.1 Owner decision, verbatim

> Owner GO 2026-09-05: fly A2T-ORG-1 as preregistered; new agent; no other change.

### 8.2 What "as preregistered" resolved to

Nothing in sections 1-7 was changed to fly this. Three facts were MEASURED rather than assumed and
are recorded here because section 4 required them:

1. **The union roster is 4,000 rows and needs one D1 supplement, not none.** Section 3 said "all
   already exposed", which is true of the model contact: every row was contacted once on 2026-09-04.
   It is not true of the D1 identity closure. `contracts.gate_media_identity` reads the immutable
   `docs/receipts/artifacts/d1-identity.json` plus AT MOST ONE additive supplement, and the three
   sealed official-population supplements are siblings parented to that same base rather than a
   chain. So the union needs its own union supplement:
   `docs/receipts/artifacts/d1-a2t-org1-union-4000.json`, 3,932 entries (495 + 1,455 + 1,982), with
   the other 68 ids verified against the base artifact and skipped because the gate refuses a
   supplement entry that duplicates a base sample. No new probe-sample receipt was needed: all 4,000
   ids already resolve inside `data.audio2tool`'s frozen-receipt universe.
2. **The grouped registry is 347 characters longer than the compact one**, not the "much longer"
   section 4 item 2 anticipated: 16,490 chars against 16,143 for the whole system message. The
   `### ` prefix costs two characters per tool over `- `, the newline between signature and
   description saves one over `: `, and the blank line before each entry adds one; three domain
   headers do the rest.
3. **The serving geometry is unchanged at `-c 49152 -np 2`.** The union carries FOUR of the
   release's 654-second synthesis defects (`tier1_direct:003943`, `tier3_multi_intent:003555`,
   `tier6_correction:003151`, `tier7_multiturn:001033`) and no other row over 56 s, so the worst
   row costs 8,515 speech tokens under the one-second window rule and the section 8.1 derivation
   rule of `docs/readiness/2026-08-25-a2t-generality-campaign-plan.md` (largest slot count whose
   per-slot window still clears worst-required plus the 8,192-token reserve, holding `-c` at the
   49,152 this GPU is proven to serve on the raw path) lands on 2 slots exactly as it did for
   `T1-official-pop-500` and `T3467-official-pop-2000`. The prompt-fit receipt re-derives it from
   the measured token count before any generation.

### 8.3 Registered identities

| item | value |
|---|---|
| roster | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-roster/flight-roster-receipt.json` |
| roster SHA-256 | `e5a81b71e1253ff866262991f79d132b89f4bfb47e7c8a0c0cf0aa04857b8736` |
| split identity hash (probe-receipt convention) | `c0c1e7ccc0a9d923e51e86be11c4aedb760a2b91c8ab166305a6877c64496ad4` |
| flight split identity hash (FlightRuntime convention) | `ed8946ddf99f9e898af1c8cb94932c538165cd591c2cff3021321749e52103d6` |
| D1 media supplement | `docs/receipts/artifacts/d1-a2t-org1-union-4000.json` (SHA-256 `b94439af4f51d648d8969f6ff876d3a24ccd49836bac011dc8f2bb0c9364ec59`, 3,932 entries) |
| dataset fragment | `configs/dataset/audio2tool-org1-union-4000.json` |
| baseline fragment | `configs/baseline/a2t-org1-domain-grouped.json` |
| probe template | `configs/probes/r1_audio2tool_official_grouped.txt` (same bytes as `r1_audio2tool_official.txt`) |
| instruction fill | `audio2tool-registry-grouped` (`data.audio2tool_tools.render_registry_grouped`) |
| experiment fragment | `configs/experiment/a2t-org1-domain-grouped-4000-v1.json` |
| smoke fragment | `configs/experiment/a2t-org1-domain-grouped-4000-smoke-v1.json` |
| model fragment | `configs/model/q4km-featcache-a2t-official-np2-04ccc72a.json` (unchanged) |
| rendered system message | 16,490 chars, SHA-256 `a0b5dd77cceac57d726e43a06b06a4c6699f21ec22973b0ba9ec6e8409879495` |

### 8.4 Exposure rows, all written before the first contact

| run id | profile | calls | speech s | GPU h |
|---|---|---:|---:|---:|
| `SAEA-A2T-ORG1-DOMAIN-GROUPED-PROMPT-FIT-V1` | `bounded-discovery-probe` | 2 | 2 | 0.3 |
| `SAEA-A2T-ORG1-DOMAIN-GROUPED-SMOKE-V1` | `bounded-discovery-probe` | 20 | 2,100 | 0.2 |
| `SAEA-A2T-ORG1-DOMAIN-GROUPED-V1` | `baseline-reproduction` | 4,200 | 24,600 | 2.0 |

### 8.5 Execution log

Filled in by the verdict:
`docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-verdict.md`.
