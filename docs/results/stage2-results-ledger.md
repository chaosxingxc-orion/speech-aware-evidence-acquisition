# Stage-2 results ledger

One row per cell, grouped by carrier and by layer. Owner Decision 14-Q, 2026-09-09. Model-free: this document was assembled with zero model, GPU, tool, embedder, tokenizer, network and audio-decode contacts, from existing verdict notes and receipts, with the owner recovery adding an operational metadata snapshot.

**Scope.** Every cell decided by a verdict note dated 2026-09-04 to 2026-09-09, plus the four entries of docs/receipts/harness-admission.json and registered cells whose scientific decisions remain pending; the 2026-09-09 owner recovery adds operational completion for all seven KV flights without inspecting their score values. Machine-readable twin: `docs/results/stage2-results-ledger.json`. Checked by `scripts/checks/results_ledger_check.py`.

## Current continuation status — source-bound 2026-09-10/11 updates

This table is the current routing layer. The 53 detailed rows and their counts below are an immutable **2026-09-09 historical snapshot**. Their `PENDING`, `not measured`, `verdict note: none`, and `named next step` fields describe what was known then and are superseded where this table names the same historical cell. Current entries do not retroactively alter those decisions, count deterministic derivatives as independent flights, or turn preparation run IDs into generation runs. Every source hash is the SHA-256 of the cited repository file at this ledger revision.

| Current entry | Current status | Registered generation run(s) | Meaning | Authoritative repository source and SHA-256 | Superseded historical row |
|---|---|---|---|---|---|
| SLURP-SYSTEM-MEMORY-BATCH002-V1 | **CONSTRUCTION_COMPLETE_NO_DEMONSTRATED_MEMORY_GAIN** | Six original and two recovery actors specified in read-registration-v4 | Four distinct TRAIN inputs; memory selected and textually used, no observed downstream task correction. No efficacy claim; no new GPU dispatch. | docs/results/2026-09-26-system-memory-batch002-consumption-verdict.md / 1204fca9d3e57a43cbe75a9c453a7e2484d51eb461345187476074803a9d23a2 | None; construction diagnostic |
| A2T-NATIVE-ROLE-CANDIDATE-ATTRIBUTION-UNION4000-V1 | **CANDIDATE_ATTRIBUTION_COMPLETE_NO_NEW_GENERATION** | Same finalized direct and native UNION4000 runs; zero new generation | Complete source-bound primary-target candidate attribution: 2882/4000 included (72.05%); 1117 observed misses and one unavailable Perception. All8883 unique candidate observations map to parameter values. Candidate-present rows gain65 correct primary tools and202 exact calls; absent rows lose209 tools and40 exact calls. The original failed tool guard remains unchanged. No new generation or scoring; owner GPU hold active. | docs/results/2026-09-15-a2t-native-role-candidate-attribution-v1.json; SHA-256 6126deb61a143361e5331eb422571b10fde3aa65d0e5ace41e19fc3727bad6c7 | None; supplements the preserved primary decision |
| SLURP-FIXED-WHISPER-EVIDENCE-V1 | **EFFECTIVENESS_NOT_ESTABLISHED** | SAEA-SLURP-SPEECH-OBSERVATION-CONTROL-V1; SAEA-SLURP-SPEECH-OBSERVATION-WHISPER-TRANSPORT-RECOVERY-V1 | Both complete 1000-row three-stage arms finalized and first-scored. NEW500 micro +0.833007 pp and intent -0.800000 pp both unresolved; secondary full-roster intent negative. Fixed supply not adopted as demonstrated improvement; registered component diagnosis pending, no automatic new mechanism. | docs/readiness/2026-09-12-slurp-fixed-whisper-result-v1.md / 6c486d49619ecbc6172d461f067c9edb04ed0b55456237b1a6b0bb540313a656 | New evidence-availability comparison; historical decisions unchanged |
| A2T-NATIVE-SYSTEM-RECOVERY-V1 | **SYSTEM_NOT_ADMITTED_KNOWLEDGE_NOT_ESTABLISHED** | SAEA-A2T-NATIVE-SYSTEM-RECOVERY-DIRECT-V1; SAEA-A2T-NATIVE-SYSTEM-RECOVERY-STAGE-CONTROL-V1; SAEA-A2T-NATIVE-SYSTEM-RECOVERY-KNOWLEDGE-V1 | All FINALIZED and first-scored; both primary declarations fail. Full strata and component limitations retained; no additional generation. | docs/readiness/2026-09-12-a2t-native-system-final-result-v1.md / 166511373efe0eb1ed26666139551b4723150eedb2915634f1ae40417a3f0758 | New native system comparison; historical decisions unchanged |
| SLURP-ROLE-COVERAGE-MATCHED-V1 | **DO_NOT_ADOPT_INTENT_NEGATIVE_ENTITY_UNRESOLVED** | `SAEA-SLURP-ROLE-COVERAGE-CONTROL-V1`, `SAEA-SLURP-ROLE-COVERAGE-TREATMENT-V1` | Both FINALIZED; NEW500 intent -2.200pp with negative CI90, micro F1 -0.541pp unresolved. Close this package; preserve the prior working baseline and live-state/provenance limitations. | `docs/readiness/2026-09-11-slurp-role-coverage-result.md` / `0195b5289fba51e1e4a2b1fe486579f11b531ede7063edb8b74628d93466d436` | New component comparison; historical decisions unchanged |
| SLURP-COMPLETE-TASK-AGENT-REPLICATION-V1 | **PRIMARY_INTENT_AND_ENTITY_POSITIVE_EXPLORATORY_WORKING_BASELINE** | `SAEA-SLURP-TASK-AGENT-DIRECT-REPLICATION-V1`, `SAEA-SLURP-TASK-AGENT-FRAME-REPLICATION-RECOVERY-V1` | Both FINALIZED; primary intent+4.200pp and micro F1+2.991pp, both CI90 positive. Retain exploratory working baseline; preserve secondary uncertainty and recovery/idle limitations. | `docs/readiness/2026-09-11-slurp-task-agent-replication-result.md` / `4ac7b30a8e46e46b33f69ec08d903329c857282d9f0cdfdcf232b14ae5940023` | New same-roster replication; old family unchanged |
| SLURP-COMPLETE-TASK-AGENT-V1 | **INTENT_SIGNAL_ENTITY_UNRESOLVED_NO_FULL_TASK_ADMISSION** | `SAEA-SLURP-TASK-AGENT-DIRECT-V1`, `SAEA-SLURP-TASK-AGENT-KNOWLEDGE-V1`, `SAEA-SLURP-TASK-AGENT-FRAME-V1` | All3 FINALIZED; compact frame has an intent signal, primary entity gain unresolved; disclose runtime/read qualifications and replicate before system lock. | `docs/readiness/2026-09-11-slurp-task-agent-result.md` / `7354e66cb93d82c86779f765fbff2ee5c9cd8925639e8e415b30d0b2c3b96920` | New live full-task family |
| SLURP-DISCRIMINATIVE-VALUES-SPAN-PAIR | **NEGATIVE_COMPONENT_NOT_SELECTED** | `SAEA-SLURP-DISCRIMINATIVE-VALUE-HISTORICAL-V1`, `SAEA-SLURP-DISCRIMINATIVE-VALUE-SPAN-V1` | NEW500 row-F1-6.0619pp; omission increases; no promotion or adaptive repeat. | `docs/readiness/2026-09-11-slurp-discriminative-values-result.md` / `3335c8c0d206bd08f416753f34078783777b4510dada6b941446615494f6c2cb` | New bounded component question |
| SLURP-KV-0-CURRENT | **HARMFUL** | `SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1` | Harmful base; retain KC-S1b. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/family-decision.json` · `0f2570f185bc6275c9aaa2e8b137b45df4383e344d6b75695d2e5068c834d01b` | SLURP-KV-0 |
| SLURP-KV-1-CURRENT | **NULL_COMPATIBLE** | `SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1` | Primary intervals span zero; no equivalence or NI claim. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/family-decision.json` · `0f2570f185bc6275c9aaa2e8b137b45df4383e344d6b75695d2e5068c834d01b` | SLURP-KV-1 |
| SLURP-KV-1-TWIN-CURRENT | **COMPARATOR_ONLY** | `SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1` | Attribution twin; no independent verdict. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md` · `8c1c4b6609aeceb08f33508c73a943cceebdbcdb58e669f6614a474bff8bdc04` | SLURP-KV-1-TWIN |
| SLURP-KV-2-CURRENT | **NOT_ADMITTED_ROTATING_TWIN_GATE_FAILED** | `SAEA-SLURP-KV2-CARDS-DEV1000-V1` | Gain over KV-0 does not pass the inherited rotating-stratum twin gate. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/family-decision.json` · `0f2570f185bc6275c9aaa2e8b137b45df4383e344d6b75695d2e5068c834d01b` | SLURP-KV-2 |
| SLURP-KV-2-TWIN-CURRENT | **COMPARATOR_ONLY** | `SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1` | Attribution twin; no independent verdict. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md` · `8c1c4b6609aeceb08f33508c73a943cceebdbcdb58e669f6614a474bff8bdc04` | SLURP-KV-2-TWIN |
| SLURP-KV-3-CURRENT | **NULL_COMPATIBLE** | `SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1` | Primary intervals span zero; no equivalence or NI claim. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/family-decision.json` · `0f2570f185bc6275c9aaa2e8b137b45df4383e344d6b75695d2e5068c834d01b` | SLURP-KV-3 |
| SLURP-KV-3-TWIN-CURRENT | **COMPARATOR_ONLY** | `SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1` | Attribution twin; no independent verdict. | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md` · `8c1c4b6609aeceb08f33508c73a943cceebdbcdb58e669f6614a474bff8bdc04` | SLURP-KV-3-TWIN |
| SLURP-KU-S3-MAX256-RECOVERY | **ADMITTED_COMPONENT** | See decision-bound source products. | Entity-side gates and joined-intent protection pass; no live-system claim. | `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s3-max256-recovery-verdict/decision.json` · `d23bc235e79438a591d9bf0afb64f709c7f58ba8c491eef48557e38398916bee` | SLURP-KU-S3 |
| SLURP-KU-S3-INDEPENDENT-REPEAT | **PASS_COMPONENT_REPEAT** | `SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1` | Passes the component-repeat criterion; no repeat-original equivalence or full-system claim. | `docs/readiness/2026-09-10-ku-s3-independent-repeat-decision.md` · `b705aec6e975d2dd58db5c017e5d20593d2ff7a3760526bfbcc3e6bb04d87283` | — |
| SLURP-KU-S4N-G2-N | **HOLD_NONINFERIORITY_FAILED** | `SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V3` | Frozen NI fails; G3 and G4 remain held. | `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s4n-g2-readout/decision.json` · `e6feda6bec2c21bc44ac582a7e4550deaebbded0aa939596e029c80d052198b5` | — |
| SLURP-KU-S4N-G2-TWIN | **COMPARATOR_COMPLETED_HELD** | `SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V3` | Completed paired comparator; no independent admission. | `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s4n-g2-readout/decision.json` · `e6feda6bec2c21bc44ac582a7e4550deaebbded0aa939596e029c80d052198b5` | — |
| E21-DR-PACKETS-UNIT-CONSTRAINED | **REJECTED** | `SAEA-E21-DR-PACKETS-UNIT-GENERATION-V2` | Fails PERSON, nonentity, and numeric protection. Correlated with unit-free. | `docs/readiness/2026-09-10-e21-dr-packets-four-delivery-decision.md` · `e5ea755a45f44df2ee1aa3a48b186dc1fa2ff91665b37efbc2809bb67ef6378f` | E21-DR1 |
| E21-DR-PACKETS-UNIT-FREE | **REJECTED** | `SAEA-E21-DR-PACKETS-UNIT-GENERATION-V2` | Directional WER harm. Correlated with unit-constrained. | `docs/readiness/2026-09-10-e21-dr-packets-four-delivery-decision.md` · `e5ea755a45f44df2ee1aa3a48b186dc1fa2ff91665b37efbc2809bb67ef6378f` | E21-DR1 |
| E21-DR-PACKETS-SELF-CONSTRAINED | **ADMITTED_AS_DISCOVERY_REFRESH_IMPROVEMENT** | `SAEA-E21-DR-PACKETS-SELF-GENERATION-V2` | Passes discovery gates with small-effect/protocol limits; does not replace KC-E1f. | `docs/readiness/2026-09-10-e21-dr-packets-four-delivery-decision.md` · `e5ea755a45f44df2ee1aa3a48b186dc1fa2ff91665b37efbc2809bb67ef6378f` | E21-DR1 |
| E21-DR-PACKETS-SELF-FREE | **NULL_NO_DEMONSTRATED_WER_GAIN** | `SAEA-E21-DR-PACKETS-SELF-GENERATION-V2` | No demonstrated corpus-WER gain. Correlated with self-constrained. | `docs/readiness/2026-09-10-e21-dr-packets-four-delivery-decision.md` · `e5ea755a45f44df2ee1aa3a48b186dc1fa2ff91665b37efbc2809bb67ef6378f` | E21-DR1 |
| E21-LOOP-PACKETS-NP4 | **RETAIN_KC_E1F_SYSTEM_FLOOR_FAILED** | `SAEA-E21-LOOP-PACKETS-NP4-JUDGE-GENERATION-V1`; `SAEA-E21-LOOP-PACKETS-NP4-TWIN-GENERATION-V1` | Targeting beats the twin, but PERSON retention against KC-E1f fails. No further LOOP generation. | `docs/readiness/2026-09-10-e21-loop-packets-decision.md` · `3c473dd3cfd5029565b17c6b454bb88d64e98a35db22b16a2437448e1d709029` | E21-LOOP-1 |
| SLURP-G6-LIVE-INTENT-SLOTS | **NOT_FULLY_ADMITTED_GUARD_FAILED** | `SAEA-SLURP-LIVE-INTENT-SLOTS-CONTROL-RECOVERY-V1`; `SAEA-SLURP-LIVE-INTENT-SLOTS-SPEECH-V1` | Positive slot evidence, but the frozen scenario protection point guard fails. | `docs/readiness/2026-09-10-slurp-live-intent-slots-result.md` · `d7cb4bbaad48173719b7be65705a1c964a7b608a5df34bc3ffea3e3c690647b7` | — |
| E21-OFFLINE-DIRECT-THEN-KC-E1F | **SYSTEM_NOT_ADMITTED_INSERTION_GUARD_FAILED** | `SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1`; `SAEA-E21-OFFLINE-KC-E1F-REPAIR-GENERATION-NP4-V1` | Fresh full44 pair finalized. PERSON improves3.3939pp; five extra insertions fail the prospective point guard. No live Reviewer/Planner/new OBS claim. | `docs/readiness/2026-09-11-e21-offline-system-result.md` · `2805ae741e3e80cb4548c287aa160a4edb7a924b326c60ccaac1aaed03061a7b` | — |
| SLURP-PROGRAM-MATCHED-LIVE-FOLLOWUP | **SYSTEM_NOT_ADMITTED_PRIMARY_AND_INTENT_GUARD_FAILED** | `SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1`; `SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1` | Final owner-authorized matched pair finalized. NEW500 row-F1 CI90 crosses zero; intent changes-0.2pp. Preserve original G6 failure; no adaptive repeat. | `docs/readiness/2026-09-11-slurp-program-matched-result.md` · `edaf18d7a25438b0f6c7d54c126e548f0957bfdd1034c45ea2a94d682fd5dbbd` | — |
| FABLE-RESULT-REPRODUCTION-AUDIT | **NUMERICALLY_REPRODUCED** | none; model-free read | Reproduces historical numbers without changing verdicts. | `docs/receipts/fable-result-reproduction-v1.json` · `57a19ffea284b3de7d8c4bd078c463cb9e52f0239d5c7c6089c65a3ba7d7fa89` | — |

## The rules this ledger follows

- **Family rule (owner, 2026-09-08).** Every "not worse" guard is a non-inferiority test whose margin is the half-width of the carrier's OWN same-request null. A margin imported from another carrier is labelled as imported wherever it decided a cell, and the row says so.
- **One factor per cell, with a form twin.** A cell moves one thing; the control is the same cell with that one thing replaced by a token-matched or shape-matched placebo, so the reported effect is attributable to content rather than to prompt form.
- **Single pass on DEV.** Dev-tier populations are optimized on freely; a test split is read once, and the row records when that read is spent.
- **Means, never best-of-N.** Every headline is a pooled or paired mean over a complete manifest scored once through the dataset's standard scorer, never a best-of-N selection and never sharded.
- **Admission statuses (design note section 8).** ADMITTED = a gain on the carrier's primary metric, disjoint from the carrier's own null, with every gating guard non-inferior at the measured margin; NEUTRAL = no harm and no gain, and may enter the default plan; HARMFUL = a gating guard fails, and the module stays in the record as a documented negative and never enters a plan; PENDING = registered, not yet decided.
- **Nothing here is recomputed.** Every number is transcribed from the cited verdict note or receipt and carries its own `source` path in the JSON. Minus signs are written ASCII; the values are the verdicts' own.

### Status words

The owner's list: `ALIGNED`, `ADMITTED`, `ADMITTED-provisional`, `REPLICATED`, `NEUTRAL`, `NULL`, `NOT ADMITTED`, `REJECTED`, `HARMFUL`, `CLOSED`.

Words the verdicts actually used that are outside that list, carried verbatim rather than translated:

- NOT ALIGNED (Earnings-22 alignment)
- EXCLUDED (Earnings-22 shape C)
- ARM B NOT ADOPTED (Earnings-22 prompt A/B)
- REJECT (SLURP EVO-S1 round 1)
- FAIL (three Audio2Tool population verdicts)
- NO CELL PASSES (Audio2Tool calibration)
- QUANTIZATION-EXCLUDED (Audio2Tool Q8 probe)
- RE-LOCKED (two SLURP projection verdicts)
- BASELINE LOCKED (SLURP closed-list baseline)
- REPORTED, NEVER DECIDED (SLURP KU-S1c)
- TIER 8 ALIGNED; TIERS 2 AND 5 FAIL (Audio2Tool tiers 2/5/8)
- NONE (three instrument cells that decide nothing)
- NOT MEASURED (the Audio2Tool own null, which does not exist)
- PENDING (registered, not decided)

ADMITTED-provisional is spelled here as status ADMITTED plus a `provisional` field, because that is what the KC-E1f v2 re-decision's own first line says: "**ADMITTED**, provisionally and with a replication obligation fixed in section 3".

## Historical per-carrier summary — frozen 2026-09-09 snapshot

The counts in this section apply only to the 53 historical rows below. They intentionally exclude the current continuation table above.

| carrier | comparator locked at | own null measured | cells flown | admitted | aligned | neutral | rejected | instrument | pending |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Earnings-21** | corpus WER 8.19952 % / ConEC PERSON 22.48886 on all 44 discovery calls (SAEA-E21-FULL44-DIRECT-BASELINE-V2, 2026-09-04) | MEASURED 2026-09-08 - corpus WER half-width 0.05793, PERSON 0.25009, ORG 0.35609, non-entity 0.06475, numeric 0.15651, semantic 0.00148 (advisory, its null excludes zero) | 8 | 2 | 1 | 1 | 4 | 1 | 3 |
| **Earnings-22** | DEV arm A corpus WER 17.4012 % on the 1,500-row dev subset; ESB test 15.9365 % on 2,735 published utterances (SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1, 2026-09-04) | MEASURED 2026-09-06 on the 1,432 cap-inert rows - corpus WER -0.0844 [-0.2356, +0.0692], half-width 0.1524 | 9 | 3 | 1 | 0 | 5 | 1 | 1 |
| **SLURP** | intent 73.10 / micro SLU-F1 35.80 on DEV-1000 under slurp-slu-official-projected-v2 (SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1 re-locked 2026-09-06) | MEASURED 2026-09-09 - intent half-width 0.9195, micro SLU-F1 1.1804, scenario 0.8255, action 0.9790, per-row SLU-F1 0.8188 | 15 | 1 | 0 | 0 | 4 | 5 | 8 |
| **Audio2Tool** | official-protocol pooled tool accuracy 61.40 % over the 4,000-row official population; no cell is an ACCEPTED alignment baseline | NOT MEASURED - every Audio2Tool interval in this ledger is read against zero | 8 | 0 | 0 | 0 | 8 | 0 | 3 |
| **all four** | | | 40 | 6 | 2 | 1 | 21 | 7 | 15 |

`instrument` counts the cells that decide nothing and exist to produce a comparator, a re-lock or a null band; SLURP additionally carries one `closed-unread` row (KU-S1, refused before registration). Counts are counts of the rows below, nothing else. `flown` and scientific `pending` are independent: the seven KV rows count in both columns. This ledger now carries 53 rows.

**Owner recovery, 2026-09-09.** Seven KV attempts are FINALIZED with COMPLETED manifests and successful scoring jobs; all seven scientific verdicts remain PENDING. Exposure-ledger closure, predecessor decisions, and the NEW500/estimator/process binding require reconciliation. Existing verdicts are preserved; this recovery is not a retrospective preregistration. Evidence: [runtime snapshot](../checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json) and [recovery plan](../superpowers/plans/experiment-handoff/RECOVERY-PLAN.md). Operational completion does not establish that the required KV-0 decision preceded its successors. No KV score value was read for this update.

---

## Earnings-21

### Stage-1 alignment

#### E21-BASE-44 - All 44 discovery calls, bare-core direct baseline

| field | value |
|---|---|
| **status** | **ALIGNED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **ALIGNED.** The bare frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M core transcribes the **whole** Earnings-21 discovery corpus at **8.200 % corpus WER under the Whisper `EnglishTextNormalizer`** |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` |
| verdict note | `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | published `openai/whisper-large-v3` 9.71 corpus WER (Open ASR Leaderboard long-form, same 44 files); Whisper large-v2 9.7; TRADE 9.75; strict degraded floor Whisper medium.en 10.2 |
| the preregistered rule | "band test - 8.200 <= 12.71 (9.71 + 3.0): PASS ... strict floor test - 8.200 <= 10.2 (Whisper medium.en): PASS ... -> ALIGNED" |
| primary result | corpus WER, Whisper normalizer, all 44 calls: 8.200 % over 359,765 reference words (S/D/I 13,098 / 5,701 / 10,700); mean of per-call WER 8.004 %; 1.51 points better than the published 9.71. No CI90 is quoted: this cell is a single-arm alignment read, not a paired contrast. |
| margin used | **none (alignment band).** An alignment band (+-3.0 points around the published row), not a non-inferiority margin. |
| guards | every published degraded-model floor cleared: medium.en 10.2 (by 2.00), small.en 10.8, base.en 12.5, tiny.en 17.0, FastConformer 13.84, Qwen2-Audio-7B 26.06. Equal-stratum re-weighting moves the number by 0.01 (sector) and 0.55 (sample rate) and does not change the verdict. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,593 model contacts of 1,750 registered; 141,345.85 speech-audio seconds (39.263 h); 0.973 GPU-h of a 4.0 ceiling; peak VRAM 22,720 MiB; paid API spend 0. |
| named next step | a self-run `whisper-large-v3` calibration anchor on our exact rows, through the same chunking and the same `core.scoring_batch` scorer; it is not a frozen-core contact and needs its own registration. |
| note | Call 4346923 (16 kHz, worst of the 44 at 18.94 %) is inside the number and costs +0.312 points. |

### Stage-1 own null

#### E21-NULL-44 - Earnings-21's own greedy replicate null

| field | value |
|---|---|
| **status** | **NONE (instrument cell: the verdict states "there is none: this cell admits and refutes nothing")** |
| status is quoted from | section 0 table |
| the verdict's own words | verdict \| **there is none: this cell admits and refutes nothing** |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-FULL44-NULL-REPLICATE-V1` |
| verdict note | `docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-full44-null-replicate-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | the sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` re-flown byte for byte: corpus WER 8.19952 %, prompt tokens 1,935,965, metered speech 141,345.8526875 s - all identical on both arms. |
| the preregistered rule | "For each metric, the Earnings-21 non-inferiority margin becomes the half-width of this null's own call-clustered CI90 on that metric. A future Earnings-21 cell demonstrates an effect on metric m iff its CI90 is disjoint from this null's measured interval, not merely from zero." |
| primary result | corpus WER 8.19952 -> 8.17951, paired call-clustered CI90 delta -0.02001 [-0.08502, +0.03085]; per-window text-identity rate 33.90 % (540 of 1,593); 44 clusters, 10,000 replicates, seed 20260903. |
| margin used | **own-null (this cell measures it).** MEASURED here and published as the carrier's margins: corpus WER / ConEC overall 0.05793; ConEC non-entity 0.06475; ConEC PERSON 0.25009; ConEC ORG 0.35609; numeric-value accuracy 0.15651; semantic high-impact 0.00148. They replace the imported Earnings-22 half-width of +-0.1524 for Earnings-21 only. |
| guards | falsifier PASS on 1,593 of 1,593 windows (slice sha256, bytes, spans, sample rate, parent hash, empty preprocess); identity gate PASS; saturated windows 0, as the comparator. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,593 model calls of 1,750 registered; 141,345.8527 speech-audio seconds of 150,000; 1.0085 GPU-h of 1.2; paid API spend 0. |
| named next step | re-read every open Earnings-21 claim against the section 3 table; decide `semantic-high-impact-error-rate-v1` rather than re-margin it; entity claims need clusters, not tighter margins; and measure the same-request null on SLURP and on Audio2Tool. |
| note | The semantic high-impact rate's own null EXCLUDES zero (+0.00222 [+0.00080, +0.00377]), so that metric cannot carry a "does not rise" clause on this carrier at any margin. |

### Stage-2 construction

#### E21-KC-E1 - KC-E1 - the ConEC pre-meeting brief on the whole prompt (cap 12 entries per class), with the KU-E1c token-matched twin

| field | value |
|---|---|
| **status** | **REJECTED** |
| status is quoted from | h1 |
| the verdict's own words | # REJECTED - KC-E1, the Earnings-21 pre-meeting brief on the whole prompt, capped at 12 entries per class |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E21-KC-E1-BRIEF-44-V1`, `SAEA-E21-KU-E1C-PLACEBO-44-V1`, `SAEA-E21-KC-E1-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-07-e21-kc-e1-pre-meeting-brief-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-kc-e1-verdict/` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` corpus WER 8.1995 % / PERSON 22.489 %, re-derived through the window-pairing instrument at 30/30 PASS; form twin `SAEA-E21-KU-E1C-PLACEBO-44-V1` corpus WER 8.3538 % / PERSON 23.723 %, token-matched at a constant +7 tokens per window. |
| the preregistered rule | "ADMITTED iff ... the call-clustered CI90 lower bound on the PERSON entity-WER reduction is > 0 against the sealed comparator AND > 0 against KU-E1c, and every guard below holds ... HARMFUL if any guard fails." |
| primary result | PERSON entity WER 22.489 -> 18.341 %: +4.148 pp [+2.633, +5.740] against the comparator and +5.382 [+3.914, +6.989] against KU-E1c; the form effect is NEGATIVE (-1.234 [-2.033, -0.484]), so the content does all of the work and more. 1,593 windows, 44 call clusters, seed 20260903, 10,000 replicates, CI90. |
| margin used | **none (margin-less guards).** The guards were written as "the CI90 must exclude zero on the good side" with no non-inferiority margin. This is the defect the v1 KC-E1f verdict named and the owner's family rule of 2026-09-08 fixed. |
| guards | corpus WER +0.536 pp [+0.195, +0.917] FAILS; numeric-value accuracy (call-pooled) -0.544 pp [-1.104, -0.041] FAILS; insertions per reference word -0.191 pp [-0.256, -0.123] PASSES; negation-critical rate 0.0278 % -> 0.0334 % advisory. Two guards fail, so the rule says HARMFUL and the note says REJECTED. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,593 charged calls per arm; prompt tokens 2,907,274 (KC-E1) and 2,918,425 (KU-E1c) against the comparator's 1,935,965; GPU 0.9948 h (KC-E1) and 1.0087 h (KU-E1c), 2.0035 GPU-h for the pair against a registered 4.7; paid API spend 0. |
| named next step | KC-E1f - the brief as a second-pass entity repair on the USE axis, with its own preregistration, its own token-matched twin, its own decision rule and its own owner GO. |
| note | Mechanism, in counts: 152 PERSON substitutions repaired against 2,242 extra non-entity deletions (83 % of the extra deletion mass). The brief is not read aloud - insertions FALL by 686. |

#### E21-KC-E1F-V1 - KC-E1f v1 - the brief as a second-pass substitution-only entity repair, with the KU-E1fc twin

| field | value |
|---|---|
| **status** | **REJECTED** |
| status is quoted from | h1 |
| the verdict's own words | # REJECTED - KC-E1f, the Earnings-21 pre-meeting brief as a second-pass entity repair |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-KC-E1F-REPAIR-44-V1`, `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`, `SAEA-E21-KC-E1F-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-verdict/` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` PERSON 22.489 %, numeric matched values 8,832 of 9,734, insertions 10,700 over 359,765 reference words; form twin `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`. |
| the preregistered rule | "ADMITTED iff ... the call-clustered CI90 lower bound on the PERSON entity-WER reduction is > 0 against the sealed comparator AND > 0 against KU-E1fc, and every guard below holds ... HARMFUL if any guard fails." |
| primary result | PERSON entity WER 22.489 -> 18.752 %: +3.737 pp [+2.653, +4.855] against the comparator and +3.840 [+2.752, +4.958] against KU-E1fc. Both legs MET. |
| margin used | **none (margin-less guards).** The two failing guards are written as superiority tests with no margin. |
| guards | delivery integrity PASSES (1,593 / 1,593 windows, 0 violations, both arms); corpus WER -0.045 pp [-0.061, -0.029] PASSES; numeric-value accuracy (call-pooled) +0.0103 pp [-0.0212, +0.0512] FAILS on a one-value difference (8,833 matched against 8,832 of 9,734); over-generation +0.00028 pp [-0.00199, +0.00255] FAILS on one insertion (10,701 against 10,700). |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,593 charged calls per arm, 141,345.8527 metered speech seconds per arm; 1.1093 GPU-h (KC-E1f) and 1.1656 (KU-E1fc) against a registered 1.2 each; paid API spend 0. |
| named next step | the successor rule must state a margin for each not-worse guard and derive it from a source that PREDATES this contrast; a margin chosen after seeing this result would be a retrofit, and this note does not choose one. |
| note | The v1 verdict stays on record beside the v2 re-decision; nothing withdraws or amends it. |

#### E21-KC-E1F-V2 - KC-E1f v2 - the same sealed bytes re-decided under margins this carrier measured for itself

| field | value |
|---|---|
| **status** | **ADMITTED** |
| provisional | provisional at the verdict; the replication obligation of section 3 was DISCHARGED on 2026-09-08 by SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1. A separate obligation - fly the switch form the admission table records - is still UNMET and keeps the module out of every default plan. |
| status is quoted from | h1 |
| the verdict's own words | # ADMITTED - KC-E1f, re-decided under margins this carrier measured for itself |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-KC-E1F-VERDICT-V2` |
| verdict note | `docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-verdict-v2/` |
| comparator and its sealed numbers | unchanged from v1: sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` and the token-matched twin `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`. Not one number moved - the same sealed bytes, the same rows byte-identical to v1's SHA-256 for SHA-256, the same estimator, seed and draws. |
| the preregistered rule | "the CI90 bound on the HARMFUL side must not exceed that metric's margin, where the margin is the half-width of the Earnings-21 own-null replicate's own call-clustered CI90 on the same metric." |
| primary result | PERSON entity WER reduction +3.737 [+2.653, +4.855] against the sealed comparator and +3.840 [+2.752, +4.958] against the token-matched twin; disjoint from the carrier's own PERSON null interval [-0.24338, +0.25680], 10.61 null half-widths at the lower bound. |
| margin used | **own-null.** OWN-NULL, from `SAEA-E21-FULL44-NULL-REPLICATE-V1`: corpus WER 0.05793, numeric-value accuracy 0.15651, over-generation 0.022178 (computed from the null replicate's own per-window rows through the same instrument and anchored against its published corpus-WER interval before it was applied). |
| guards | corpus WER UB -0.02936 <= +0.05793; numeric-value accuracy (call-pooled) LB -0.02122 >= -0.15651; over-generation UB +0.00255 <= +0.02218; delivery integrity 0 violations on 1,593 windows; the semantic high-impact guard stays advisory because its own null excludes zero. Every gating guard passes under both weightings. |
| harness-admission entry | module *substitution-only repair with the ConEC brief*; switch `judges.<phase>.judges = ['e21-substitution-alignment-flag-v1'] (table: judges; OFF arm null)`; status **ADMITTED**; BLOCKED - provisional obligation UNMET: the recorded switch form has never been flown |
| citable sentence | On the 44 Earnings-21 discovery calls, a second, substitution-only repair pass over the frozen core's own sealed transcript, supplied with a 12-entry ConEC pre-meeting brief, reduces PERSON entity WER from 22.489 % to 18.752 % - a call-clustered CI90 reduction of +3.737 points [+2.653, +4.855] against the sealed comparator and +3.840 [+2.752, +4.958] against a token-matched placebo twin, an effect disjoint from this carrier's own same-request replicate null - with every guard holding at the non-inferiority margins that null measured; the result is training-free, zero-parameter-update, discovery-split, single-carrier and provisional until replicated on the same roster. |
| GPU-hours and contacts | zero model, GPU, tool, embedder, tokenizer, network, audio-decode and paid-API contacts - a re-decision of sealed bytes. The arms it decides cost 1,593 charged calls each and 1.1093 / 1.1656 GPU-h. |
| named next step | the replication of section 3 - a second independent pass of the KC-E1f arm on the same 44-call roster and the same 1,593 windows, re-read against the null's measured intervals - before any candidate freeze, any citation as an admitted effect, or any promotion into the default plan. |
| note | PERSON is the ONLY metric in this cell whose effect is larger than the carrier's own replicate noise; the corpus-WER, ORG and numeric-accuracy improvements v1 reported are inside the null band and are withdrawn as findings. |

#### E21-KC-E1F-REP - KC-E1f replication - a request-identical second pass of the repair arm

| field | value |
|---|---|
| **status** | **REPLICATED** |
| status is quoted from | h1 |
| the verdict's own words | # REPLICATED - KC-E1f, flown a second time on the same roster |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1` |
| verdict note | `docs/readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-replication-v1/` |
| comparator and its sealed numbers | the same sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` and the same twin; the first pass `SAEA-E21-KC-E1F-REPAIR-44-V1` measured +3.737 [+2.653, +4.855] on the same contrast. Configuration proved identical by hash before the first contact: composed config 05777ca3...123b3e5f, protocol 43b60556...0f6bd630, split identity fcc1b0bc...d69e, prompt tokens 3,550,695 on both passes. |
| the preregistered rule | "a second independent pass ... re-read against the null's measured intervals, whose PERSON effect is again disjoint from [-0.24338, +0.25680]." |
| primary result | PERSON entity WER reduction +3.634 [+2.590, +4.690] against the sealed comparator and +3.737 [+2.686, +4.773] against the token-matched twin; both disjoint from the carrier's own PERSON null interval, 10.36 null half-widths at the lower bound of the comparator leg, clearing the band's upper edge by 2.33 points. |
| margin used | **own-null.** OWN-NULL, `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s published table plus the v2 decision's computed over-generation band, read rather than retyped. |
| guards | corpus WER UB -0.03090 <= +0.05793; numeric-value accuracy (call-pooled) LB -0.07745 >= -0.15651; over-generation UB +0.00328 <= +0.02218; delivery integrity 0 violations on 1,593 windows; the semantic high-impact guard advisory and EXACTLY zero on this pass. Every gating guard passes under both weightings. First pass versus replicate is INSIDE the null band on six of the seven metrics that have one (PERSON +0.103 [-0.331, +0.560]). |
| harness-admission entry | module *substitution-only repair with the ConEC brief*; switch `judges.<phase>.judges = ['e21-substitution-alignment-flag-v1']`; status **ADMITTED (replication state set MET by this verdict)**; still BLOCKED - the recorded switch form has never been flown |
| citable sentence | On the 44 Earnings-21 discovery calls, a second, substitution-only repair pass over the frozen core's own sealed transcript, supplied with a 12-entry ConEC pre-meeting brief, reduces PERSON entity WER from 22.489 % - a call-clustered CI90 reduction of +3.737 points [+2.653, +4.855] on the first pass and +3.634 [+2.590, +4.690] on an independent second pass of the same roster under a configuration identical to the digit in prompt tokens, each disjoint from this carrier's own same-request replicate null and each met against a token-matched placebo twin - with every guard holding at the non-inferiority margins that null measured, on both passes; the result is training-free, zero-parameter-update, discovery-split and single-carrier. |
| GPU-hours and contacts | 1,593 charged contacts, prompt tokens 3,550,695 equal to the first pass to the digit, completion tokens 437,350; 1.1957 GPU-h against the first pass's 1.1093 - a 7.8 % spread on request-identical work. |
| named next step | compose and fly the switch form the admission table records - a config fragment that arms `judges.<phase>.judges` and a cell that shows it delivers what the sealed policy form delivered - before the module may enter the Earnings-21 default plan. |
| note | The verdict deliberately does NOT promote the module into the default plan; it records the remaining blocker under its own name. |

### Stage-2 observation

#### E21-TAIL2S - 2.0 s silence tail on every buffered 90-second window

| field | value |
|---|---|
| **status** | **NOT ADMITTED** |
| status is quoted from | section 0 table |
| the verdict's own words | **verdict** \| **NOT ADMITTED** |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E21-FULL44-TAIL2S-V1` |
| verdict note | `docs/readiness/2026-09-07-e21-full44-tail2s-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-full44-tail2s-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2`: corpus WER 8.1995 %, ConEC PERSON 22.4889, ORG 17.2129, non-entity 4.7304, numeric-value accuracy 90.7335, semantic high-impact 0.02780. |
| the preregistered rule | "ADMITTED iff all three hold: (1) the CI90 upper bound on the corpus-WER delta is < -0.2356 ... (2) no agentic metric worsens ... (3) the effect concentrates where the audit predicts." |
| primary result | corpus WER 8.1995 -> 7.2714 %, paired call-clustered CI90 -0.9281 [-1.0514, -0.7949] over 1,593 windows in 44 call clusters; window-level stratified -0.9281 [-1.0632, -0.7782]. |
| margin used | **imported (Earnings-22 null) at decision; re-read against own-null and unchanged.** IMPORTED at decision time: the Earnings-22 same-request null's own interval [-0.2356, +0.0692] and its +-0.1524 half-width. Re-read against Earnings-21's own measured margins the cell still fails, now on FOUR metrics instead of two. |
| guards | clause 1 PASS (upper bound 0.559 points below the -0.2356 threshold); clause 2 FAIL - numeric-value accuracy +0.0411 [-0.2074, +0.2877] and ConEC non-entity +0.1032 [-0.0350, +0.2493] both straddle zero but fail non-inferiority at the imported +-0.1524; clause 3 PASS (interior mid-speech-ended windows -0.9780 against already-silent windows -0.3669, a 2.7x ordering fixed before any number existed). |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,593 model calls of 1,750; 141,345.8527 metered speech seconds (144,531.8527 delivered) of 150,000; 0.9765 GPU-h of 1.2; paid API spend 0. |
| named next step | measure this carrier's own same-request null - the named next cell - and read the PERSON regression as a finding: any future Earnings media convention has to be judged on the substitution-plus-deletion block as well as on corpus WER. |
| note | The whole gain is an insertion collapse (-3,663 insertions, +491 deletions, S+D block 324 operations WORSE). The +0.6856 [+0.1314, +1.3467] PERSON movement the verdict called "the only demonstrated harm" was downgraded by the own-null cell to 2.7 null half-widths, consistent with replicate noise at its low end. |

#### E21-OBS-E1 - OBS-E1 - the transport unit as the speaker turn (diarization-cut units)

| field | value |
|---|---|
| **status** | **REJECTED** |
| status is quoted from | h1 |
| the verdict's own words | # OBS-E1 - the Earnings-21 transport unit as the speaker turn: REJECTED |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` |
| verdict note | `docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-flight-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt attempt-20260904T233816Z-bcd338): corpus WER 8.19952, ConEC PERSON 22.48886, non-entity 4.73038, ORG 17.21293, numeric 90.73351, semantic 0.02780. |
| the preregistered rule | "HARM: CI90 UB(dPERSON) < 0 OR CI90 UB(dWER) < -0.30" - section 6's rule as written; the HARM branch fires and the label is REJECTED. |
| primary result | ConEC PERSON entity WER 22.48886 -> 24.58005, improvement -2.0912, call-clustered CI90 [-3.1701, -1.0978], 8.4 own-null half-widths; corpus WER 8.19952 -> 7.15078, +1.0487 [+0.9253, +1.1745], 18.1 own-null half-widths. 44 clusters, seed 20260903, 10,000 replicates. |
| margin used | **own-null.** OWN-NULL: `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s call-clustered CI90 half-widths (PERSON 0.25009, corpus 0.05793, non-entity 0.06475, ORG 0.35609, numeric 0.15651, semantic 0.00148 advisory). |
| guards | corpus WER non-inferior and a measured improvement; ConEC PERSON NOT non-inferior and a measured harm; non-entity (+0.0148 [-0.1014, +0.1397]) and ORG (+0.5042 [-0.5743, +1.5750]) fail non-inferiority only because their intervals are wider than the null half-width - not resolved at this power, not harmed; numeric-value accuracy +0.1952 [-0.1084, +0.4832] non-inferior; semantic high-impact advisory. Byte-level falsifier PASS on 44 of 44 calls and 5,122 of 5,122 units; identity anchor PASS. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 5,122 contacts against the comparator's 1,593; cut audio 141,345.852687 s identical to the digit, delivered 151,589.852687 s; 1.0657 GPU-h; prompt tokens 2,255,812 (+16.5 %). |
| named next step | OBS-E1b - a fixed-window arm at `obs_buffer_seconds` 27.60 delivering 5,122 windows on the same calls, contact-count and mean-length matched, which is the one arm that separates contact count from boundary placement and speaker purity. Not registered here: one experiment in flight. |
| note | A contact-matched control is impossible by construction, so the cell contrasts the transport unit as a whole and confounds boundary placement, speaker purity and contact count/length. n = 44 clusters is below the program's n >= 400 rule: no paper-facing effectiveness claim in either direction. |

### Harness module

#### E21-DISPATCH - Cross-call dispatcher (obs_prefetch_depth 1)

| field | value |
|---|---|
| **status** | **NEUTRAL** |
| status is quoted from | h1 |
| the verdict's own words | # Verdict - the cross-call dispatcher is NEUTRAL on Earnings-21, and it buys 17 % of throughput |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-FULL44-DISPATCH-ADMISSION-V1` |
| verdict note | `docs/readiness/2026-09-08-e21-dispatcher-admission-v1-verdict.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-dispatch-admission-v1/` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` corpus WER 8.19952 %, plus a second like-for-like arm, the depth-0 own-null replicate `SAEA-E21-FULL44-NULL-REPLICATE-V1` on the same resident session. The two pairings AGREE on the status. |
| the preregistered rule | "NEUTRAL - otherwise: every gating metric's paired delta lies within +-margin_m and no gating CI90 excludes zero on the harmful side. Section 8's gate admits NEUTRAL modules into the default plan." |
| primary result | corpus WER (asr-wer-whisper) 8.19952 -> 8.20730 %, call-clustered CI90 +0.00778 [-0.02329, +0.03856] against the sealed comparator (0.13 of the carrier's own null half-width) and +0.02780 [-0.02052, +0.09427] against the depth-0 own-null replicate. |
| margin used | **own-null.** OWN-NULL, `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s measured call-clustered CI90 half-widths. The caveat travels with them: that null measured the noise of re-flying at depth 0. |
| guards | conec_non_entity_wer_percent -0.00263 [-0.01994, +0.01574] vs margin 0.06475 (inside); ORG -0.32088 [-0.88314, +0.19584] vs 0.35609 (inside); ConEC overall +0.00778 [-0.02329, +0.03856] vs 0.05793 (inside); PERSON +0.20569 [-0.07995, +0.51951] vs 0.25009 (inside); corpus WER +0.00778 vs 0.05793 (inside); numeric-value accuracy -0.05137 [-0.19511, +0.09794] vs 0.15651 (inside). The advisory semantic high-impact metric moved +0.00222 [+0.00110, +0.00343], 1.5x its margin - it was removed from the gate BEFORE any number existed because its own null excludes zero, and the receipt records status_if_advisory_were_gating. |
| harness-admission entry | module *cross-call dispatcher (obs_prefetch_depth 1)*; switch `obs_prefetch_depth 0 -> 1 (class: run; falsifier kind request-bytes-identical)`; status **NEUTRAL**; IN the default plan configs/baseline/e21-buf90-zero-locked-scored4-prefetch1.json |
| citable sentence | none |
| GPU-hours and contacts | 1,593 model calls; 1.0165 GPU-h of 1.2 registered; paid API spend 0. Throughput 17.244 -> 20.168 windows/min (+16.96 %) against the depth-0 arm on the same server, zero-slot share 17.55 % -> 3.75 %, idle stretches 43 -> 10. |
| named next step | turn the dispatcher on for Earnings-21 cells at this geometry one fragment at a time; decide `semantic-high-impact-error-rate-v1` rather than re-margin it; measure the process-instance term; and treat depth 2 as a named follow-up that gets its own admission receipt or is not used. |
| note | The falsifier proves the request did not move: all 1,593 emitted SliceRecords equal the comparator's on sha256, bytes, span, sample rate and parent hash, and prompt_tokens_total is 1,935,965 on both, so the only channel open to this module is scheduling. NEUTRAL is a licence to USE it, never evidence about knowledge or the agent layer. |

### Stage-2 construction (pending)

#### E21-LOOP-1 - Loop-1 - the first whole-loop Earnings-21 cell (Plan / Observe / Solve / Review / re-Observe / Solve / Commit)

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | not decided - no verdict note exists |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-MF-LOOP-1-PREP-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-e21-loop-1-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-loop-1-wire-check/` |
| comparator and its sealed numbers | to be paired against the sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2`; the model-free preparation row is closed and its judge inventory and wire check are receipted. |
| the preregistered rule | see the preregistration; not applied - the cell has not flown. |
| primary result | not measured. |
| margin used | **own-null (declared).** Own-null (`SAEA-E21-FULL44-NULL-REPLICATE-V1`) when it flies. |
| guards | not evaluated. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | model-free preparation only: SAEA-E21-MF-LOOP-1-PREP-V1, 0 calls, 0 GPU hours. |
| named next step | the first cell that runs the whole loop, after KC-E1f. |

#### E21-DR1 - DR1 - draft-then-refresh

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | not decided - no verdict note exists |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-E21-MF-DR1-PREP-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-09-e21-draft-then-refresh-dr1-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-e21-dr1-wire-check/` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2`; the model-free unit-draft stitch and the wire check are receipted. |
| the preregistered rule | see the preregistration; not applied. |
| primary result | not measured. |
| margin used | **own-null (declared).** Own-null (`SAEA-E21-FULL44-NULL-REPLICATE-V1`) when it flies. |
| guards | not evaluated. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | model-free preparation only: SAEA-E21-MF-DR1-PREP-V1, 0 calls, 0 GPU hours. |
| named next step | registered and awaiting its flight slot. |

### Stage-2 observation (pending)

#### E21-OBS-E1B - OBS-E1b - uniform context units, the contact-matched control for OBS-E1

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | not decided - no verdict note exists |
| date | 2026-09-08 |
| ledger run id(s) | `SAEA-E21-MF-OBS-E1B-SEAM-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-e21-obs-e1b-context-units-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1b-seam/` |
| comparator and its sealed numbers | sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` and the OBS-E1 arm; the model-free seam and stitch proof are receipted. |
| the preregistered rule | see the preregistration; not applied. |
| primary result | not measured. |
| margin used | **own-null (declared).** Own-null (`SAEA-E21-FULL44-NULL-REPLICATE-V1`) when it flies. |
| guards | not evaluated. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | model-free preparation only: SAEA-E21-MF-OBS-E1B-SEAM-V1, 0 calls, 0 GPU hours. |
| named next step | a fixed-window arm at `obs_buffer_seconds` 27.60 delivering 5,122 windows on the same calls - the one arm that separates contact count from boundary placement and speaker purity. |

---

## Earnings-22

### Stage-1 alignment

#### E22-ESB-TEST-ALIGN - ESB short-form test, the study's first same-model alignment attempt

| field | value |
|---|---|
| **status** | **NOT ALIGNED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **NOT ALIGNED. 15.937 % corpus WER under the Whisper `EnglishTextNormalizer` over all 2,735 published ESB test utterances, against Qwen3-Omni-30B-A3B-Instruct's own published 9.79** (+6.15) |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` |
| verdict note | `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-e22-esb-shortform-alignment-400-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | the same frozen model's own published zero-shot 9.79 (NVIDIA NeMo AutoModel) and the cross-read 12.3 (Open ASR Leaderboard); strict floor whisper-large-v3 11.59; loose floor whisper-base.en 15.09. |
| the preregistered rule | "band <= 12.79 (9.79 + 3) ... floor test (strict), whisper-large-v3 <= 11.59 ... floor test (loose), whisper-base.en <= 15.09 ... ALIGNED-BETTER < 6.79" |
| primary result | corpus WER 15.937 % over 48,919 reference words (S/D/I 2,236 / 948 / 4,612) on 2,735 utterances; mean of per-utterance WER 28.129 %; equal-call weighting 16.703 %. Single-arm alignment read - no CI90 is quoted. |
| margin used | **none (alignment band).** An alignment band, not a non-inferiority margin. |
| guards | band FAIL (+3.15 over), strict floor FAIL, loose floor FAIL by 0.85; eight of nine published floors failed and only whisper-tiny.en 19.12 cleared. Per call 14.113 to 22.159 - no call is inside the band. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 2,735 contacts of 2,800 registered; 19,494.608 s (5.415 h) of 20,500 registered; about 0.226 GPU-h of 2.0; peak VRAM 22,506 MiB; paid API spend 0. |
| named next step | a self-run whisper-large-v3 anchor over these exact utterances through this exact scorer, which would remove the normalizer, aggregation, chunking and subset confounds in one step; and a test of the over-generation hypothesis on a population that is not these six calls. |
| note | Superseded as the study's short-form surface by the 2026-09-07 tail-silence re-read, which is ALIGNED under a named model-usage local optimization. |

#### E22-ESB-TEST-TAIL2S - ESB short-form TEST re-read with the tail-silence media (the second and last test read)

| field | value |
|---|---|
| **status** | **ALIGNED** |
| status is quoted from | section 0 table |
| the verdict's own words | **verdict** \| **ALIGNED** |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` |
| verdict note | `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-esb-shortform-tail2s-test-v1` |
| comparator and its sealed numbers | the sealed `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` on the same 2,735 published segments: 15.9365 % corpus WER; published NeMo AutoModel 9.79 and cross-read 12.3. |
| the preregistered rule | "band test: W <= 12.79 (9.79 + 3.0). floor test (strict): W <= 11.59, whisper-large-v3 on the same column ... ALIGNED = band test and strict floor test both pass." |
| primary result | corpus WER W = 9.2377 % against the sealed 15.9365 % on the same rows: paired pooled delta -6.6988 [-7.0373, -6.3753], CI90 stratified by call. The band test passes with 3.55 points to spare; the strict floor passes with 2.35. |
| margin used | **none (alignment band + paired contrast).** None for the band; the paired contrast against the sealed rows is the primary statement and the band is secondary. |
| guards | the section 4.2 falsifier holds on 2,735 of 2,735 rows: measured prompt tokens 476,578 against the predicted 476,578, zero disagreeing rows; the four-row smoke returned 88 / 166 / 270 / 556 against its own predicted totals. All nine degraded-model floors cleared. |
| harness-admission entry | none |
| citable sentence | Under a named model-usage local optimization of the study's own serving path, the frozen core reaches 9.2377 % corpus Whisper-normalized WER on the published ESB Earnings22 test subset, against a published 9.79 and a cross-read 12.3 that were measured without it. |
| GPU-hours and contacts | 2,735 contacts of 2,800 registered; 24,964.608 of 25,500 registered speech-audio seconds; 0.2220 GPU-h against a 1.00 registered ceiling and a 0.60 plan; paid API spend 0. |
| named next step | Earnings-22 test is CLOSED: the read is spent, no third read is proposed, and any further Earnings-22 work moves to dev or stops. |
| note | The deviation label is not detachable: the published systems did not append silence, so this number is never reported as a like-for-like reproduction of the published protocol. |

### Stage-1 own null

#### E22-DEV-NULL - The cap-inert same-request null - the study's first measured greedy-nondeterminism null

| field | value |
|---|---|
| **status** | **NONE (a measurement inside the cell (b) read, not a decided cell)** |
| status is quoted from | opening, second paragraph |
| the verdict's own words | **The number that outlasts both decisions is a null.** |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-STOPCAP-V1`, `SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/verdict/summary.json` |
| comparator and its sealed numbers | arm A restricted to the same 1,500 dev rows: corpus WER 17.4012 %, agentic error rate 1.9161 %. |
| the preregistered rule | no admission rule - this is the measurement the two cell decisions sit on top of. |
| primary result | on the 1,432 cap-inert rows, where the request differed only by an inert `max_tokens` integer larger than the generation, corpus WER moved -0.0844 points, CI90 [-0.2356, +0.0692], with 302 of 1,432 rows emitting different bytes. |
| margin used | **own-null (Earnings-22); exported to two other carriers and superseded on both.** This interval's half-width, +-0.1524, became the IMPORTED Earnings-21 margin (later replaced by Earnings-21's own) and, on the SLURP scale, the imported +-0.60 pp bar (later replaced by SLURP's own). |
| guards | identity gate: six hard-coded raw pairs reproduced; 1,500 rows compared per cell against the finalize block, zero disagreements. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | no contacts of its own - a model-free read of the sealed cell (b) rows; the verdict row SAEA-E22-MF-USAGE-CELLS-VERDICT-V1 spent zero contacts of every kind and zero GPU hours. |
| named next step | every cross-run Earnings-22 contrast this study has drawn or will draw sits on top of this null. |
| note | About a fifth of the admitted cell (a) effect. |

### Stage-2 model usage

#### E22-PROMPT-AB - DEV ESB prompt A/B - the instruction text

| field | value |
|---|---|
| **status** | **ARM B NOT ADOPTED** |
| status is quoted from | section: Decision, as preregistered |
| the verdict's own words | **Decision, as preregistered: arm A's instruction remains this study's ASR instruction for cleaned-reference protocols.** |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-PROMPT-A-V1`, `SAEA-E22-DEV-ESB-PROMPT-B-V1` |
| verdict note | `docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | arm A, the sealed ESB test flight's instruction byte for byte: corpus WER 17.565 % over 6,038 dev utterances and 103,423 reference words. |
| the preregistered rule | "The arm with the lower pooled corpus Whisper-normalized WER becomes this study's ASR instruction for cleaned-reference protocols. This holds whatever the significance test says." |
| primary result | arm B 18.394 % against arm A 17.565 %: B - A = +0.830 corpus WER points; the corpus-level A - B delta is -0.830 points, CI90 [-1.653, -0.172]; the per-utterance paired delta is -0.02741 [-0.0449, -0.0133] with 686 saves / 821 harms / 4,531 ties and sign test p = 0.00055. 10,000 replicates stratified by source call (10 strata), seed 20260903. |
| margin used | **none (selection rule).** A selection rule on a dev split, which the preregistration says does not require significance. |
| guards | arm B is worse on every aggregation reported: corpus, per-utterance mean, equal-call and the frozen `saea-scoring-v1` family. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 6,038 contacts of 6,350 registered per arm; 0.4515 and 0.4596 GPU-h of 0.75 each; across the experiment 12,076 contacts, 21.83 h of audio and 0.911 GPU-hours. |
| named next step | the prompt text is excluded as the explanation; the next suspect named for the owner is the model card's evaluation SHAPE (no system message, instruction text after the audio). |
| note | No alignment verdict is issued or possible: these ten calls are the study's own dev subset10, not the published ESB test subset. |

#### E22-SHAPE-C - DEV ESB shape C - the model card's evaluation request shape

| field | value |
|---|---|
| **status** | **EXCLUDED** |
| status is quoted from | section 7 |
| the verdict's own words | **The official usage shape is EXCLUDED.** It does not become this study's ASR request shape for cleaned-reference protocols |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-SHAPE-C-V1` |
| verdict note | `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-shape-c-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | arm A 17.5648 % corpus WER and arm B 18.3944 % on the same 6,038 dev utterances and the same media bytes. |
| the preregistered rule | a three-way conjunction: "arm C's pooled corpus WER beats arm A" AND "paired C-A CI90 lower bound above 0" AND "hypothesis/reference length ratio falls toward 1.0". |
| primary result | arm C 17.8896 % against arm A 17.5648 %: C - A = +0.325 corpus WER points. The mean of per-utterance WER moves the other way (31.3062 against 33.1249), which is the whole story of the experiment. |
| margin used | **none (conjunction rule).** A three-way conjunction whose governing condition is a plain comparison. |
| guards | condition 1 (C beats A) NO - 17.8896 > 17.5648; condition 2 (CI90 lower bound above 0) yes at +0.0112; condition 3 (length ratio falls toward 1.0) yes - 1.0398 against 1.0861. The conjunction fails on the first condition under either reading. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 6,038 contacts of 6,350 registered; 0.4620 GPU-h of a registered 1.0 and a planned 0.6. |
| named next step | no second test read is recommended to the owner; arm A's instruction and request shape both stand, each now chosen against a measured alternative rather than inherited. |
| note | The shape removed 2,176 insertions (11,270 -> 9,094) and paid 2,605 deletions (2,370 -> 4,975): over-generation was a symptom, not the cause. |

#### E22-USAGE-A-Q8 - Cell (a) - the Q8_0 decoder

| field | value |
|---|---|
| **status** | **ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **CELL (a), THE Q8_0 DECODER, IS ADMITTED: -0.4305 corpus-WER points with a call-stratified CI90 of [-0.6468, -0.2177] and an agentic CI90 upper bound of +0.0192, so both preregistered clauses hold.** |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-Q8-V1`, `SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/verdict/summary.json` |
| comparator and its sealed numbers | arm A restricted to these 1,500 dev rows: corpus WER 17.4012 %, agentic error rate 1.9161 %, over 26,251 reference words. |
| the preregistered rule | two clauses: "corpus WER improves and the CI90 upper bound is -0.2177 < 0" AND "the agentic CI90 upper bound is +0.0192 < +0.05". |
| primary result | corpus WER (Whisper normalizer) -0.4305 points, call-stratified CI90 [-0.6468, -0.2177], call-clustered [-0.6063, -0.2368]; cell corpus WER 16.9708 %. 1,500 rows, 10,000 replicates stratified by source call, seed 20260903. |
| margin used | **preregistered fixed margin (+0.05 on the agentic metric).** The agentic clause carries a +0.05-point margin inherited verbatim from section 1.6 of the boundary-exact preregistration and fixed before any number existed. It is a preregistered margin, not a null half-width. |
| guards | clause 1 holds; clause 2 holds (agentic delta -0.0610, CI90 [-0.1494, +0.0192]). Per utterance 195 saves / 141 harms / 1,164 ties, exact sign test p = 0.0038. Named-entity mass 299 -> 299 and domain-term mass 49 -> 49: the higher-precision decoder buys exactly nothing on the two classes the agentic metric is about. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 1,600 calls / 10,500 speech-audio seconds / 3.0 GPU hours; realized contacts and GPU hours are not stated in the verdict, which is a zero-contact model-free read. |
| named next step | keep Earnings-22 short-form NOT ALIGNED at 15.937: an admitted dev setting does not alter a test number that was never re-flown, and 0.43 points does not close 6.15. |
| note | Model usage is closed as an explanation of the Earnings-22 gap: the largest thing the study can buy inside its own serving path is 7 % of the 6.15-point test gap. |

#### E22-USAGE-B-CAP - Cell (b) - the duration-proportional decode cap

| field | value |
|---|---|
| **status** | **NOT ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **CELL (b), THE DURATION-PROPORTIONAL CAP, IS NOT ADMITTED, and it fails BOTH clauses: the WER CI90 upper bound is +0.0149 and the agentic CI90 upper bound is +0.0544 against a margin of +0.05.** |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-STOPCAP-V1`, `SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/verdict/summary.json` |
| comparator and its sealed numbers | arm A restricted to these 1,500 dev rows: corpus WER 17.4012 %, agentic error rate 1.9161 %. |
| the preregistered rule | the same two clauses as cell (a): WER CI90 upper bound below zero, and agentic CI90 upper bound below +0.05 points. |
| primary result | corpus WER -0.1409 points, call-stratified CI90 [-0.2967, +0.0149], call-clustered [-0.3698, +0.0915]; cell corpus WER 17.2603 %. |
| margin used | **preregistered fixed margin (+0.05 on the agentic metric).** The same preregistered +0.05-point agentic margin, inherited verbatim and not adjusted after the fact. |
| guards | clause 1 fails (upper bound +0.0149, not below zero); clause 2 fails by 0.0044 points (agentic -0.0152, CI90 [-0.0903, +0.0544] against +0.05). Per utterance 98 saves / 73 harms / 1,329 ties, sign test p = 0.066. The cap bit 68 rows against a predicted 50, and 22 of the 37 error operations it removed came from the 1,432 rows the cap could not touch. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 1,600 calls / 10,500 speech-audio seconds / 0.35 GPU hours; realized contacts and GPU hours are not stated in the verdict, which is a zero-contact model-free read. |
| named next step | half of its measured gain is jitter; the cap is not adopted and the cap-inert null it produced is the number that outlasts the decision. |
| note | A 0.0044-point miss is a miss: the margin was not adjusted after seeing the result. |

### Stage-2 observation

#### E22-ENC-1-BX - Encoding probe cell 1 - boundary-exact re-cut

| field | value |
|---|---|
| **status** | **NOT ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **Cell 1 (`boundary-exact`) is NOT ADMITTED**: it is a real effect (-3.0475 corpus WER, -2.7808 boundary) that fails clause 2 alone, its agentic CI90 upper bound being **+0.0637** against the **+0.05** margin fixed before any number existed. |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-BX-V1`, `SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev-encoding-probes/verdict/summary.json` |
| comparator and its sealed numbers | arm A on the same 1,500 dev rows: corpus WER 17.4012 %, agentic 1.9161 %, boundary block 8.2778 WER points. |
| the preregistered rule | "ADMITTED as a model-usage local optimization iff all three clauses hold: (1) the CI90 upper bound on the corpus-WER delta is < -0.2356 ...; (2) the agentic error rate's point estimate is <= arm A's and the CI90 upper bound on its delta is below +0.05 points; (3) segmentation-artifact + runaway-tail + runaway-head falls by at least 2.0 WER points from arm A's 8.2778." |
| primary result | corpus WER 17.4012 -> 14.3537 %, stratified delta -3.0475 [-3.5344, -2.5654]; boundary block delta -2.7808 [-3.2253, -2.3505]; 512 saves / 265 harms / 723 ties, sign test p < 1e-6. |
| margin used | **own-null (Earnings-22) for clause 1; preregistered fixed margin for clause 2.** Clause 1's -0.2356 threshold is the Earnings-22 same-request null's own interval bound; the agentic +0.05 is the preregistered fixed margin. |
| guards | clause 1 PASS; clause 2 FAIL at +0.0637 against +0.05 (agentic delta -0.0190 [-0.1026, +0.0637]); clause 3 PASS. Its `named-entity` mass RISES 299 -> 301 and `domain-term` 49 -> 58 - the only cell that worsens both - which is what removing real audio at a clip edge should cost: the re-cut removes up to 0.180188 s of real audio from 1,403 of 1,500 clips. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 1,600 calls / 10,200 speech-audio seconds / 0.40 GPU hours; realized contacts and GPU hours are not stated in the verdict, which is a zero-contact model-free read. Audio tokens 0.9848x arm A and prompt tokens 210,663 against a predicted 210,663 on 1,500 of 1,500 rows. |
| named next step | not adopted; `tail-silence-2s` is the recommended local optimization for the E22 short-form serving surface. |
| note | The clause-2 margin came from the boundary-exact preregistration itself, which is the cell it then refused. |

#### E22-ENC-2-TAIL2S - Encoding probe cell 2 - 2.0 s of appended digital silence

| field | value |
|---|---|
| **status** | **ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **CELL 2 (`tail-silence-2s`) AND CELL 3 (`pad-30s`) ARE BOTH ADMITTED, AND THEY DID WHAT NO MODEL-USAGE KNOB COULD: THEY MOVED THE BOUNDARY BLOCK.** |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-TAIL2S-V1`, `SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev-encoding-probes/verdict/summary.json` |
| comparator and its sealed numbers | arm A on the same 1,500 dev rows: corpus WER 17.4012 %, agentic 1.9161 %, boundary block 8.2778 WER points. |
| the preregistered rule | "ADMITTED as a model-usage local optimization iff all three clauses hold: (1) the CI90 upper bound on the corpus-WER delta is < -0.2356 ...; (2) the agentic error rate's point estimate is <= arm A's and the CI90 upper bound on its delta is below +0.05 points; (3) segmentation-artifact + runaway-tail + runaway-head falls by at least 2.0 WER points from arm A's 8.2778." |
| primary result | corpus WER 17.4012 -> 9.4054 %, stratified delta -7.9959 [-8.5203, -7.5007], clustered [-8.7149, -7.3239]; boundary block 8.2778 -> 1.1085, delta -7.1807 [-7.6649, -6.7379], 86.7 % of the block; 811 saves / 97 harms / 592 ties, sign test p < 1e-6. |
| margin used | **own-null (Earnings-22) for clause 1; preregistered fixed margin for clause 2.** Clause 1's -0.2356 threshold is the Earnings-22 same-request null's own interval bound; the agentic +0.05 is the preregistered fixed margin. |
| guards | clause 1 PASS, clause 2 PASS (agentic -0.1333 [-0.2129, -0.0554]), clause 3 PASS. The CI90 upper bound of -7.5007 sits 24 whole null-widths below zero and the effect is 18.6x the Q8_0 decoder's. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 1,600 calls / 13,500 speech-audio seconds / 0.50 GPU hours; realized contacts and GPU hours are not stated in the verdict, which is a zero-contact model-free read. Audio tokens 1.2800x arm A and prompt tokens 251,782 against a predicted 251,782 on 1,500 of 1,500 rows. |
| named next step | `tail-silence-2s` is the recommended local optimization for the E22 short-form serving surface - the cheapest admitted variant at 1.28x arm A's audio tokens against `pad-30s`'s 4.34x - and the one-time test re-read with the same media is registered separately. |
| note | Mechanism: the model completes an utterance whose signal stops mid-speech; moving the encoder's pad block 2 s away from the last word removes the continuation. Tail insertion spans collapse 704 -> 39 while head spans barely move 149 -> 135. |

#### E22-ENC-3-PAD30S - Encoding probe cell 3 - silence padding to 30.0 s

| field | value |
|---|---|
| **status** | **ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **CELL 2 (`tail-silence-2s`) AND CELL 3 (`pad-30s`) ARE BOTH ADMITTED, AND THEY DID WHAT NO MODEL-USAGE KNOB COULD: THEY MOVED THE BOUNDARY BLOCK.** |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-E22-DEV-ESB-PAD30S-V1`, `SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1` |
| verdict note | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev-encoding-probes/verdict/summary.json` |
| comparator and its sealed numbers | arm A on the same 1,500 dev rows: corpus WER 17.4012 %, agentic 1.9161 %, boundary block 8.2778 WER points. |
| the preregistered rule | the same three-clause rule as cells 1 and 2, quoted verbatim in section 2 of the verdict. |
| primary result | corpus WER 17.4012 -> 9.3254 %, stratified delta -8.0759 [-8.6069, -7.5659]; boundary block -> 0.9181, delta -7.3597 [-7.8431, -6.9204]; 823 saves / 103 harms / 574 ties, sign test p < 1e-6. |
| margin used | **own-null (Earnings-22) for clause 1; preregistered fixed margin for clause 2.** Clause 1's -0.2356 threshold is the Earnings-22 same-request null's own interval bound; the agentic +0.05 is the preregistered fixed margin. |
| guards | clause 1 PASS, clause 2 PASS (agentic -0.1181 [-0.2083, -0.0269]), clause 3 PASS. Its advantage over `tail-silence-2s` is -0.0800 [-0.2581, +0.1000], entirely inside this runtime's measured same-request null and a coin-flip per row (82 saves / 75 harms / 1,343 ties, sign test p = 0.632). |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 1,600 calls / 46,000 speech-audio seconds / 2.00 GPU hours; realized contacts and GPU hours are not stated in the verdict, which is a zero-contact model-free read. Audio tokens 4.3403x arm A and prompt tokens 678,026 against a predicted 678,026 on 1,500 of 1,500 rows. |
| named next step | admitted but NOT recommended: it buys nothing over the tail within the measured null for 3.39x the audio tokens. |
| note | It more than doubles the encoder's zero-pad block (75,330 -> 148,412 padded mel frames) and still wins by a hair, which is what shows the mechanism is the discontinuity and not the constant. |

### Stage-2 construction (pending)

#### E22-KC-E2 - KC-E2 - the pre-meeting brief on the Earnings-22 DEV-1500 roster

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | not decided - no verdict note exists |
| date | 2026-09-07 |
| ledger run id(s) | none registered |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-brief-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-kc-e2-brief-dev1500-v1/` |
| comparator and its sealed numbers | arm A on the 1,500-row dev subset; the brief-source audit that prices its knowledge is receipted model-free. |
| the preregistered rule | see the preregistration; not applied - the cell has not flown. |
| primary result | not measured. |
| margin used | **own-null (declared).** The Earnings-22 cap-inert null's +-0.1524 half-width is this carrier's own measured margin. |
| guards | not evaluated. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | no exposure row registered; zero contacts spent. |
| named next step | preregistration only - no flight row exists in the exposure ledger for this cell. |
| note | The only cell in this ledger with no exposure-ledger row of any kind. |

---

## SLURP

### Stage-1 alignment / comparator lock

#### SLURP-CL-BASE - Closed-list direct baseline on DEV-1000

| field | value |
|---|---|
| **status** | **BASELINE LOCKED** |
| status is quoted from | section: Verdict |
| the verdict's own words | **The closed-list arm is the study's SLURP direct baseline**, as preregistered, and it moves the intent number a long way while leaving the slot number where it was. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` |
| verdict note | `docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-direct-baseline-v1/result-summary.json` |
| comparator and its sealed numbers | the sealed DEV-1000 M0 arm (scenario 70.00 / action 61.50 / intent 53.60 / SLU-F1 36.90) and the locked BLEND cell (83.90 / 77.60 / 75.70 / 41.69), both reproduced to the second decimal from the 2026-09-04 alignment audit as this read's identity anchor. |
| the preregistered rule | "The closed-list arm becomes the study's SLURP direct baseline regardless of outcome, because it is the protocol-aligned one. There is no pass/fail gate on the headline." |
| primary result | intent (scenario+action) 71.40 against M0's 53.60: paired +17.80 pp, CI90 [+15.70, +19.90], sign test p = 1.7e-38, holding at +17.60 pp [+14.80, +20.40] on the 500 rows unexposed at the lock tier. SLU-F1 35.80 against 36.90 (-1.10); the paired per-sample slot-F1 contrast is -1.70 pp [-2.94, -0.48]. 10,000 replicates stratified by gold scenario, seed 20260807, CI90. |
| margin used | **none (comparator lock).** The cell is a comparator lock, not an admission. |
| guards | impossible (scenario, action) pairs fall 32.20 % -> 4.20 %, an 87 % reduction, and entity types outside the 55 fall 0.28 % -> 0.00 %; the port-vs-official identity check passed on all three arms at an absolute difference of 0.0; zero skipped rows on every arm. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 contacts of 1,050 registered; 2,884.79 of 3,000 audio seconds; about 0.105 of 1.0 GPU-h; 0 tool, 0 embedding contacts, 0 paid spend. |
| named next step | the slot layer is the target an evidence-acquisition control plane exists to attack: SLU-F1 did not move under a closed type list, and that is where the 28-point gap to the weakest published pipeline lives. |
| note | 80.5 % of the locked BLEND cell's SLURP intent margin over M0 is reproduced by a prompt-side label inventory with zero retrieval; what survives is +4.30 pp pooled, and on the unexposed 500 its 90 % CI includes zero. |

### Stage-1 comparator re-lock (model-free)

#### SLURP-PROJ-V1 - Legal-label projection v1 - the closed-list comparator re-locked

| field | value |
|---|---|
| **status** | **RE-LOCKED** |
| status is quoted from | section: Verdict |
| the verdict's own words | **RE-LOCKED, as preregistered.** The SLURP direct comparator is the sealed closed-list arm **plus** the legal-label projection `slurp-legal-label-projection-v1`, scored through the registered `slurp-slu-official-projected`. |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1` |
| verdict note | `docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-relock/result-summary.json` |
| comparator and its sealed numbers | the unprojected sealed closed-list arm: scenario 81.00, action 73.90, intent 71.40, SLU-F1 35.80, 3 unparsed. |
| the preregistered rule | the preregistered lock conditions: no gold-scenario stratum harmed on intent, and the entity columns unchanged row by row. |
| primary result | intent 71.60 against 71.40: paired +0.20 pp pooled, CI90 [0.00, +0.50], 2 saves / 0 harms; +0.00 on OLD500 and +0.40 on NEW500. Action 73.30, down 0.60 pp from 73.90. Impossible (scenario, action) pairs 3.90 % -> 0.00 %. |
| margin used | **none (lock conditions).** A lock decision with harm bounds, not a non-inferiority test. |
| guards | SLU-F1 35.80, entities-strict, Word-F1 and Char-F1 all unchanged to the last decimal on every arm, row by row; no gold-scenario stratum harmed on intent anywhere; the port-vs-official identity check passed on all ten scored sets (absolute difference 0.0; KC-S1a 5.6e-17). |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | zero model, GPU, tool, embedding and network contacts; one registered read, ten scored sets, one lock decision. |
| named next step | the residual is named and priced: 19 of the 39 illegal rows put a legal ACTION name in the SCENARIO slot, and promoting that name back to its owning scenario would recover 15 of them, about +1.5 pp intent. |
| note | Protocol alignment, not accuracy: only 2 of the 39 legalised rows land on the gold intent. Superseded by v2 the same day. |

#### SLURP-PROJ-V2 - Legal-label projection v2 - promoting an action-named scenario

| field | value |
|---|---|
| **status** | **RE-LOCKED** |
| status is quoted from | section: Verdict |
| the verdict's own words | **RE-LOCKED, as preregistered.** The SLURP direct comparator is the sealed closed-list arm **plus** `slurp-legal-label-projection-v2`, scored through the registered `slurp-slu-official-projected-v2`. |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1` |
| verdict note | `docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-v2/result-summary.json` |
| comparator and its sealed numbers | v1's locked 71.60 intent and the unprojected sealed 71.40, on the same sealed DEV-1000 outputs. |
| the preregistered rule | the preregistered lock conditions: non-negative on OLD500 and NEW500 in both contrasts, and no gold-scenario stratum harmed on intent in either. |
| primary result | intent 73.10: paired +1.50 pp over the locked v1 comparator (15 saves / 0 harms, CI90 [+1.0, +2.1], p = 6.1e-05) and +1.70 pp over the raw sealed labels (17 saves / 0 harms, CI90 [+1.1, +2.3], p = 1.5e-05). Scenario 82.60 from 81.00; action 74.60, above the unprojected 73.90. |
| margin used | **none (lock conditions).** A lock decision with harm bounds, not a non-inferiority test. |
| guards | SLU-F1 35.80, entities-strict 21.91, Word-F1 33.69 and Char-F1 38.20 unchanged to the last decimal on every arm across all three views; impossible pairs 3.90 % -> 0.00 %; not one gold-scenario stratum harmed on intent in either contrast. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | zero model, GPU, tool, embedding and network contacts; one registered read, fifteen scored sets, one lock decision. |
| named next step | every pending SLURP cell now has to beat 73.10, not 71.60 and not 71.40. |
| note | The whole intent gain is one stratum: `recommendation` moves 46.67 -> 71.67 on 60 rows (+25.00 pp, 15 saves, 0 harms) and the other seventeen strata are flat. It is a repair of the baseline's own output, not a mechanism. |

### Stage-1 own null

#### SLURP-NULL - SLURP's own greedy replicate null

| field | value |
|---|---|
| **status** | **NONE (instrument cell: the verdict states "there is none: this cell admits and refutes nothing")** |
| status is quoted from | section 0 table |
| the verdict's own words | verdict \| **there is none: this cell admits and refutes nothing** |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1` |
| verdict note | `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-own-null-replicate-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | the re-locked closed-list comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` re-flown byte for byte: intent 73.10, micro SLU-F1 35.8020, prompt tokens 2,190,161 and metered speech 2,884.793687 s identical on both arms. |
| the preregistered rule | "For each metric, the SLURP non-inferiority margin becomes the half-width of this null's own speaker-clustered CI90 on that metric. A future SLURP cell demonstrates an effect on metric m iff its CI90 is disjoint from this null's measured interval, not merely from zero." |
| primary result | intent accuracy 73.10 -> 73.60, paired speaker-clustered CI90 +0.5000 [-0.4049, +1.4341]; micro SLU-F1 35.8020 -> 36.0893, +0.2873 [-0.9088, +1.4521]. 1,000 rows, 124 speaker clusters, 10,000 replicates, seed 20260903. Raw completion identity 82.10 %; projected-intent flip rate 5.20 %. |
| margin used | **own-null (this cell measures it).** MEASURED here and published as the carrier's margins: intent 0.9195; scenario 0.8255; action 0.9790; micro SLU-F1 1.1804; micro entities-strict 1.2607; micro Word-F1 1.1317; micro Char-F1 1.2743; per-row SLU-F1 0.8188; per-row entities-strict 0.7696; per-row Word-F1 0.7983; per-row Char-F1 0.8743. They replace the imported +-0.60 pp on SLURP only, and the 28 % flip floor with the measured 17.9 %. |
| guards | falsifier PASS on 1,000 of 1,000 rows: the MODEL_REQUEST payload identical after removing `request_id` and `decoding_params.id_slot`, packet sha256 equal, per-row prompt tokens equal with a delta histogram of exactly {0: 1000}; identity gate PASS on the comparator's nine published anchors. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 model calls of 1,050 registered; 2,884.7937 of 3,000 speech-audio seconds; 0.0637 GPU-h of 1.0 registered against a 0.30 stop threshold; paid API spend 0. |
| named next step | re-read every open SLURP claim against the section 4 table (KV-0 first, then KU-S3, KU-S4 and the logprob probe); restate the per-scenario harm bound or drop it as a gate; and measure Audio2Tool's null, the third carrier and the only one still without one. |
| note | Eleven of eleven metrics moved UP under a pure null, and the imported +-0.60 pp bar was too narrow on every one of them, by 1.28x to 2.12x - too narrow being the direction that lets a null through. |

### Stage-2 construction

#### SLURP-KC-S1B - KC-S1b - the per-intent TRAIN slot schema on a separate slot contact

| field | value |
|---|---|
| **status** | **ADMITTED** |
| status is quoted from | section: Verdict |
| the verdict's own words | **KC-S1b is ADMITTED**, on both preregistered conditions and with a large margin, and it is the first mechanism in this study to move SLURP's slot layer at all. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1` |
| verdict note | `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-slurp-use2-slot-stage-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/result-summary.json` |
| comparator and its sealed numbers | the sealed closed-list direct baseline SLU-F1 35.80 (entities strict 21.91 / Word-F1 33.69 / Char-F1 38.20) and the equal-contact control KC-S1a at 35.75; the locked BLEND cell is 41.69. |
| the preregistered rule | "ADMITTED - KC-S1b only: its SLU-F1 paired CI90 lower bound is above 0 against the closed-list baseline on NEW500 and the (KC-S1b - KC-S1a) lower bound is above 0 on the same population. The schema, not the contact, has to be the lever." |
| primary result | SLU-F1 44.35 against 35.80 (+8.55) under the official `evaluate.py`; paired per-sample slot F1 on the unexposed NEW500 +10.11 pp, CI90 [+8.11, +12.19], sign test p = 8.5e-16, 60 saves / 2 harms - condition 1 met; against KC-S1a on NEW500 +10.02 pp, CI90 [+8.01, +12.10], p = 9.1e-15, 60 saves / 3 harms - condition 2 met. 10,000 replicates stratified by gold scenario, seed 20260903. |
| margin used | **none (zero-referenced); the carrier's own null landed four days later.** The rule reads lower bounds against zero. SLURP's own null was measured only on 2026-09-09; its micro SLU-F1 margin of 1.1804 pp is far below this effect, but the cell was decided before it existed. |
| guards | intent identical by construction and asserted row by row at 71.40 on all three arms, every paired intent contrast exactly 0.00 with CI90 [0.00, 0.00]; the port-vs-official identity check passed on all five scored sets; zero skipped rows and zero unparsed in the joined view. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 flown contacts (1,206 of 1,300 registered, 206 of them an aborted attempt); 2,884.7937 audio seconds per pass; about 0.20 GPU-h plus the aborted attempt's 206 calls / 552.9527 s; one recovery re-registration used after a CUDA fault killed the server mid-roster. |
| named next step | KC-S1b becomes the SLURP slot mechanism the next cells build on - USE-2b (the model's own transcript as the extraction source), USE-2c (the top-2 union schema), KU-S3 and EVO-S1. Rung 1 of the claim ladder only; rung 2 is a same-roster replication at a different serving geometry. |
| note | First admitted mechanism of the three-dimension program; precision and recall rise together (29.98 -> 37.54 and 17.26 -> 26.95). Still 19.67 points under the weakest published trained pipeline (Google/SF-ID 64.02). |

### Stage-2 construction (equal-contact control)

#### SLURP-KC-S1A - KC-S1a - a second slot-only contact with no schema

| field | value |
|---|---|
| **status** | **NULL** |
| status is quoted from | section: Verdict |
| the verdict's own words | **KC-S1a is null, exactly as it should be.** One extra contact that asks for slots alone ... moves the slot layer by **+0.09 pp** on NEW500 (CI90 [-0.20, +0.38], 2 saves / 1 harm) and **-0.09 pp** pooled. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` |
| verdict note | `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-slurp-use2-slot-stage-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/result-summary.json` |
| comparator and its sealed numbers | the sealed closed-list direct baseline: SLU-F1 35.80, entities strict 21.91, intent 71.40. |
| the preregistered rule | "ADMITTED - KC-S1b only: its SLU-F1 paired CI90 lower bound is above 0 against the closed-list baseline on NEW500 and the (KC-S1b - KC-S1a) lower bound is above 0 on the same population ... NULL - either interval includes 0." |
| primary result | per-sample slot F1 on the unexposed NEW500: +0.09 pp, CI90 [-0.20, +0.38], 2 saves / 1 harm; -0.09 pp pooled. SLU-F1 35.75 against the baseline's 35.80. Intent identical by construction and asserted row by row at 71.40 on all three arms. |
| margin used | **none (zero-referenced).** The rule reads a lower bound against zero; SLURP had no measured null in September. |
| guards | the port-vs-official identity check passed on all five scored sets at an absolute difference of 0.0; the CLOSED-LIST row reproduces its own 2026-09-05 verdict to the second decimal on all seven metrics; zero skipped rows. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 contacts of 1,050 registered; 2,884.7937 audio seconds; about 0.15 GPU-h; 1,000 contacts in 531.3 s. |
| named next step | it is the control every KC-S1b delta is stated net of: a second look at the same audio with the same information is worth nothing. |
| note | The contact-count control that makes the KC-S1b claim attributable to the schema rather than to the extra contact. |

### Stage-2 consumption

#### SLURP-KU-S1 - KU-S1 (BLEND-CL) - the alpha-blend knowledge-supply cell

| field | value |
|---|---|
| **status** | **CLOSED (refused before registration; UNREAD - neither ADMITTED nor NULL nor HARMFUL)** |
| status is quoted from | section 6 |
| the verdict's own words | KU-S1 ... **never flew, and is UNREAD** - neither ADMITTED nor NULL nor HARMFUL. It was refused on a measured, structural blocker before it had an exposure row |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-SLURP-KU-S1-CONTAINMENT-ANALYSIS-V1` |
| verdict note | `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-consumption-ku-s1-v1/result-summary.json` |
| comparator and its sealed numbers | none - the cell never flew and has no arm. |
| the preregistered rule | the snapshot-containment rule: supply must travel the traced typed-content channel, and a `KbFacetProvider` packet renders `KnowledgeValue.content` verbatim into `plan.instruction`. |
| primary result | the blocker, measured: 11,514 of 11,514 knowledge values are at or over 8 characters, i.e. protected material by construction, and a measured top-5 block is 3,224 characters carrying 19 distinct protected payloads; under `slurp-kb-size-full` 78 of 1,000 rendered phase-2 control turns collide. |
| margin used | **not applicable.** Not applicable. |
| guards | the containment analysis spent zero model, GPU, tool, embedding, network, audio and gold contacts. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | zero contacts of every kind - the cell was refused before it had an exposure row. |
| named next step | the fix is named and not done: render supply through `rails.runner._agent_messages`'s typed content blocks (enabler E6, traced supply), which precedes every knowledge-supplying phase cell on this carrier. |
| note | A refusal on a measured structural blocker, not a judgment call, and not by relaxing any rule. |

### Stage-2 consumption (equal-contact control)

#### SLURP-KU-S1C - KU-S1c - the two-contact draft-revise control with no knowledge

| field | value |
|---|---|
| **status** | **REPORTED, NEVER DECIDED** |
| status is quoted from | section: Verdict |
| the verdict's own words | **KU-S1c is reported, never decided** - it carries no admission gate; it is the equal-contact, no-knowledge control every two-contact SLURP cell's delta is now stated net of. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` |
| verdict note | `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-consumption-ku-s1-v1/result-summary.json` |
| comparator and its sealed numbers | the sealed closed-list direct baseline: intent 71.40, SLU-F1 35.80; and its own draft phase at intent 72.60, SLU-F1 35.51. |
| the preregistered rule | no admission gate - the cell is registered as a control, and the preregistration says so. |
| primary result | intent 72.90 against the baseline's 71.40: +1.50 pooled, CI90 [+0.30, +2.70]; +1.60 on the unexposed NEW500, CI90 [-0.20, +3.40] - the interval includes zero. Against its own draft the revise contact moves intent +0.30 pp pooled, CI90 [-0.40, +1.00]. SLU-F1 35.92 against 35.80, +0.12. |
| margin used | **none (control).** A control with no gate. |
| guards | the port-vs-official identity check passed on all three scored sets (absolute difference 0.0, 0.0 and 5.6e-17); the CLOSED-LIST row reproduces its own verdict to the second decimal; zero skipped rows. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 2,000 contacts of 2,100 registered; 5,769.5874 of 6,000 audio seconds; about 0.3 of 1.0 GPU-h; 0 tool, 0 embedding, 0 paid spend. |
| named next step | every two-contact SLURP delta is stated net of this control; the finding it fixes is that a phase program changes two things at once against a `policy: "fixed"` direct arm - +1.20 of the +1.50 is the control turn and only +0.30 is the second contact. |
| note | Contacts are not the lever on SLURP; constructed knowledge is (KC-S1b, +8.55 SLU-F1). |

### Stage-2 evolution (training-free loop)

#### SLURP-EVO-S1-R1 - EVO-S1 round 1 - the slot-schema evolution loop

| field | value |
|---|---|
| **status** | **REJECT** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: REJECT. Two of the three conditions hold; the pooled targeted interval fails at exactly zero. |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-SLURP-EVO-S1-PROPOSER-V2`, `SAEA-SLURP-EVO-S1-FOLD-A-V2`, `SAEA-SLURP-EVO-S1-FOLD-B-V2` |
| verdict note | `docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md` |
| preregistration | `docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1` |
| comparator and its sealed numbers | the round's incumbent A_0 flown over the same fold rows through the same harness; scorer `slurp-slu-official-train`, both arms passing the port/official identity check (SLU-F1 absolute difference 0.0 and 5.6e-17). |
| the preregistered rule | three conditions: "pooled targeted CI90 lower bound strictly above 0" AND "every admitted scenario, harms - saves <= 2 on its own 60 rows" AND "unadmitted scenarios pooled >= -1.0 pp". |
| primary result | pooled targeted CI90 lower bound -0.000 pp (-9.25e-19) against a rule of strictly above 0; point estimate +2.500 pp, CI90 [-0.000, +5.417] on the 120 targeted rows, of which six moved up, two moved down and 112 tied. |
| margin used | **none (zero-referenced + fixed harm bound).** The conditions read a lower bound against zero and a fixed per-scenario harm count. |
| guards | condition 2 passes (news -2, social -2 against a bound of 2); condition 3 passes (unadmitted scenarios pooled -0.264 pp, CI90 [-1.024, +0.500] against >= -1.0 pp). Instrument finding: 1,019 of 1,080 fold-B rows were asked byte-identical questions and 286 of them (28.1 %) returned different text anyway, so of the eight rows that make up the pooled targeted contrast four are the mechanism and four are the decoder. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | propose 56 contacts over 54 draws; fold A 6,480 contacts (6 x 1,080); fold B 2,160 contacts (2 x 1,080); select and confirm model-free at 0 contacts. GPU hours are not stated in the verdict. |
| named next step | the stop rule reads `continue` (R_max is 4 and stopping wants two consecutive rejects), but nothing in the document authorizes round 2: A_1 = A_0, the round's portfolio is recorded and dropped, and every exposure row stays `consumed = no`. |
| note | The 28.1 % flip figure this cell measured on a longer-prompt arm was later corrected by the SLURP own-null replicate to 17.9 % on the comparator's own arm. |

### Stage-2 observation / harness module

#### SLURP-TAIL2S - Silence tail on the delivered clip (tail_silence_seconds 2.0)

| field | value |
|---|---|
| **status** | **NOT ADMITTED** |
| status is quoted from | first-paragraph |
| the verdict's own words | **NOT ADMITTED.** Run `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`, attempt `attempt-20260909T035340Z-95296f` |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1` |
| verdict note | `docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-silence-tail-v1/verdict/result-summary.json` |
| comparator and its sealed numbers | the sealed re-locked comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` (attempt attempt-20260905T060424Z-2c5596) at intent 73.10, scenario 82.60, action 74.60, micro SLU-F1 35.80, entities strict 21.91, word-F1 33.69, char-F1 38.20, unparsed 3. |
| the preregistered rule | "ADMITTED as a model-usage local optimization iff all three hold: (1) the CI90 lower bound on the intent delta is > +0.60 pp ...; (2) SLU-F1 does not worsen ... and scenario and action accuracy are both non-inferior on the same rule; (3) no scenario loses more than 3.0 pp of intent accuracy, and at most 2 of the 18 scenarios lose anything at all." |
| primary result | intent accuracy 73.10 -> 74.40 %, paired +1.3000 [+0.1934, +2.4262] speaker-clustered over 1,000 rows in 124 speaker clusters; [+0.2000, +2.4000] stratified by gold scenario; equal-stratum weighting +1.2747 [+0.2040, +2.3332]. The interval excludes zero and its lower bound does not clear the +0.60 pp bar. |
| margin used | **imported (Earnings-22 null) at decision; SLURP's own null measured the same day.** IMPORTED, NOT MEASURED at decision time: the +-0.60 pp figure is section 4.1's own, taken from the Earnings-22 same-request null's half-width on the same scale. SLURP's own null (intent half-width 0.9195) landed the same day and confirms the verdict for a measured reason. |
| guards | clause 2 non-inferiority at -0.60 pp, speaker-clustered CI90 lower bounds: SLU-F1 +0.1455 (inside), action -0.0987 (inside), scenario -0.6921 (OUTSIDE, by 0.09 pp). Clause 3 per-scenario harm bound: the rule allows at most 2 of 18 scenarios to lose intent and none by more than 3.0 pp; measured 5 losing scenarios with a worst of -10.2564 pp (takeaway, 4 harms of 39 rows), plus recommendation -3.3333 and iot -3.2787. BOTH gating guards fail, under both interval families. The media falsifier closes on all 1,000 rows: +2.0 s and exactly 32,000 samples per row, +26 prompt tokens on every row with no other value in the histogram. |
| harness-admission entry | module *silence tail on the delivered clip (tail_silence_seconds 2.0)*; switch `observe.<phase>.tail_silence_seconds null -> 2.0 (table: observe)`; status **HARMFUL**; barred from every default plan; provisional obligation UNMET (the recorded switch form has never been flown on this carrier) |
| citable sentence | none |
| GPU-hours and contacts | 1,000 calls of 1,050 registered; 4,884.7937 of 5,000 registered speech-audio seconds; 0.0687 GPU-h of 0.30 registered; prompt / completion tokens 2,216,161 / 26,215; paid API spend 0. |
| named next step | the SLURP same-request null - the blocking next cell, now flown - and the `takeaway` / `iot` regression, a small enumerable set of rows whose sealed outputs both arms already carry. |
| note | Every headline number ROSE and the cell is still refused: five gains above +4.9 pp sit beside five losses. This is a redistribution with a positive sum, and clause 3 is the clause that refuses to switch a redistribution on for everybody. The comparator does NOT move to the @ts2 media. |

### Stage-2 construction (execution complete; scientific verdict pending)

#### SLURP-KV-0 - KV-0 - the example-free slot-schema base

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1` |
| attempt | `attempt-20260909T062500Z-74bfac` |
| sealed at UTC | 2026-09-09T06:42:45Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1, sealed manifest sha256 088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08 -- the same roster, the same contacts, the same instruction bytes apart from the block's examples. No twin: KV-0 IS the null view. |
| the preregistered rule | KV-0 is a SUBTRACTION and is read against KC-S1b under the family's non-inferiority rule, not under a gain rule. NEUTRAL (and the family's base) iff the paired per-sample official SLU-F1 CI90 lower bound on the unexposed NEW500 is above the non-inferiority margin taken from the carrier's own null, with the normalized secondary agreeing in sign. ADMITTED if the lower bound is above 0 -- the five examples were costing the arm. HARMFUL if the upper bound is below the margin, in which case the whole family is re-designed around a block that keeps its examples and no KV cell above KV-0 flies. Intent is identical by construction on every arm and is asserted row by row. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-2 - KV-2 - TRAIN vocabulary cards

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV2-CARDS-DEV1000-V1` |
| attempt | `attempt-20260909T064623Z-2a0ef7` |
| sealed at UTC | 2026-09-09T07:13:59Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1 (the family base) with SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1, sealed manifest sha256 088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08 reported beside it; the form twin is SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1. |
| the preregistered rule | ADMITTED iff, on the unexposed NEW500, the paired per-sample OFFICIAL SLU-F1 CI90 lower bound is above 0 against the sealed KV-0 rows AND above 0 against the form twin SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1, with the normalized secondary slurp-slu-f1-normalized-v1 AGREEING IN SIGN on both (MF-10 section 4.1). NULL if any interval includes 0. HARMFUL if an upper bound is below 0. The twin contrast is read twice: on the whole roster, and on the construction-fixed stratum of rows whose predicted intent rotates its view in place, where the twin is volume-matched to the character. Intent is identical by construction and asserted row by row; a non-zero intent delta is a defect, not a result. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-2-TWIN - KV-2 form twin - vocabulary cards assigned to other types

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1` |
| attempt | `attempt-20260909T071753Z-548ca4` |
| sealed at UTC | 2026-09-09T07:44:55Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV2-CARDS-DEV1000-V1; the pair is the twin contrast of the KV-2 decision rule. |
| the preregistered rule | This arm carries no admission rule of its own: it exists to be subtracted from KV-2. It is reported with its own per-stratum table and its block-volume covariate. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-1 - KV-1 - TRAIN-derived type descriptions

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1` |
| attempt | `attempt-20260909T074825Z-0d2278` |
| sealed at UTC | 2026-09-09T08:08:50Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1 (the family base); the form twin is SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1. |
| the preregistered rule | ADMITTED iff, on the unexposed NEW500, the paired per-sample OFFICIAL SLU-F1 CI90 lower bound is above 0 against the sealed KV-0 rows AND above 0 against the form twin SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1, with the normalized secondary slurp-slu-f1-normalized-v1 AGREEING IN SIGN on both (MF-10 section 4.1). NULL if any interval includes 0. HARMFUL if an upper bound is below 0. The twin contrast is read twice: on the whole roster, and on the construction-fixed stratum of rows whose predicted intent rotates its view in place, where the twin is volume-matched to the character. Intent is identical by construction and asserted row by row; a non-zero intent delta is a defect, not a result. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-1-TWIN - KV-1 form twin - descriptions assigned to other types

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1` |
| attempt | `attempt-20260909T081235Z-583048` |
| sealed at UTC | 2026-09-09T08:34:16Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1; the pair is the twin contrast of the KV-1 rule. |
| the preregistered rule | This arm carries no admission rule of its own: it exists to be subtracted from KV-1. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-3 - KV-3 - TRAIN exemplars

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1` |
| attempt | `attempt-20260909T083938Z-401fca` |
| sealed at UTC | 2026-09-09T08:59:48Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1 (the family base); the form twin is SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1. |
| the preregistered rule | ADMITTED iff, on the unexposed NEW500, the paired per-sample OFFICIAL SLU-F1 CI90 lower bound is above 0 against the sealed KV-0 rows AND above 0 against the form twin SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1, with the normalized secondary slurp-slu-f1-normalized-v1 AGREEING IN SIGN on both (MF-10 section 4.1). NULL if any interval includes 0. HARMFUL if an upper bound is below 0. The twin contrast is read twice: on the whole roster, and on the construction-fixed stratum of rows whose predicted intent rotates its view in place, where the twin is volume-matched to the character. Intent is identical by construction and asserted row by row; a non-zero intent delta is a defect, not a result. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

#### SLURP-KV-3-TWIN - KV-3 form twin - another intent's TRAIN exemplars

| field | value |
|---|---|
| **status** | **PENDING - scientific verdict** |
| execution status | **FINALIZED / COMPLETED**; 1 scoring job succeeded, 0 failed; score values uninspected |
| status is quoted from | scientific verdict pending; execution completion is metadata only |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1` |
| attempt | `attempt-20260909T090318Z-b9657d` |
| sealed at UTC | 2026-09-09T09:22:21Z |
| flight study commit | `2afb4b5cdc33f13a73a9b5d11a246f9a6858868b` |
| exposure closure at snapshot | `consumed=no`; reconcile with completed runtime metadata |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json` |
| comparator and its sealed numbers | SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1; the pair is the twin contrast of the KV-3 rule. |
| the preregistered rule | This arm carries no admission rule of its own: it exists to be subtracted from KV-3. This records the original rule; recovery has not applied it or changed it. |
| primary result | The complete-manifest scoring job succeeded. No score value was inspected during recovery, and no scientific result or verdict is entered here. |
| margin used | **own-null attribution retained; population, estimator and process binding unresolved.** The own-null verdict section 4 historically states 1.1804 pp for pooled DEV1000 micro SLU-F1 and 0.8188 pp for its per-row estimand, superseding the imported reference in KV section 6.4. Those statements do not establish a matching NEW500 per-row margin or np4/process binding for this family. All seven treatment flights already exist; no margin or preregistration may be changed retrospectively to decide them. |
| guards | No scientific guard was evaluated in this recovery. Locate a prior KV-0 read/admission record and reconcile the predecessor gate before any family verdict. Later arms were finalized, but the inspected checkout has no record establishing that the required prior decision occurred. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,000 metered model contacts; 2884.7936875 speech-audio seconds; registered caps 1,050 contacts and 3,000 seconds. Realized GPU hours are not stated in the operational snapshot. |
| named next step | Reconcile the completed attempt with its consumed=no exposure row; locate any earlier read/decision or document the sequence deviation. Register any new model-free result read first. Preserve sealed artifacts and original rules; unresolved analysis remains descriptive until its authority is settled. |
| note | Execution complete does not mean scientific admission. This row is counted as flown and scientifically pending. Do not re-fly or re-score it merely to recover the history. |

### Stage-2 consumption (pending)

#### SLURP-KU-S3 - KU-S3 - speech-keyed TRAIN slot fillers as typed content

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | not decided - no verdict note exists |
| date | 2026-09-07 |
| ledger run id(s) | `SAEA-SLURP-KU-S3-VECTORS-V1`, `SAEA-SLURP-KU-S3-SNAPSHOT-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-slurp-kus3-wire-check/` |
| comparator and its sealed numbers | the re-locked closed-list comparator at intent 73.10 / SLU-F1 35.80, unchanged and un-re-run. |
| the preregistered rule | see the preregistration; not applied - the flight cell has not been registered. |
| primary result | not measured. |
| margin used | **own-null (declared, and it replaces the imported bar this preregistration was written against).** SLURP's own null, measured 2026-09-09: micro SLU-F1 1.1804 pp, per-row 0.8188 pp, intent 0.9195 pp. |
| guards | not evaluated. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | model-free preparation only: SAEA-SLURP-KU-S3-VECTORS-V1 and SAEA-SLURP-KU-S3-SNAPSHOT-V1, 0 calls and 0 GPU hours each. |
| named next step | re-read against the section 4 margins before it flies - it currently reads against an imported bar 1.3x to 2.1x too narrow. |

### Harness module

#### SLURP-LOGPROB - Logprob-as-judge probe - the frozen core's own per-token distribution recorded beside every answer

| field | value |
|---|---|
| **status** | **NOT ADMITTED** |
| status is quoted from | h1 |
| the verdict's own words | # Verdict — the SLURP logprob-as-judge probe: **NOT ADMITTED** |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1` |
| verdict note | `docs/readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-08-slurp-logprob-judge-probe-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-logprob-judge-probe-v1/` |
| comparator and its sealed numbers | The sealed closed-list direct request is unchanged except for decoding_params.logprobs=true and top_logprobs=5. The admission bars concern the confidence signal; the greedy own-null replicate is the latency reference, not a replacement task baseline. |
| the preregistered rule | Both preregistered conditions must hold for the whole-answer minimum logprob: intent-error AUROC >= 0.75 with CI90 lower bound >= 0.70, and precision at 86 flags > 72.09 percent with its CI90 lower bound strictly above 72.09 percent. Both conditions fail. |
| primary result | the preregistered rule, applied mechanically by admission_verdict over the preregistered primary statistic min_token_logprob, 1,000 DEV-1000 rows in 124 speaker clusters, 10,000 replicates, seed 20260908, CI90. ARM A: AUROC for intent error 0.6935 [0.6660, 0.7202] against a bar of >= 0.75 with lower bound >= 0.70 -- fails on both halves. ARM B: precision at 86 flags 51.1628 % [42.5287, 59.0909] against a bar of > 72.09 % with the lower bound strictly above -- fails by 20.93 pp with the whole interval under the bar. BOTH ARMS FAIL, so NOT ADMITTED |
| margin used | **none (fixed AUROC and precision bars); own null is the cost reference.** MEASURED, not imported. This row does not read a non-inferiority margin at all -- its rule is an AUROC bar and a precision bar, both fixed before the flight -- but it uses this carrier's own null for two things: as the wall-clock reference the decoding parameter's cost is measured against, and as the warning attached to the per-scenario table (that null moved intent by -5.13 to +5.41 pp across the same 18 strata with nothing changed). The 28.1 % flip floor the preregistration quoted is superseded by that null's measured 5.20 % projected-intent flip rate |
| guards | the four-row smoke was a GATE, not a formality: the cell would not have flown without it. 4 of 4 rows returned a choices[0].logprobs object ON THE SPEECH-FEATURE PACKET ROUTE, with exactly five alternatives on every one of 162 generated tokens, the first alternative equal to the sampled token throughout, four MODEL_LOGPROBS records whose logprobs_sha256 recomputes and whose requested_top_logprobs is 5, and the answer reconstructed from the token stream equal to the sealed text on 4 of 4. the flag also loses to a free judge on this arm's own rows: recomputed here, the legality judge flags 42 rows at 66.67 % precision and 10.57 % recall on intent error at zero cost and zero latency, against the confidence flag's 86 rows at 51.16 % and 16.60 %. The union of all three reaches 50.41 % at 123 flags -- adding the confidence flag to the deterministic judges lowers their precision |
| harness-admission entry | module *decode-confidence flag from the sealed trace (the judge replay-logprob-flag-v1, fed by decoding_params.logprobs / top_logprobs)*; switch `judges.<phase>.judges = ['replay-logprob-flag-v1'] (table: judges; OFF arm null)`; status **HARMFUL**; barred from every default plan because the admission gate failed; the recorded judge switch itself was not flown |
| citable sentence | none |
| GPU-hours and contacts | 1,000 contacts; 2,884.7936875 metered speech-audio seconds; 0.0690 GPU-h and 248.47 seconds wall. Compared with the greedy own-null replicate: +5.30 percent per-request latency, +8.33 percent wall, +8.35 percent GPU-h. |
| named next step | Use deterministic judges for the re-ask module. Any label-token successor needs its own frozen primary and fresh registered evidence; the retrospective label-token diagnostic does not admit this probe. |
| note | The scientific verdict remains NOT ADMITTED. Harness status HARMFUL means the module cannot enter a default plan; it does not claim measured answer degradation. Only the decoding parameter flew, and the judge was evaluated offline. The locked SLURP comparator does not change. |


---

## Audio2Tool

### Stage-1 alignment

#### A2T-CAL-400 - Direct-baseline calibration - four cells over Factor A (output contract) and Factor D (audio path)

| field | value |
|---|---|
| **status** | **NO CELL PASSES** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: NO CELL PASSES. The miss is the finding. |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-A2T-DIRECT-CALIBRATION-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-direct-baseline-calibration-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-03-a2t-direct-baseline-calibration-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-direct-calibration-400-v1/result-summary.json` |
| comparator and its sealed numbers | the Audio2Tool paper's Table 3 row per tier: tier1 92.4, tier2 84.6, tier3 74.7, tier4 33.4, tier5 90.6, tier6 81.5, tier7 54.6, tier8 41.7. |
| the preregistered rule | "at least one cell reaching per-tier tool-accuracy \|delta\| <= 5 pp against the paper row on tiers 1, 2, 5 and 6, with the tier rank order preserved" |
| primary result | overall tool accuracy on n = 400 per cell: A0'-legacy-raw 51.75, A1-native-raw 46.00, P0-legacy-packets 52.75, P1-native-packets 44.00. Summed absolute per-tier gap across all eight tiers: A0' 142.3 pp, P0 146.3, A1 185.5, P1 201.5. No cell meets the rule on any of the four decision tiers and no cell preserves the tier rank order. |
| margin used | **none (acceptance band).** A +-5 pp per-tier acceptance band against the paper row. |
| guards | the two protocol factors under test do not close the gap and one makes it worse: within raw audio the native `tools` contract costs -0.0575 of tool accuracy (46 saves / 69 harms / 285 ties, sign test p = 0.0398, CI90 [-0.1000, -0.0150]); the packet audio path is statistically null against raw audio. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,600 contacts of 1,608 planned and 1,700 registered; 8,638.752 speech-audio seconds of 9,000 registered; four attempts, all FINALIZED, none aborted. Realized GPU hours are not stated in the verdict; the registered ceiling is 6.0. |
| named next step | mechanism work stays stopped pending the owner's decision among Factor C (Q8_0), prompt-template variants, or a protocol clarification request to the paper's authors. |
| note | A 2026-09-04 correction appended after the official-protocol replication records that the flight path ignored a fragment's `task_instruction_template` field; it changes no number and no conclusion in this cell. |

#### A2T-OFFPROTO-400 - Official-protocol replication - the paper's released code, string for string

| field | value |
|---|---|
| **status** | **FAIL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: FAIL. But the protocol was the wrong suspect for most of the gap, and Tier 1 is now the whole story. |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-official-protocol-replication-400-v1/result-summary.json` |
| comparator and its sealed numbers | the paper's Table 3 row per tier, scored with the pinned release's own `metrics.py` (`a2t-toolcall-official`, git blob d98277bc..., commit b9d5383c...); and the sealed calibration cell A0prime on the same 400 rows. |
| the preregistered rule | "\|delta\| <= 5 pp against the paper row on tiers 1, 2, 5 and 6 with the tier rank order preserved" - section 7. |
| primary result | per-tier tool accuracy at n = 50 per tier with Wilson CI90: tier1 60.0 [48.4, 70.6] against 92.4 (-32.4); tier2 74.0 against 84.6 (-10.6); tier5 78.0 against 90.6 (-12.6); tier6 84.0 against 81.5 (+2.5). One of the four decision tiers passes, the rank order is not preserved, and the paper's value lies outside the Wilson CI90 on three of the four. Summed absolute gap across all eight tiers 77.3 pp, from the reconstruction's 116.3. |
| margin used | **none (acceptance band + Wilson CI90).** A +-5 pp per-tier acceptance band plus a Wilson CI90 containment read. |
| guards | mirroring the published protocol genuinely improves tool selection by +5.50 pp overall on the same 400 rows, paired, sign test p = 0.023, CI90 [+1.75, +9.25] pp - and Tier 1 moves the WRONG way, 66.0 -> 60.0 on the same rows and the same metric. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 400 contacts of 408 planned and 450 registered; 2,159.688 s of 2,300 registered; end-to-end wall 278 s; prompt tokens 3,660 per call against A0prime's 13,315. Realized GPU hours are not stated in the verdict; the registered ceiling is 1.0. |
| named next step | whether the paper's Tier-1 row is produced on a population this roster does not represent (first-speaker-per-query over every query) or under a candidate tool set narrower than all 152. Drawing that roster, or asking the authors, is an owner decision. |
| note | The published prompt is a third the size of the reconstruction (3,581 tokens against 13,236) and its output contract is different in kind (a call string against a JSON array). |

#### A2T-T1-POP-500 - Tier-1 official population (n = 500) and the whitespace variant

| field | value |
|---|---|
| **status** | **FAIL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: FAIL on both cells. But Tier 1 is no longer an unexplained gap - it is a smart_home gap, and it has a named cause. |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1`, `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-a2t-tier1-official-population-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier1-official-population-v1/result-summary.json` |
| comparator and its sealed numbers | the paper's tier-1 row 92.4, and the frozen-400 tier-1 measurement of 60.0 at n = 50. |
| the preregistered rule | the owner's 3-point alignment band: ALIGNED needs >= 89.4 against the published 92.4. |
| primary result | tier-1 tool accuracy 65.60 % at n = 500, CI90 [62.03, 69.00], against a published 92.4 - a delta of -26.80. The roster is worth +5.6 pp, not +32. The whitespace variant is worth nothing: paired over the same 400 rows, +1.00 pp, sign test p = 0.5034, CI90 [-0.75, +3.00] pp. |
| margin used | **none (alignment band + Wilson CI90).** The owner's 3-point alignment band plus Wilson CI90 containment. |
| guards | at n = 500 the tier splits by DOMAIN: `wearables` 93.41 [87.75, 96.55] on 91 rows and `smart_car` 92.68 [83.04, 97.04] on 41 rows both sit ON the published 92.4, while `smart_home` 55.71 [51.42, 59.91] on 368 rows sits 36.7 pp below it; equal-domain weighting 80.60. Exact match remains the sharper anomaly at 10.20 % [8.18, 12.64] against a published 92.4 %. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | T1 500 contacts of 540 registered and 1,668.914042 of 1,750 s; W 400 contacts of 410 registered and 2,159.688 of 2,250 s; end-to-end wall 330 s and 250 s. Realized GPU hours are not stated in the verdict; the registered ceilings are 1.2 and 0.8. |
| named next step | whether to spend the next flight on quantization (the registered probe), on a narrowed candidate set, or on asking the authors which corpus and which tool set produced Table 3, is an owner decision. |
| note | 161 of 163 smart_home misses name a real registry tool, half of them the same idea's twin in `smart_car`. The named component is near-synonym selection in a registry that contains near-synonyms. |

#### A2T-T258-POP - Tiers 2 / 5 / 8 official population (n = 500 per tier)

| field | value |
|---|---|
| **status** | **TIER 8 ALIGNED; TIERS 2 AND 5 FAIL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: tier 8 ALIGNED, tiers 2 and 5 FAIL - and on both failing tiers the shortfall is one stratum, not the tier. |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-tier258-official-population-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-a2t-tier258-official-population-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier258-official-population-v1/result-summary.json` |
| comparator and its sealed numbers | the paper's rows tier2 84.6, tier5 90.6, tier8 41.7, and the degraded-model floors Qwen-2.5-Omni-7B 80.6 / 74.1 / 36.5. |
| the preregistered rule | the owner's 3-point alignment band: tier2 needs >= 81.6, tier5 >= 87.6, tier8 >= 38.7. |
| primary result | tier2 79.60 [76.48, 82.40] against 84.6 (-5.00, FAIL); tier5 80.80 [77.74, 83.53] against 90.6 (-9.80, FAIL); tier8 46.80 [43.16, 50.48] against 41.7 (+5.10, ALIGNED). n = 500 per tier, official scorer, 1,499 of 1,500 rows parsed (99.93 %). |
| margin used | **none (alignment band + Wilson CI90).** The owner's 3-point alignment band, with Wilson CI90 containment deciding CONSISTENT-WITHIN-NOISE. |
| guards | the floor rule: tier2 sits 1.00 pp UNDER Qwen-2.5-Omni-7B's published 80.6 and is called out as the rule requires, though its CI90 contains 80.6; tier5 clears by 6.70 and tier8 by 10.30; no tier is below the weakest published SpeechLM row. Neither failing tier is CONSISTENT-WITHIN-NOISE: 84.6 and 90.6 both sit outside their Wilson CI90. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 1,500 contacts of 1,560 registered (1,508 planned); 9,784.337875 of 9,900 s. Realized GPU hours are not stated in the verdict; the registered ceiling is 1.5. |
| named next step | the three tiers the frozen 400 could not decide are now decided; smart_home is the weak stratum on every tier. |
| note | Tier 8 is the first Audio2Tool tier this repository has landed ALIGNED under the owner's rule, and it clears the band by 5.1 points. |

#### A2T-T3467-POP - Tiers 3 / 4 / 6 / 7 official population (n = 500 per tier)

| field | value |
|---|---|
| **status** | **FAIL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: all four tiers FAIL on the natural mixture, and all four would be ALIGNED on an equal-domain one. |
| date | 2026-09-04 |
| ledger run id(s) | `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-tier3467-official-population-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-a2t-tier3467-official-population-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier3467-official-population-v1/result-summary.json` |
| comparator and its sealed numbers | the paper's rows tier3 74.7, tier4 33.4, tier6 81.5, tier7 54.6, and the Qwen-2.5-Omni-7B floors 50.2 / 22.4 / 68.3 / 48.2. |
| the preregistered rule | the owner's 3-point alignment band: tier3 needs >= 71.7, tier4 >= 30.4, tier6 >= 78.5, tier7 >= 51.6. |
| primary result | tier3 65.00 [61.42, 68.42] against 74.7 (-9.70); tier4 28.20 [25.01, 31.62] against 33.4 (-5.20); tier6 75.80 [72.52, 78.81] against 81.5 (-5.70); tier7 49.40 [45.74, 53.07] against 54.6 (-5.20). All four FAIL and not one is CONSISTENT-WITHIN-NOISE. n = 500 per tier, 1,992 of 2,000 rows parsed (99.60 %). |
| margin used | **none (alignment band + Wilson CI90).** The owner's 3-point alignment band, with Wilson CI90 containment deciding CONSISTENT-WITHIN-NOISE. |
| guards | the floor rule: no tier is below a degraded model's published number; tier7 clears Qwen-2.5-Omni-7B by only 1.20 pp, which is inside its own sampling error and is the row to watch; the other three clear by 5.8 to 14.8. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 2,000 contacts of 2,080 registered (2,008 planned); 11,964.831167 of 12,100 s. Realized GPU hours are not stated in the verdict; the registered ceiling is 2.0. |
| named next step | the eight-tier table is complete at one resolution: one tier ALIGNED and seven FAIL on the natural mixture. |
| note | At n = 50 all four of these tiers sat INSIDE the owner's 3-point band and none of them could be believed; that is exactly what n = 500 was bought for. |

### Stage-1 own null

#### A2T-NULL - Audio2Tool's own same-request null

| field | value |
|---|---|
| **status** | **NOT MEASURED** |
| status is quoted from | named as the open item by both carriers that did measure theirs |
| date | not measured |
| ledger run id(s) | none registered |
| verdict note | none |
| comparator and its sealed numbers | none - the cell does not exist. |
| the preregistered rule | not registered. |
| primary result | not measured. |
| margin used | **none - the carrier has no measured null.** Audio2Tool has no measured own null, so every Audio2Tool cell in this ledger reads its CI90 against ZERO rather than against a carrier-measured band, and no other carrier's margins travel to it. |
| guards | not applicable. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | zero - not registered and not flown. |
| named next step | "Audio2Tool still has no measured null. This is now the second carrier of three where the imported margin was demonstrably wrong. There is no reason to expect it is right on the third." |
| note | Carried as an explicit row because its absence is what makes every Audio2Tool interval in this ledger zero-referenced. |

### Stage-2 construction

#### A2T-KC-A1 - KC-A1 inline contrast notes, with KC-A1c the token-matched form twin

| field | value |
|---|---|
| **status** | **NULL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: NULL, and the form twin is the reason the null is worth reading |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-A2T-KC-A1-CONTRAST-NOTES-V1`, `SAEA-A2T-KC-A1C-CATEGORY-ONLY-V1` |
| verdict note | `docs/readiness/2026-09-05-a2t-kc-a1-contrast-notes-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-a2t-kc-a1-contrast-notes-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/result-summary.json` |
| comparator and its sealed numbers | each row's own sealed official-protocol output over the same 4,000 rows: pooled tool accuracy 61.40 %; equal-domain 68.11. |
| the preregistered rule | "ADMITTED: the pooled CI90 lower bound is above 0, both weightings agree in sign, AND at least half of the [gain is on target pairs] ... NULL: the CI90 includes 0, or the weightings disagree, or the target-pair share is below 0.5." |
| primary result | total (KC-A1 - sealed baseline) +0.42 pp, CI90 [-0.12, +0.97], 101 saves / 84 harms / 3,815 ties, sign p = 0.2394; form (KC-A1c - baseline) +0.25 pp [-0.30, +0.80]; content (KC-A1 - KC-A1c, paired) +0.17 pp [-0.38, +0.70]. Baseline 61.40 -> KC-A1 61.825, with KC-A1c 61.65 between them. Tier-stratified bootstrap, 10,000 replicates, seed 20260903. |
| margin used | **none (zero-referenced + share threshold); this carrier has no measured null.** The rule reads the pooled CI90 against zero plus a target-pair share threshold of 0.5. |
| guards | the pooled CI90 includes zero; the target-pair share of the gain is 0.198 against a required 0.5; the content contrast's CI90 lower bound is below 0, so no part of the movement is credited as content (`content_effect_credited: false`). Equal-domain weighting agrees in sign: +0.29 pp [-0.34, +0.93] for KC-A1 and +0.15 pp [-0.48, +0.77] for KC-A1c. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 4,000 contacts of 4,200 registered per arm; 23,418.083083 of 24,600 s per arm; generation wall 3,970 s (KC-A1) and 2,803 s (KC-A1c); prompt tokens 3,709.74825 per call in BOTH arms, identical to five decimal places over 14,838,993 tokens each. Realized GPU hours are not stated in the verdict. |
| named next step | program section 4a routes a NULL with separability >= 0.80 to EVO-A1 from the official baseline, which is where this goes; a rewrite that separates `setColor` from `setLighting` is worth more than any number of notes that separate either from `setAmbientLighting`. |
| note | The first MEASURED form cost in the study: a same-shape token append is nearly free (+0.25 pp, CI90 [-0.30, +0.80]), which retires the working assumption that ORG-1's three points were partly a length tax. They were structure. |

### Stage-2 model usage

#### A2T-Q8 - Q8_0 quantization probe (Factor C)

| field | value |
|---|---|
| **status** | **QUANTIZATION-EXCLUDED** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: QUANTIZATION-EXCLUDED. And Tier 1 did not move by a single row. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-A2T-Q8-QUANTIZATION-PROBE-V1` |
| verdict note | `docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-q8-quantization-probe-400-v1/result-summary.json` |
| comparator and its sealed numbers | the sealed `R-official-raw` cell of the official-protocol replication on the same frozen 400 rows, byte-identical in request: prompt tokens 1,464,049 on both flights to the digit, same rendered prompt hash after substituting the sealed session's media-marker nonce, same mmproj sha256, same geometry. |
| the preregistered rule | section 6: if the paired CI90 on the four acceptance tiers contains zero, the outcome is QUANTIZATION-EXCLUDED - the residual gap is not the decoder quantization. |
| primary result | on the four acceptance tiers, C-q8 minus R-official-raw is +0.50 pp of tool accuracy, 4 saves / 3 harms / 193 ties, sign test p = 1.0000, tier-stratified paired bootstrap CI90 [-1.50, +2.50] pp. The interval contains zero. |
| margin used | **none (zero containment).** The rule is a containment read on the paired CI90. |
| guards | Tier 1 is 60.0 % on Q4_K_M and 60.0 % on Q8_0 with zero saves, zero harms and all fifty rows landing on the same side; `wearables` is 72.63 % both ways on 95 rows with zero discordant pairs. The audio never re-entered the encoder: the feature-cache directory held 5,617 entries before and after and the server log carries zero `encoding` lines. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 400 contacts of 408 planned and 450 registered; 2,159.688 s of 2,300. Realized GPU hours are not stated in the verdict; the registered ceiling is 4.0. |
| named next step | the Q4_K_M core stays the operating core; the tier-1 anomaly is not the decoder quantization and the remaining suspects are the llama.cpp audio front end against the HF processor, and the published tier-1 row itself. |
| note | The one tier that carries the whole unexplained gap is the one tier the decoder quantization does not touch at all. |

### Stage-2 observation (pending)

#### A2T-16K - Input-rate standardization cell (a) - 16 kHz media

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | registered; the flight row is open (consumed = no) and no verdict note exists |
| date | 2026-09-09 |
| ledger run id(s) | `SAEA-A2T-OFFICIAL-PROTOCOL-16K-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-07-a2t-input-rate-standardization-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-a2t-input-rate-16k-wire-check/` |
| comparator and its sealed numbers | the sealed `R-official-raw` official-protocol cell on the frozen 400. |
| the preregistered rule | see the preregistration; not applied - the cell has not been read. |
| primary result | not measured. |
| margin used | **none - the carrier has no measured null.** None available - Audio2Tool has no measured own null. |
| guards | not evaluated; the model-free input-rate audit and the 16 kHz media build are receipted. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceiling 408 calls / 2,400 speech-audio seconds / 0.2 GPU hours, plus an 8-call smoke row. |
| named next step | Audio2Tool is the only carrier in this study whose audio is resampled by llama.cpp, and the resampler that does it is the one miniaudio itself labels "fastest, lowest quality". |

### Stage-2 evolution (pending)

#### A2T-EVO-A1 - EVO-A1 - the tool-description evolution loop

| field | value |
|---|---|
| **status** | **PENDING** |
| status is quoted from | registered; all five flight rows are open (consumed = no) and no verdict note exists |
| date | 2026-09-06 |
| ledger run id(s) | `SAEA-A2T-EVO-A1-PROPOSER-V1`, `SAEA-A2T-EVO-A1-FOLD-A-V1`, `SAEA-A2T-EVO-A1-FOLD-B-V1`, `SAEA-A2T-EVO-A1-CURVE-400-V1`, `SAEA-A2T-EVO-A1-FINAL-4000-V1` |
| verdict note | none |
| preregistration | `docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/` |
| comparator and its sealed numbers | the sealed official-protocol baseline at pooled tool accuracy 61.40 %. |
| the preregistered rule | see the preregistration; not applied - no round has been decided. |
| primary result | not measured. |
| margin used | **none - the carrier has no measured null.** None available - Audio2Tool has no measured own null. |
| guards | not evaluated; the model-free construction-capacity and decontamination rows are closed. |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | registered ceilings, run-cumulative across every attempt: proposer 80 calls / 400 s / 0.1 GPU-h; fold A 10,176 / 48,397 / 2.5; fold B 3,344 / 15,604 / 1.0; curve 1,600 / 13,882 / 0.8; final 4,008 / 23,419 / 1.0. All five rows are `consumed = no`. |
| named next step | KC-A1's NULL routes here: a rewrite that separates same-domain twins, from the official baseline. |

### Stage-2 construction (ORG)

#### A2T-ORG-1 - The domain-grouped tool registry

| field | value |
|---|---|
| **status** | **HARMFUL** |
| status is quoted from | section: Verdict |
| the verdict's own words | ## Verdict: HARMFUL. The domain cue does exactly what H1 said it would, and it still costs 3.23 points. |
| date | 2026-09-05 |
| ledger run id(s) | `SAEA-A2T-ORG1-DOMAIN-GROUPED-V1` |
| verdict note | `docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-verdict.md` |
| preregistration | `docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-preregistration.md` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-4000-v1/result-summary.json` |
| comparator and its sealed numbers | each row's own sealed official-protocol output over the 4,000-row official population: pooled tool accuracy 61.40 %; equal-domain weighting 68.11. |
| the preregistered rule | "HARMFUL: the CI90 upper bound is below 0. ORG-1 is dropped and the reason ... is recorded here before A2T-ORG-2 is registered." |
| primary result | pooled official tool accuracy 61.40 -> 58.17 %, delta -3.23 pp, tier-stratified bootstrap CI90 [-4.15, -2.33], 194 saves / 323 harms / 3,483 ties, exact sign test p < 0.0001, 10,000 replicates, seed 20260903. Equal-domain weighting 68.11 -> 65.04, -3.07 pp [-4.12, -2.01]. |
| margin used | **none (zero-referenced); this carrier has no measured null.** The rule reads the CI90 upper bound against zero; Audio2Tool has no measured own null. |
| guards | every domain loses - `smart_home` -3.26, `wearables` -3.38, `smart_car` -2.56 - and `wearables` has 13 tools and the fewest confusable neighbours of any domain, so a cue that only supplied domain knowledge could not cost 3.4 points there. The mechanism does fire: cross-domain twin misses fall 621 -> 521 (-16 %) and the named cross-domain pairs collapse 183 -> 113 (-38 %), while same-domain twin misses rise 898 -> 1,118 (+24 %). |
| harness-admission entry | none |
| citable sentence | none |
| GPU-hours and contacts | 4,000 contacts of 4,200 registered (4,008 planned); 23,418.083083 of 24,600 registered speech-audio seconds; generation wall 2,586 s; 3,752.7 prompt tokens per call; 26 parse failures of 4,000. Realized GPU hours are not stated in the verdict. |
| named next step | A2T-ORG-2 is registered against the official-protocol baseline, not against ORG-1, and its contrast notes must target the SAME-domain twins, because that is where 1,118 of the 1,673 misses now live. |
| note | One methodological caution now measured rather than assumed: a prompt-form change that supplies real, correct, release-authored knowledge can cost three points on this carrier, so any later ORG or SUPPLY mechanism that changes the shape of the registry block owes a same-shape control. |

---

## Cross-checks reported, not fixed

`scripts/checks/results_ledger_check.py` recomputes all four findings below from the repository on every run and prints them; they are findings, not failures, and this ledger fixes none of them.

**A. Verdicts whose first line does not carry the status word - 23 of the rows above.** Only fifteen statuses in this ledger were parsed out of a verdict's H1 or its opening paragraph. In every other case the word lives under a `## Verdict` heading, in a section 0 table, or in a later section, and the `status is quoted from` field of the row records exactly where. The pattern is carrier-shaped: the Audio2Tool verdicts and several historical SLURP verdicts put the status under `## Verdict`; the SLURP logprob verdict states NOT ADMITTED in its H1, while the Earnings-21 mechanism verdicts put it in the title. Two instrument cells (the Earnings-21 and SLURP own-null replicates) carry no status word at all, and say so in so many words: "there is none: this cell admits and refutes nothing".

**B. Cells with a closed ledger row and no verdict note - two.** `SAEA-E21-TOOL-DIARIZATION-V1` (the pinned Sortformer diarization tool row, closed 2026-09-07, whose unit plan OBS-E1 then flew; documented only in `docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md`) and `SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1` (the MF-7 embedder contacts; documented only in `docs/readiness/2026-09-06-slurp-consumption-ku-s1-v2-preregistration.md`). Both are tool rows rather than cells, which is why neither owes a verdict under the current convention - but the convention is not written down anywhere, and that is the finding.

**C. Harness-admission entries with no ledger row - none.** All four entries of `docs/receipts/harness-admission.json` resolve to a closed exposure-ledger row and carry a row here: KC-E1f v2 (ADMITTED), the cross-call dispatcher (NEUTRAL), the SLURP silence tail (HARMFUL), and the SLURP logprob probe (harness HARMFUL; scientific NOT ADMITTED).

**D. Umbrella disagreements - none at the owner recovery check.** All 35 rows that declare umbrella headline values are carried by the current umbrella page, to trailing-zero formatting. This supersedes the ledger's earlier cross-check finding of two missing projection values; it changes no scientific result. The published-baselines page was read-only in this cross-check; separate umbrella current-routing updates point to the recovered plan and ledger.

## What this ledger is not

It is a transcription, not an analysis: it recomputes no interval, re-weights no stratum and issues no verdict of its own. Where a verdict and the umbrella page state the same headline, the check compares them and reports any disagreement; it never edits the umbrella.

## Superseded owner continuation note: early 2026-09-10

This paragraph predates the source-bound current continuation table at the top and is retained as history.

The tables above retain the historical recovery transcription. Current KU-S3 max256 recovery is **ADMITTED_COMPONENT**: three new 1,000-row arms completed and scored once each, two registered NEW500 row-SLU-F1 contrasts pass, and the inherited joined-intent protection is verified without changing entity predictions or original outputs. See the [component verdict](../checks/speech-aware-evidence-acquisition/2026-09-10-ku-s3-max256-recovery-verdict/README.md). Live full-system and inherited replication requirements remain open. KV recovery is complete in the [family report](../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md); historical missing decisions remain explicit.

## Original-result reproduction: 2026-09-10

The [independent reproduction report](2026-09-10-fable-reproduction-audit.md) and [source-bound receipt](../receipts/fable-result-reproduction-v1.json) reproduce the original KC-S1b contrasts, existing max64 repeat analysis, E21 KC-E1f original rule and historical v2 redecision, and KV recovery contrasts. All 16,560 statistical fields agree. No fresh inference or official scoring was performed. Preserve the original rejection/redecision sequence, the historical KV order deviation and the distinction between component evidence and live system performance. The +10.11 pp KC-S1b headline denotes strict entity mean row F1; do not relabel it as official micro SLU-F1.

## September 13: complete native-system candidate

EXPLORATORY_SYSTEM_CANDIDATE. Direct and native system each completed DEV1000 and received one complete official score. Primary NEW500 micro improves by 14.429673 percentage points and joint intent by 6.2 points; both frozen lower-bound conditions pass. Same-roster replication is next. See [the verdict and all scenario tables](../readiness/2026-09-13-slurp-direct-vs-native-system-v1-verdict.md). This continuation preserves historical rows and does not establish component causality/generalization.

## September 14: complete TRAIN Fold A native anchor

COMPLETE_TRAIN_CONSTRUCTION_ANCHOR. The sole CUDA/reboot recovery completed all 1,080 ordered samples, 5,417 model calls and one official full score. Natural-mixture official SLU micro F1 is 48.53363%, intent accuracy 77.96296%, C0 coverage 86.75926%, covered-set final intent accuracy 89.86126%, and full intent/entity exact match 29.35185%. These are anchor levels, not a same-roster direct-model effect. The original failed five-contact attempt remains separate. All 18 scenario strata, actual initial knowledge support and source pins are in [the complete result](2026-09-14-slurp-native-train-a-anchor.md). Root admits one same-roster complete-system refresh/tools successor; Fold B remains untouched and no training-free optimization cycle is yet complete.

## September 14: native refresh/tools first attempt interrupted

ABORTED_ENGINEERING_FAILURE. The TRAIN A successor stopped after 86 model debits, 344 capacity endpoints and one CPU ASR debit. A valid candidate list failed inside the framework schema formatter before its source-bound handler. No completed task result, comparison or score exists. Root preserved original traces and exposure and admitted the sole same-method recovery after four actual-framework synthetic proof rows and 73 related passing tests. See [recovery protocol and accounting](../readiness/2026-09-14-slurp-native-candidate-refresh-tools-train-fold-a-recovery-v1/README.md). No task metric or scientific threshold changed.

## September 15: repeated useful SLURP agent base

The max512 native dual-store base replication passes the unchanged exploratory rule: NEW500 official micro F1 +14.7970 pp, speaker CI90 [11.5245, 18.0112], DEV1000 +14.6233 and equal-scenario +12.1257. Both complete first-score artifacts and all strata are retained in [the root verdict](2026-09-14-slurp-dual-store-base-replication-verdict-v1.md). The original same-package pair is positive separately; no pooled rescue or generalization claim. Audio2Tool [engineering proof](2026-09-15-a2t-native-role-engineering-proof-v1.md) is sealed with no task-quality result; full4000 remains pending registration.

## September 15 native Audio2Tool complete comparison

| Cell | Decision | Complete result | Source |
| --- | --- | --- | --- |
| A2T-NATIVE-ROLE-BASE-UNION4000-V1 | **PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED** | Official primary-call exact18.50% to22.55%; gain4.05pp, paired query-cluster CI95[2.963,5.165]. Both primary lower-bound checks pass the1.0pp threshold, but official tool accuracy declines3.60pp and fails the original point guard. The complete system has optimization space; stable adoption and isolated component effects are not established. | [Primary decision](2026-09-15-a2t-native-role-primary-decision-v1.json), SHA-256 dbb8edc282370ecf779d8794888e3694f82fccdceba6a397b7f4a60245ca7c43; [full report](2026-09-15-a2t-native-role-base-full4000.md) |

Both raw arms are FINALIZED with4,000 rows and one first complete official scoring batch each. Repo-v2 normalized call-multiset exact improves14.60% to18.50%; its semantics differ from official primary-call exact and do not enforce order. Preserve the original aborted attempt and all exposure. Candidate attribution is still being closed independently; no new GPU work is authorized by this result.


## 2026-09-16: SLURP TRAIN A review-stage attribution

[Complete report](2026-09-16-slurp-train-a-review-stage-attribution.md).
Model-free analysis of the released full1080 native anchor; no official rescore.
Five actual Solver revisions produce zero new fully correct answers and one intent harm.
Two partial slot diagnostics improve and one declines; all failures and all18 strata remain.
Root personally reviewed all revised trajectories. This diagnoses the review-decision-use
chain and does not isolate a Reviewer causal effect or admit a successor. The maximum-five
candidate experiment remains running; its quality has not been read.


## 2026-09-16: SLURP review context provenance

[Root source audit](2026-09-16-slurp-review-context-provenance.md) traces an unsupported
illustrative filler to the legacy global task contract, separate from both released
semantic stores. All five revised episodes were examined. Candidate label/description
mismatch and hypothesis/evidence confusion are also observed; isolated causal effects
and prevalence remain unmeasured. Prepare a consistent opt-in global contract without
example fillers, preserving the complete legal inventory and historical defaults.
No new generation, official score, quality verdict or Track B launch is created.

## September 16: maximum-five candidate contrast closed

NOT_ADVANCED. Complete TRAIN A1080 candidate coverage increases 937 to 951, but official
pooled SLU changes only +0.08674 pp, speaker CI95 [-1.36499, 1.65097]. Final intent decreases
842 to 837. Only three of 19 newly covered rows finish correct. Seven actual revisions yield
two intent saves and one full-answer save; there are no binding slot-value cap discards.
Keep the maximum-three incumbent. Root selects one typed-context/evidence-review system
package versus matched direct for prospective admission. Read [the full result and all
18 strata](2026-09-16-slurp-candidate-five-train-a.md). Historical positive DEV system
replications remain valid within their stated exploratory scope.

## September 16: typed-context sole recovery closed

**CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY.** The sole full1080 recovery aborted
after 6,645 generation contacts; one actual Reviewer request required 24,878 tokens
in a 24,576-token slot and was refused before generation. The 6,646 request-fit
receipts account for 26,584 endpoint contacts. No complete system manifest or score
exists and no partial quality was read. This is an engineering failure, not evidence
of task ineffectiveness. The direct comparator remains complete, first-scored and
quality-unreleased; the conditional replica remains ineligible.

Preserve the older replicated positive SLURP base. No third replay, prefix splice,
partial scoring or renamed retry is admitted. The next bounded question is dynamic
role-context capacity. See the [root terminal report and evidence pins](../handoff/2026-09-16-fable51/TERMINAL-UPDATE-20260916.md)
and [latest file handoff](../handoff/2026-09-16-fable51/LATEST.md).

## 2026-09-17: TRAIN A direct anchor released (Fable 5.1)

Under owner decision 3 of 2026-09-16 the held direct score of SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1 was read once: official pooled SLU 33.885 %, intent 73.70 %, scenario 82.69 %, action 75.09 %, span F1 21.10 % on the 1,080-row Fold A roster. Paired against the retained dual-store anchor on the same rows (whole-speaker bootstrap, 10,000 draws, seed 20260915): pooled SLU +14.65 pp, CI95 [+11.79, +17.51]; intent +4.26 pp, CI95 [+2.15, +6.46]; action +4.17; pooled span F1 +8.40; scenario +2.13 with CI95 crossing zero. Three scenarios lose pooled SLU (iot, music, lists) and five lose intent (alarm, calendar, datetime, lists, general -10.00). Zero new contacts; the closed typed-context pair is not reopened. Source: [release note](2026-09-17-slurp-train-a-direct-anchor-release.md), SHA-256 `92728dde617254692f72727147037ab3d0af437c2ce672b1e5c27b34c57a8c56`; machine result `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `fe1008ec97627b4b2358870543b4bb4d58a764211e9fa119f35e36f59ae800e5`. Owner decisions and the program: [owner decisions note](../readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md), [program spec](../superpowers/specs/2026-09-16-slurp-v2-base-program-design.md).

## 2026-09-17: Phase A audits of the SLURP v2 base program (Fable 5.1)

Three zero-contact audits on sealed outputs, recorded with their machine results under `SPEECHRL_DATA_DIR/analysis/`: [A1 USE projection](2026-09-17-slurp-a1-use-projection-audit-v1.md) (filler surface normalisation +3.461 pp official SLU on TRAIN A, CI95 [+2.781, +4.180], +3.733 on DEV1000, no scenario harm; about three quarters is case alignment the symmetric scorer scores at zero; support filter rejected; illegal-label rule R_action +1.389 pp intent), [A2 exemplar headroom](2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md) (plain top-20 speech-keyed TRAIN exemplars: candidate-union coverage 0.868 to 0.972, type recall 0.960, filler recall 0.566, no memorisation channel) and [A3 coverage confusion](2026-09-17-slurp-a3-coverage-confusion-audit-v1.md) (34 of 143 misses are gold general_quirky with no own card; 20 illegal delivered ids; date omission 81/135, time representation 46/72). They decide the forms of cells B1, B3, B4a and B4b in the program spec; none is a task-quality verdict.

## 2026-09-17: cell B0, review loop off (Fable 5.1)

Run SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1 (FINALIZED, 2,160 contacts, 1.054 GPU hours) against the sealed anchor on the same 1,080 rows: pooled official SLU +0.13 pp CI95 [-1.15, +1.45], intent -0.37 pp CI95 [-1.53, +0.82], 22 saves / 26 harms (p 0.67); against the released direct anchor +14.78 pp SLU CI95 [+11.90, +17.70]. **HARMFUL by the preregistered rule** (the intent CI95 lower bound -1.53 is below the imported 0.92 pp margin, which is narrower than the 1.175 pp half-width this roster yields); the loop changed at most 2 of 1,080 delivered intents. A same-roster own-null replicate with a re-decision rule fixed before reading is registered. Source: [verdict](2026-09-17-slurp-b0-review-off-verdict.md), SHA-256 `a36785b6dca3a7f41a99402c8474ca3b73cea10077f0b6b1abaf99281da34694`; machine result `analysis/SAEA-SLURP-B0-REVIEW-OFF-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `c26a76a3d7c24f41876a6a8fed6086d0620a6967ce09b7f687525996494c980e`.

## 2026-09-17: cell B0 re-decision v2, review loop off under the TRAIN A own null (Fable 5.1)

Run SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1 (FINALIZED, 2,160 contacts, 1.059 GPU hours), byte-identical to cell B0, measures the roster's own null: half-widths pooled SLU 1.1218 pp, intent 1.0051 pp, 77 of 1,080 rows change delivered intent between two greedy passes. Under the rule fixed before the read (both passes non-inferior to the anchor at those margins) the intent clause fails on both passes (CI95 lower bounds -1.527 and -1.313) and the SLU clause fails once (-1.150) and passes once (-1.043). **HARMFUL**; the loop stays in the default plan (harness-admission entry NEUTRAL for the loop itself), and cells B1, B2 and B4 re-register on the anchor. Source: [re-decision v2](2026-09-17-slurp-b0-review-off-redecision-v2.md), SHA-256 `cb04d406c520073e3a63ce3de4ea1996a2ace28fd26068eca8cad6338876f1ce`; machine result `analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `69abec23e2c6aecca0d55474268ae2c9966631f243497f354a95b332c7ceb849`.

## 2026-09-17: cell B4b, slot store v2 (date/time slot-contract revision) on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2 (FINALIZED, 5,407 contacts, 3.465 GPU hours) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 51.09, **+2.55 pp CI95 [+1.13, +3.98]**; intent +0.56 [-0.71, +1.82] (non-inferior at the 1.0051 own-null margin); projection v3 +2.06 [+0.53, +3.51] agreeing in sign; no scenario breaches the intent band; pooled span F1 +2.91; time-slot false-negative mass -32.9 and filler-distance mass -28 %. Against the released direct anchor +17.20 pp SLU. **ADMITTED** by the preregistered rule, the first admitted module of the SLURP v2 base program; default-plan entry provisional until a same-roster replication. Source: [verdict](2026-09-17-slurp-b4b-slot-store-v2-verdict.md), SHA-256 `1d19459ad826e712eb2ddfd1f6899ac2fcbb9c1803d5d2e38a4be2722d352b1d`; machine result `analysis/SAEA-SLURP-B4B-SLOT-STORE-V2-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `f5ff74c6c56609ead0547b2442ff0f3c1214a1ed63d08e2b43384d41ae384daf`.

## 2026-09-17: cell B1, exemplar supply to the Solver (recovery flight) on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2 (FINALIZED, 5,425 contacts, 3.68 GPU hours; the first attempt aborted on a Solver-revisit refusal fixed by E3c) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 61.14, **+12.61 pp CI95 [+10.54, +14.60]**; intent +2.22 [+0.74, +3.71]; projection v3 62.67 (+10.67), symmetric 62.97 (+10.89); pooled span F1 +18.93; all 18 scenarios gain SLU. Against the released direct anchor +27.25 pp SLU. **ADMITTED pending the derangement twin** (owner decision 8/15: the twin flies on a positive arm CI95). Source: [verdict](2026-09-17-slurp-b1-exemplars-k20-verdict.md), SHA-256 `79a3daa754db36b1d460e4cba04b5e385836b1a8cee40866dad865f7b668d5f1`; machine result `analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `a6430288b389f65b00951dd5a518ece285022977bae90e5d7ae39dde0af4c1a9`.

## 2026-09-18: cell B1 derangement twin, the retrieval key separated from the exemplars (Fable 5.1)

Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2 (FINALIZED, 5,429 contacts, 3.637 GPU hours; the same twenty-exemplar supply keyed by another Fold A row's sealed speech vector, prompt tokens -0.25 % against the arm) on the same 1,080 rows: B1 minus twin official pooled SLU-F1 53.30 -> 61.14, **+7.83 pp CI95 [+5.85, +9.75]** (clause 1b passes), intent +2.04 [+0.49, +3.78]; twin minus anchor +4.77 [+3.20, +6.36] with nil intent (+0.19 [-1.03, +1.39]); twin minus direct +19.42; projection v3 55.76 / 80.09, symmetric 55.90; no scenario breaches the band on any gating contrast. **Cell B1 ADMITTED (owner decision 18, branch A): module M1 is speech-keyed exemplar supply** -- presence buys 38 % of the SLU gain, the key 62 % and nearly all of the intent gain; M1p is not registered. Harness-admission entry M1 written (stores null form), provisional until the B5e/B5er pair replicates it. Source: [verdict](2026-09-18-slurp-b1-twin-verdict.md), SHA-256 `fb841eb30b30ee5229d9d590be39bae5dd0e734cea42037a718fcdf5202672f6`; machine result `analysis/SAEA-SLURP-B1-TWIN-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `37cec40d539df80eb02e9b45f8965669105f2a91588dafbf0d921aa526d02d1a`.

## 2026-09-18: cell B5e, the early combination of M1 and M4b on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 (FINALIZED, 5,415 contacts, 3.871 GPU hours; the run's one recovery after a 25-contact infrastructure abort) on the same 1,080 rows: official pooled SLU-F1 **62.34** / intent **80.09** (v3 63.78 / 81.85; symmetric 64.18). **BAR NOT MET on the official number** (SLU 1.66 pp short, intent clears by 2.09; owner decision 23). B5e minus anchor +13.80 [+11.77, +15.80]; minus B1 +1.20 [-0.11, +2.48] with intent -0.09 [-1.51, +1.38]; minus B4b +11.25; minus direct +28.45; interaction -1.36 [-3.29, +0.56]. **Combination HARMFUL by the registered clause 3** (the intent CI95 lower bound -1.51 crosses -1.0051 on a one-row tie: an interval-width trigger, recorded with the caveat that the own-null margin came from a request-identical replicate). B5er not registered; decision 20 path: B2 v3 (flying), B7a, B4a, then B5b. Source: [verdict](2026-09-18-slurp-b5e-combination-verdict.md), SHA-256 `5e2ba383341f2c5544df044d5145b2064b5d5251f5981a27e1a56a6a00e54b6f`; machine result `analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `9ce5678666b50e411f9530693907017d3285f156a6d1a586ad60271dc12d8d7c`.

## 2026-09-18: cell B5e addendum under owner decision 25 (Fable 5.1)

Combination status re-read as **NEUTRAL, non-inferiority not proven at the request-identical margin**: the registered clause 3 fired on the intent CI95 lower bound alone (-1.51 against -1.0051) with a one-row-tie point estimate; owner decision 25 requires a measured loss for a HARMFUL reading of a combination cell. M4b inside the combination +1.20 pp official SLU [-0.11, +2.48] over B1 is recorded as a beneficial, unproven gain. Bar outcome, decision-20 path and the non-registration of B5er unchanged. Source: [addendum](2026-09-18-slurp-b5e-combination-verdict-addendum-decision-25.md), SHA-256 `f7d970c00329c1975891d79adfb14fe605e6e474ac51336fda26361f9bb445a8`.

## 2026-09-19: cell B2 v3, grouped Solver sampling N=5 (module M2) on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3 (FINALIZED, 9,807 contacts, 3.714 GPU hours) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 48.60, **+0.06 pp CI95 [-1.46, +1.60]**; intent +0.83 [-0.30, +1.88]; v3 -0.00, symmetric -0.23; no scenario breaches the band. **NEUTRAL; non-inferiority on pooled SLU not proven at the request-identical margin.** False positives suppressed as predicted (spurious mentions 362 -> 303) but omissions rose; the greedy twin is not due and the cell closes; M2 enters no plan. Sample agreement is a confidence signal for later modules (unanimous rows 81.4 % correct intent vs 39.7 %). Source: [verdict](2026-09-19-slurp-b2-samples5-verdict.md), SHA-256 `4fe97086c07bb80a955622aa03390fa3c76268d192273c71612ec3452d387df2`; machine result `analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/score-contrasts.json` under `SPEECHRL_DATA_DIR`, SHA-256 `7aeaccca0c20f7fa5da847c1a8f11119fbc81837f8264e1b292c1311064527a9`.

## 2026-09-19: cell B4b replicate, slot store v2 (module M4b) on the anchor, flown as the first resume-recovery (Fable 5.1)

Run SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2 (FINALIZED at study commit f2a2cb21; attempt attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2: 580 rows kept from the predecessor attempt aborted at 2,922 contacts by the 2026-09-18 serving-session death, 500 rows flown, I7r custody verified on every kept row; 2,501 contacts and 1.743 GPU hours this attempt, run-cumulative 5,423 calls) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 50.07, **+1.54 pp CI95 [+0.30, +2.93]**; intent +0.65 [-0.62, +1.87] against the -1.0051 margin; v3 +0.85 same sign; scenario -0.19, action +0.65; 0 of 18 scenarios breach the band. **REPLICATED** (first pass +2.55 [+1.13, +3.98]): module M4b's obligation is MET and the SLURP default plan now pins slot store v2. Own null of the admitted configuration (B4b-rep minus B4b): h_SLU 1.3222, h_intent 1.0682, 792 of 1,080 answers byte-identical. Mechanism replicates on dates (omissions 81 -> 77 -> 76, exact mentions 28 -> 33 -> 37 of 138) and on filler distance (814 -> 751 -> 749); the time cell is weaker on the second pass (exact time mentions 8 -> 22 -> 14), which explains the smaller pooled gain. Kept-versus-flown is scenario-confounded by construction and is reported, not read. Verdict: `docs/results/2026-09-19-slurp-b4b-replicate-verdict.md`.

## 2026-09-19: cell B8a, the delivery-time normaliser node (module M3 inside the agent) (Fable 5.1)

Model-free read (run SAEA-SLURP-B8A-DELIVER-NORMALISE-MODEL-FREE-READ-V1, zero contacts) over copies of the sealed anchor, B1 and B5e arms, node ON minus OFF on the OFFICIAL unprojected pooled SLU-F1: anchor 48.53 -> 51.99, **+3.46 pp CI95 [+2.78, +4.18]** (intent +1.39 [+0.71, +2.04]); B1 61.14 -> 62.67, **+1.53 [+1.05, +2.03]** (intent +1.57); B5e 62.34 -> 63.78, +1.44 [+1.00, +1.92] (intent +1.76, reported). Intent harmed on zero rows; 0 of 18 scenarios breach; triple equality (official-with-node == v3 == replay) 0 mismatches; STOP 27 checks passed. The four-row smoke (SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1) passed structurally at e79ce296. **ADMITTED**: module M3 enters the SLURP default plan (`native_episode.deliver_normaliser`); every official SLURP number from here on is produced by a system containing the node, and a later cell registered against a node-free sealed arm must say so. The TRAIN symmetric number moves at most +0.16, so the gain is a surface-convention repair of the official scorer's reading, admitted as such (decision 23). Verdict: `docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`.

## 2026-09-19: cell B7a v2, Node Context Policy level L1 on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2 (FINALIZED at study commit 83d6b1b2, 5,621 contacts, 3.781 GPU hours; the v1 cell closed after two aborts, v2 flew with the finite-completion policy armed) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 48.22, **-0.31 pp CI95 [-1.81, +1.12]**; intent -0.65 [-2.18, +0.87] against the -1.0051 margin; v3 -0.50, symmetric -0.68; 0 of 18 scenarios breach the band. **HARMFUL** under the registered NEUTRAL test -- by interval width (both point estimates inside the margins; the cell's own half-widths are 30-52 % wider than the imported ones), not by a measured loss -- and in any case dead weight: 5.21 contacts per row, +11.6 % GPU hours, +7.8 % prompt tokens, 59 revisions against 6, and the structured review-finding boundaries rendered FALLBACK-RAW on 100 % of rows. Diagnostics: 3 finite-completion rows retained (0 abstentions), 2 illegal Planner actions retained, per-row exact slot F1 +1.33 and per-row SLU-F1 +1.98 (reported, not interpreted). Owner decision 32 fires: cells B7r and B7c close unflown, cell B8b is re-based on the anchor, level L2 stays unflown. Verdict: `docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md`.

## 2026-09-19: cell B4a v2, the general_quirky fallback candidate + intent-boundaries v2 on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2 (FINALIZED at study commit 682ee52d, 5,412 contacts, 4.721 GPU hours) against the sealed anchor on the same 1,080 rows: intent 77.96 -> 78.70, +0.74 pp CI95 [-0.30, +1.75] (the cell's primary; lower bound not above zero); official pooled SLU-F1 48.53 -> 47.83, **-0.70 pp CI95 [-2.29, +0.89]** (the HARMFUL clause fires on the lower bound against -1.1218); v3 +0.28 and symmetric +0.74 same sign; 0 of 18 scenarios breach. **HARMFUL** by interval width rather than measured loss, and inert in mechanism: the fallback was appended on 1,052 rows, lifted gold-general_quirky candidate coverage from 24 % to 100 % and was selected on zero rows; general intent 36.67 % on both arms, qa 75.00 % on both; the covariate cost +30 % prompt tokens and +39 % GPU hours with pooled span F1 -2.00 and per-row exact slot F1 -1.91. Owner decision 9: cell B4c closes unflown. Decision-30 streak: two consecutive one-factor cells NEUTRAL/HARMFUL (B7a v2, B4a v2). Verdict: `docs/results/2026-09-19-slurp-b4a-fallback-quirky-anchor-v2-verdict.md`.

## 2026-09-19: efficiency cell EFF-1, constant native tool-schema rendering on the anchor (Fable 5.1)

Run SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1 (FINALIZED at study commit 711bc6c4, 5,293 contacts, 1.843 GPU hours) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 44.14, **-4.39 pp CI95 [-6.69, -2.17]**; intent 77.96 -> 68.80, **-9.17 pp CI95 [-11.64, -6.79]** (both HARMFUL clauses fire on the point estimate and the upper bound against the B0r margins -1.1218 / -1.0051); 9 of 18 scenarios breach; v3 -4.94 / -9.81 and symmetric -4.96 same sign. **HARMFUL**, root-caused to the Solver's delivery shape: with the Reviewer's tools array rendered into its system message the Solver answered 145 of 1,092 contacts with a tool-call-shaped string (anchor 0), the Reviewer then ran once without its task-contract call, and the string was delivered verbatim -- 137 rows the official scorer cannot parse (anchor 7), each scoring zero; on the 938 rows both arms parsed the delta is +0.03 SLU / +0.21 intent (diagnostic only). The efficiency measurement stands: prefilled tokens per row 26,197 -> 10,127 (-61.3 %), cached share 42.9 % -> 75.2 %, GPU hours per 1,080 rows 3.388 -> 1.843 (-45.6 %), 45.94 contacts per minute whole-flight (26.06 on the anchor's attach window), projected 13,078-row read 41.0 h -> 22.3 h. The key enters no default plan; the repair (a decode-time constraint on the tool-free roles, or withdrawing the Reviewer's task-contract tool) is a new cell and, for the withdrawal, an owner decision. An efficiency cell does not count toward decision 30 (streak stays at two). Verdict: `docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`.

## 2026-09-19: cell B1r, the request-identical replicate of module M1 (the speech-keyed exemplar supply) on TRAIN A (Fable 5.1)

Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1 (FINALIZED at study commit c905ddf0, 5,443 contacts, 3.851 GPU hours) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 62.23, **+13.70 pp CI95 [+11.64, +15.73]**; intent 77.96 -> 80.09, **+2.13 pp CI95 [+0.81, +3.38]** (above the -1.0051 margin); v3 +11.98 same sign; 0 of 18 scenarios breach. **REPLICATED** under cell B1's own three-clause rule, applied unchanged. The own null of the admitted configuration (B1r minus B1, request-identical: the first model-facing request byte-identical on 1,080 of 1,080 rows): pooled SLU +1.09 [-0.10, +2.37] and intent -0.09 [-1.31, +1.13], half-widths **h_SLU_M1 1.2350 / h_intent_M1 1.2212** (the borrowed B0r 1.1218 / 1.0051; the intent margin was about 22 % too narrow), delivered text identical on 74.35 % of rows, 80 intent flips. Consequences: the M1 harness-admission obligation is MET, the SLURP default plan carries the train-exemplars store, and every later B1-based comparator reads at 1.2350 / 1.2212 (owner decision 38). One finite_completion disposition on the replicate (Reviewer length cap, latest Solver draft delivered; the E13 policy kept the flight alive). Verdict: `docs/results/2026-09-19-slurp-b1-replicate-verdict.md`.

## 2026-09-20: cell B8b-anchor, the Reviewer slot-audit attachment on the anchor, sealed as an E10 resume-recovery (Fable 5.1)

Run SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1 (resume attempt FINALIZED at study commit 2f185b13; 378 rows kept from the attempt aborted on 2026-09-19 at 2,016 contacts under I7r custody, 702 rows flown; run-cumulative 5,822 contacts, 3.846 GPU hours) against the sealed anchor on the same 1,080 rows: official pooled SLU-F1 48.53 -> 49.40, **+0.87 pp CI95 [-0.63, +2.37]** (the admission clause's lower bound not above zero); intent 77.96 -> 79.17, **+1.20 pp CI95 [-0.19, +2.59]** (non-inferior at -1.0051); action +1.39 [+0.09, +2.69]; v3 +1.13 and symmetric +1.06 same sign; 0 of 18 scenarios breach; every metric positive, saves exceed harms on all five per-row metrics. **NEUTRAL** -- a beneficial but not CI95-proven movement (decision 25) at +7 % contacts and +13.5 % GPU hours, so it enters no plan; the audit block's next test is inside the knowledge index (decisions 48-53). Dispositions: 6 finite_completion rows, 1 react_exhaustion visit (item E22 kept the flight alive where the predecessor aborted). Decision-30 streak: three consecutive one-factor NEUTRAL/HARMFUL cells (B7a v2, B4a v2, B8b-anchor) -- trigger (b) fires; under decision 57 v2.0 is PROVISIONALLY locked on B5e plus the normaliser node (63.78 / 81.85) with the plan-arm replicate owed. Verdict: `docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md`.

## 2026-09-20: cell B1-notool, the Reviewer's task-contract tool withdrawn on the B1 base (repair form 0-B) (Fable 5.1)

Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1 (FINALIZED at study commit 23f011dd, 4,432 contacts = 4.10 per row, 0 tool calls, 1.611 GPU hours) against the sealed B1 arm on the same 1,080 rows: official pooled SLU-F1 61.14 -> 62.13, **+0.99 pp CI95 [-0.59, +2.50]**; intent 80.19 -> 80.00, **-0.19 pp CI95 [-1.33, +0.91]** against the -1.2212 margin (the lower bound misses by 0.11 pp; no measured loss anywhere; B1r's own null fails the same clause; eight length-capped Reviewer rows decide it). The verdict writes NON-INFERIORITY NOT PROVEN; the coordinator records **NEUTRAL** under owner decision 25 and the B5e precedent (open to the owner's overruling). Decision 56: both numbers within 5 % of B1's, so no other base is flown. Efficiency: prefilled tokens per row 26,072 -> 8,020 (-69 %), GPU hours per 1,080 rows 3.851 -> 1.611, contacts per minute 23.10 -> 42.91, projected 13,078-row read 46.6 h -> 19.5 h; delivery shape healthy (0 tool-call-shaped Solver completions). The withdrawal enters the SLURP default plan and is the base of the knowledge-index cell (decision 53); in `docs/receipts/harness-admission.json` the module is written as the RETIREMENT of the Reviewer's task-contract toolkit under the `phase_tools` switch class and the `RETIRED` status that item E25 added for it (ON = the toolkit the comparator carried, OFF = its absence; the check proves the plan carries OFF). Diagnostic carried forward: the music scenario breaches the intent band (-8.33, +5 net harmed; repeats vs B1r). Verdict: `docs/results/2026-09-20-slurp-b1-notool-verdict.md`.

## 2026-09-21: cell IDX, the knowledge index + pointer block on the tool-free B1 base, with its derangement twin IDXT (Fable 5.1)

Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-V1 (FINALIZED at study commit 38984e80, 4,516 contacts = 4.18 per row, 0 tool calls, 1.334 GPU hours) against the sealed B1-notool arm on the same 1,080 rows: official pooled SLU-F1 62.13 -> 54.76, **-7.37 pp CI95 [-9.72, -4.80]**; intent 80.00 -> 77.59, **-2.41 pp CI95 [-4.56, -0.32]** -- both guards a measured loss against the 1.2350 / 1.2212 margins: **HARMFUL** (owner decision 25). The twin SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-TWIN-V1 (FINALIZED at 9f2997d0, 4,559 contacts, 1.247 GPU hours; view slurp-knowledge-index-twin-v1, seed 20260920) reads **HARMFUL as a control** (SLU -9.97 [-12.46, -7.32], intent +0.19 [-2.00, +2.31]) and enters no plan. Decomposition (decision 62): FORM (twin minus base) SLU -9.97, CONTENT (IDX minus twin) SLU +2.60 [+0.80, +4.49] / intent -2.59 [-4.33, -0.86] -- the loss is the form; the content term is an upper bound (the IDX expansion block is about 3,000 characters longer per row on 1,055 of 1,080 rows). Index consumption (decision 64): MISLEADING TERSENESS (IDX verdict; the block is read -- pointed slot types 86 % vs 72 % -- but the terse lines mislead: expanded-stratum precision 0.67 -> 0.52, intent-pointer adherence 95 -> 92 %, citations near zero), undecided / NON-CONSUMPTION better supported (twin verdict). Contingency: the form is CLOSED at decision 52's defaults; the richer-granularity route is contraindicated; the owner decides the next form (decision 72). Efficiency (mandatory): prefilled tokens per row 8,020 -> 3,379 (render proof 3,096), GPU hours per 1,080 rows 1.611 -> 1.334, contacts per minute 42.91 -> 53.41, projected 13,078-row read 19.5 h -> 16.2 h; cost fell, the score fell more (decision 50's second clause fails). Diagnostics: one system-message sha over all contacts, 0 degradations, 0 tools arrays; finite_completion 20 (base 8); play intent 63.33 -> 21.67. Verdicts: `docs/results/2026-09-21-slurp-idx-knowledge-index-verdict.md`, `docs/results/2026-09-21-slurp-idxt-knowledge-index-twin-verdict.md`; drivers `index_cell_read.py` / `twin_cell_read.py` under the analysis roots (every table regenerable by stage; decision 58).

## 2026-09-21: cell PLAN, the SLURP default plan flown as one arm on the tool-free B1 base (the v2.0 lock evidence) (Fable 5.1)

Run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 (FINALIZED at study commit e367a629, flown by the SAEA-Batch-Driver scheduled task; 4,424 contacts = 4.10 per row, 0 tool calls, 1.758 GPU hours) against the sealed B1-notool arm on the same 1,080 rows: official pooled SLU-F1 62.13 -> 63.63, **+1.50 pp CI95 [-0.04, +3.24]** (CI90 [+0.18, +2.94]; own-null margin 1.2350 cleared by the point estimate, CI95 includes zero); intent 80.00 -> 82.22, **+2.22 pp CI95 [+0.92, +3.56]** (McNemar p 0.0018, 40 saves / 16 harms): **NEUTRAL** (decision 25: the intent gain is proven, the SLU gain beneficial but unproven). Lock comparison (reported, never gated): against the provisional v2.0 lock (B5e + the v3 node applied model-free, 63.78 / 81.85, both reproduced exactly) SLU -0.15 [+-1.39], intent +0.37 [+-1.00] -- parity; under the projection-v3 scorer the base rises to 63.60 and the SLU edge collapses to +0.03, so the plan's node-independent advantage is intent. Frontier (decision 75): PLAN sits on both Pareto planes -- 63.63 at 1.758 GPU-h per 1,080 (B1-notool 62.13 at 1.611; B8a on B5e 63.78 at 3.871) and at 8,353 prefilled tokens per row (B1-notool 8,020; B8a 46,796): within 0.15 SLU of the provisional lock at 45 % of its GPU cost and 18 % of its prefill. Structural: 0 tools arrays, 0 tool calls, one normaliser receipt per row (102 rows changed), slot-contracts v2 pins verified, E20 compaction 0 rows (prompt limit 20,990 of 24,576), finite_completion 10 (base 8), planner_action_illegal 1; 0 scenario breaches. Cost +9.1 % GPU-h, localised at the Solver (v2 cards, +339 tokens per row). Candidate v2.0 lock numbers 63.63 / 82.22 pending the request-identical replicate PLANr. Read by the stage driver plan_cell_read.py (decision 58); a latent defect found in the driver (`_score_copies` copies outputs without a digest check; audited byte-identical this time) is open. Verdict: `docs/results/2026-09-21-slurp-plan-v2-lock-arm-verdict.md`.

## 2026-09-22: cell PLANr, the request-identical replicate of the default-plan arm, and the v2.0 LOCK (Fable 5.1)

Run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 (FINALIZED at study commit e367a629, flown by the SAEA-Batch-Driver scheduled task; 4,389 contacts = 4.06 per row, 0 tool calls, 1.665 GPU hours) against the sealed PLAN arm on the same 1,080 rows: official pooled SLU-F1 63.63 -> 63.80, **+0.17 pp CI95 [-1.11, +1.38]**; intent 82.22 -> 82.50, **+0.28 pp CI95 [-0.74, +1.25]** (15 saves / 12 harms, McNemar p 0.70); equal-scenario SLU +0.46 / intent +0.28; 0 scenarios beyond the band, 0 decision-17 flags: **REPLICATED (NEUTRAL)**. The plan's own null (decision 38) is fixed by this contrast: h_SLU 1.2485, h_intent 0.9943 -- the margins of every cell read against the sealed PLAN arm. Lock comparison: against the provisional lock (B5e + v3 node, 63.78 / 81.85) SLU +0.03 [-1.35, +1.41], intent +0.65 [-0.52, +1.86]. Frontier: PLANr on both Pareto planes (8,321 prefilled tokens per row, 1.665 GPU-h per 1,080; 26 rows with a REVISE against PLAN's 38). Structural: 0 compactions, 9 finite-completion rows, 0 planner_action_illegal, 0 ReAct exhaustions, 105 rows changed by the normaliser node. **v2.0 is LOCKED** on cell PLAN's fragment as flown at e367a629 (M1 + M4b + M3 + the RETIRED toolkit + E13 / E20 / E22; np4), lock numbers 63.63 / 82.22 (replicate 63.80 / 82.50); no development bar (decision 86). Lock record: `docs/results/2026-09-22-slurp-v2-lock-v1.md` (supersedes the 2026-09-20 provisional record). Verdict: `docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md`; read by plan_cell_read.py with a per-cell registered-facts file (decision 58).

## 2026-09-22: cell B9a-rec, the Acquisition node (kind (a) knowledge re-query) as one factor on the locked default plan (Fable 5.1)

Run SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1 (the one recovery after item E36; FINALIZED at flight commit 942aab16, SAEA-Batch-Chain-B9arec; 4,420 contacts = 4.09 per row, 0 tool calls, 1.683 GPU hours) against the sealed PLAN arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 63.63 -> 63.89, **+0.26 pp CI95 [-1.19, +1.60]** (non-inferior); intent 82.22 -> 82.22, **0.00 pp CI95 [-1.10, +1.08]** (13 saves / 13 harms; lower bound below -h by 0.10 pp): **NON-INFERIORITY NOT PROVEN** by width, no measured loss (decision 25), 0 scenarios beyond the band. **Acquisition read: 18 rows routed ACQUIRE and all 18 acquisitions returned zero items** (18 ties vs PLAN on every metric) -- the node is instantiated but inert; root cause by name: the E36 binding re-runs the Solver's pure (phase, sample) supply and excludes exactly those ids (empty by construction); repair = item E36b (findings-keyed store search), a new cell only by owner decision (43 / 44). The plan's acquisition key stays off; no harness-admission entry written. Frontier: 63.89 / 82.22 at 8,445 prefilled tokens per row and 1.683 GPU-h (on both planes by cost, identical in effect). Verdict: `docs/results/2026-09-22-slurp-b9a-rec-acquisition-node-verdict.md`; read by plan_cell_read.py (patched copy for the zero-contact acquisition visit) + acquisition-read.json (decision 58).

## 2026-09-22: cell B6, the locked v2.0 default plan against the bare core on the fresh DEV-2000-ADDED roster (Fable 5.1)

Runs SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1 (1,000 contacts, 0.087 GPU-h) and SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1 (4,071 contacts = 4.07 per row, 1.655 GPU-h), both FINALIZED at flight commit 54f569c6 (SAEA-Batch-Chain-B6), scored once each with the devel official scorer, read paired and clustered by utterance (913 utterances, 87 doubled): official pooled SLU-F1 38.09 -> 65.40, **+27.30 pp CI95 [+24.05, +30.50]**; intent 61.7 -> 76.6, **+14.90 pp CI95 [+11.78, +18.03]** (199 saves / 50 harms); scenario +12.2, action +13.7, span-F1 +31.9, slot-F1 exact +25.1; far-field +13.5 / headset +16.5 intent: **DESCRIPTIVE** (decision 76a's SLURP direct-vs-system comparison; no bar, decision 86; dev numbers, decision 28). Per-scenario table NOT AVAILABLE (roster withholds the stratum; no gold read). The decision-78 seal path is complete. Read by the reusable driver scripts/analysis/slurp_paired_roster_read.py (decision 58). Note: `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`.

## 2026-09-22: cell E35, the Earnings21 + ConEC carrier on FlightRuntime (Fable 5.1)

Runs SAEA-E21-NATIVE-WINDOW-{DIRECT,SYSTEM}-{FOUR-ROW,SUB10}-V1 (four-row pair structural; sub10 pair 10 calls / 342 windows: direct 342 contacts, system 1,597 contacts = 4.67 per window through all six nodes), FINALIZED at flight commits 825ee769 / 1a9c78d2 (SAEA-Batch-Chain-E35) on the E21 serving geometry (np4, max 1,024 completion tokens), scored once each: **STRUCTURAL PASS** (decision 89: Earnings joins FlightRuntime), **DESCRIPTIVE HARM as flown** (corpus WER 0.0724 -> 0.2863, numeric accuracy 0.9239 -> 0.7106, 10 / 10 calls worse; n = 10, no claim), **root-caused model-free** to one harness defect: E13 `deliver-latest-or-abstain` scoped to the whole episode voids 76 windows (22.9 % of the reference words, 95.6 % of the extra error mass) after a length-truncated Perception contact; with those windows scored like the direct arm the system arm reads 0.0778, and on the 234 windows that reached a Planner ACCEPT direct 0.0707 vs system 0.0722. The six-node form is NOT admitted for Earnings until item E39 (E13 scoped to the answering node, per-role completion caps, tool-free Reviewer template) passes a four-row dry run. ConEC entity WER not measured (official tool not run). Read: `docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`; appendix `docs/results/2026-09-22-e21-native-window-e35-sub10-diagnosis.md`.

## 2026-09-22: cell R-PRIM, the Reviewer verdict as a closed set of primitives on the locked plan (Fable 5.1)

Run SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1 (4,353 contacts = 4.03 per row, 1.57 GPU-h, FINALIZED at flight commit 827af825, SAEA-Batch-Chain-RPrim) against the sealed PLAN arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 63.63 -> 64.21, **+0.58 pp CI95 [-0.82, +1.80]** (non-inferior); intent 82.22 -> 82.13, **-0.09 pp CI95 [-1.16, +0.94]** (non-inferiority NOT PROVEN by width, 0.17 pp of CI beyond the margin, no loss): **NEUTRAL** (decision 25 precedent). Cost lower than the base (contacts 4.03 vs 4.10 per row). The purpose of E37 is met: parse rate 100 % on 1,091 Reviewer visits (0 of 2,167 anchor reviews parsed before), tokens ACCEPT 1,073 / REVISE-INTENT 7 / REVISE-SLOT-VALUE 11, REVISE precision 0.91, recall 0.017 against 598 wrong rows. Decision 97: not HARMFUL, so the pruning cells P1 (Reviewer 3 -> 1) and P0 (review-off) are registered on the R-PRIM base. Read: `docs/results/2026-09-22-slurp-review-primitives-verdict.md`.

## 2026-09-23: cell P1, Reviewer 3 -> 1 (native_episode.roles.reviewer.max_iterations) (Fable 5.1)

Run SAEA-SLURP-NATIVE-PRUNE-REVIEWER1-V1 (4338 contacts = 4.02 per row, 1.38 GPU-h, FINALIZED at flight commit 1e349630, SAEA-Batch-Chain-Prune) against the sealed R-PRIM arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 0.00 -> 0.00, **+0.00 pp CI95 [+0.00, +0.00]**; intent 0.00 -> 0.00, **+0.09 pp CI95 [+0.00, +0.00]**: **NEUTRAL (non-inferiority NOT PROVEN on SLU by width, not by loss): SLU -0.15 pp [-1.38, +1.24] misses the margin 1.2485 by 0.13 pp of CI width, intent +0.09 pp [-0.69, +0.90] non-inferior**. The factor is nearly a no-op on this base: the R-PRIM Reviewer already used one visit per row on 1,069 of 1,080 rows (its max_iterations 3 was never drawn), so P1 removes at most the second Reviewer contact of 11 rows; contacts per row 4.017 vs 4.031, GPU-h 1.38 vs 1.57 (throughput noise, not a budget saving). The review-budget question is answered by P0 (review-off), not by P1. Decision 97 stands: not HARMFUL. Read: `docs/results/2026-09-23-slurp-prune-reviewer1-verdict.md`.

## 2026-09-23: cell P0, review-off (Reviewer 0, Planner 0, no revision: Perception -> Solver -> Delivery, the item-E1 / cell-B0 form) (Fable 5.1)

Run SAEA-SLURP-NATIVE-PRUNE-REVIEW-OFF-V1 (2160 contacts = 2.00 per row, 1.26 GPU-h, FINALIZED at flight commit 1e349630, SAEA-Batch-Chain-Prune) against the sealed R-PRIM arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 0.00 -> 0.00, **+0.00 pp CI95 [+0.00, +0.00]**; intent 0.00 -> 0.00, **-0.56 pp CI95 [+0.00, +0.00]**: **NEUTRAL (non-inferiority NOT PROVEN on both metrics by width, not by measured loss): SLU -0.36 pp [-1.45, +0.78] vs margin 1.2485; intent -0.56 pp [-1.60, +0.52] vs margin 0.9943; no CI95 upper bound below zero, no point estimate beyond a margin (decision 25 Method B)**. Removing the review loop halves the contacts (2.00 vs 4.03 per row, prefilled tokens 7,802 vs 8,346, GPU-h 1.26 vs 1.57) and costs at most -0.36 SLU / -0.56 intent by point estimate, unproven in either direction at this width; the locked plan keeps its Reviewer + Planner (decision 85 admits a pruning only on a proven non-inferior read), and a request-identical replicate would be needed to narrow the interval before any plan change. Together with P1 (no-op) and R-PRIM (98.4 % ACCEPT, recall 0.017), the review loop on the locked plan is a 2-contact-per-row insurance whose measurable value is within the null band. Read: `docs/results/2026-09-23-slurp-prune-review-off-verdict.md`.

## 2026-09-23: cell ADV-1, the SYSTEM-level semantic-advantage contact (Fable 5.1)

Run SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1 (225 contacts on the 225 disagreeing ROLL-1 rows, FINALIZED at flight commit b9c9ff71, SAEA-Batch-Chain-ADV1): **STRUCTURAL PASS** -- 225 / 225 legal statement sets (JSON form), 396 blocks, node distribution perception 124 / solver 159 / reviewer 99 / planner 14, delta kinds slot-contract 155 / intent-boundary 121 / reviewer-criterion 99 / planner-rule 13 / exemplar-note 6 / perception-hint 2. Algorithm label tfgrpo-semantic-advantage-v1 (decision 101). No effectiveness claim (decision 99: read at CELL-1 vs the sealed PLAN). Read: `docs/results/2026-09-23-slurp-stage3-advantage-r01-read.md`.

## 2026-09-23: cell CELL-1, the locked v2.0 plan plus the per-node stage3-deltas-v1r store (379 node-targeted deltas curated from the sealed ADV-1 statements; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4) (Fable 5.1)

Run SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1 (4553 contacts = 4.22 per row, 1.80 GPU-h, FINALIZED at flight commit 00c313c3, SAEA-Batch-Chain-Cell1) against the sealed PLAN arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 63.63 -> 63.15, **-0.48 pp CI95 [-2.18, +1.24]**; intent 82.22 -> 81.48, **-0.74 pp CI95 [-2.17, +0.57]**: **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on either metric (no observable positive gain on TRAIN Fold A; the twin reproduces the arm within noise, so the delta store's content moves nothing at the pooled level)**. Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.15 vs 63.63 (-0.48 pp, CI95 [-2.18, +1.24]) and intent 81.48 vs 82.22 (-0.74 pp, CI95 [-2.17, +0.57]); the derangement twin reads 63.19 (-0.44, CI95 [-1.94, +0.99]) and 82.31 (+0.09, CI95 [-1.19, +1.30]); arm minus twin is -0.04 pp SLU and -0.83 pp intent (descriptive): the pooled effect is neither content nor form. Every row received deltas (256 of 379 distinct values supplied; Planner reaches 59 % of rows), the per-delta paired outcomes are strongly heterogeneous (Solver deltas +5 to +6.5 pp SLU on 100+ rows beside -4 to -5 pp), and the per-scenario table swings from audio +8.9 / weather +8.3 / datetime +4.2 to general -12.4 / alarm -6.8 / news -6.6 / play -5.8 pp -- the pattern decision 83's retention rule was preregistered for (iteration 2: 200 kept / 179 retired, iteration-2-retention-v1.md). Cost: contacts +2.9 %, GPU-h +2.5 %, prefilled tokens +10.9 %; off both frontiers. The loop itself (rollout -> scoring -> advantage -> curation -> release -> cell -> read) closed end to end under the contracts; the four launch defects of 2026-09-23 were mechanism-wiring defects fixed before any generation contact was wasted beyond 320 metered calls. Stage-3 algorithm label tfgrpo-semantic-advantage-v1 (decision 101). Read: `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md`.

## 2026-09-24: cell CELL-2, the locked v2.0 plan plus the per-node stage3-deltas-v2 store (the 200 values owner decision 83's per-scenario x frontier retention kept out of the 379 v1r deltas over the CELL-1 read; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4) (Fable 5.1)

Run SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1 (4483 contacts = 4.15 per row, 1.77 GPU-h, FINALIZED at flight commit 1425f00b, SAEA-Batch-Chain-CELL2) against the sealed PLAN arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 63.63 -> 64.27, **+0.64 pp CI95 [-0.76, +1.92]**; intent 82.22 -> 82.13, **-0.09 pp CI95 [-1.22, +0.96]**: **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on intent (SLU non-inferior and positive but unproven); iteration 2 moves the arm in the right direction without a proven gain**. Against the sealed PLAN arm the arm reads official pooled SLU-F1 64.27 vs 63.63 (+0.64 pp, CI95 [-0.76, +1.92]; non-inferior at the 1.2485 margin, gain unproven) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.22, +0.96]; the lower bound sits 0.23 pp beyond the -0.9943 margin, so non-inferiority is NOT proven by width, not by a measured loss); the per-row SLU mean is +1.30 pp (CI95 [-0.04, +2.67], CI90 [+0.16, +2.44]; saves 87 / harms 70) and the TRAIN symmetric scorer agrees in sign (+0.66). The derangement twin reads 63.68 (+0.05, CI95 [-1.52, +1.62]) and 81.30 (-0.93, CI95 [-2.40, +0.41]); arm minus twin is +0.59 pp SLU and +0.83 pp intent (descriptive): the retained content sits above its own form control on both metrics, inside the noise band. Iteration 1 -> 2 (CELL-1 -> CELL-2): SLU -0.48 -> +0.64, intent -0.74 -> -0.09; the harm scenarios contracted (alarm -6.8 -> -3.6, news -6.6 -> -0.5, play -5.8 -> -0.6) and the winners grew (audio +8.9 -> +14.5, weather +8.3 -> +9.7, email +3.5), while general stays the hole (-12.4 -> -10.6 SLU, -6.7 intent) because no retained value targets it. Against the Stage-2 lock B5e official the arm is +1.93 SLU [+0.56, +3.34] and +2.04 intent [+0.74, +3.34]. Consumption: 121 of 200 values supplied, Solver reaches 68.5 % of rows, Reviewer 64.1 %, Planner 18.3 % (10 of 14 Planner values retired), one Solver value (d1c93189) reads -1.9 SLU / -2.2 intent on 182 rows. Cost: 4.15 contacts per row (+1.3 %), 1.768 GPU-h (+0.6 %), prefilled tokens +6.6 %, zero rows compacted. A SECOND look on the rows whose CELL-1 read chose the retained set: a development number under owner decisions 28 / 86, and no claim before the fresh-roster replicate. Stage-3 algorithm label tfgrpo-semantic-advantage-v1 (decision 101). Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md`.

## 2026-09-24: cell CELL-1-GEPA, the locked v2.0 plan plus the per-node stage3-deltas-gepa-v1 store (448 values: 248 curated by the decision-83 frontier rule from the sealed GEPA-R01 reflective proposer contact over 68 (scenario, node) groups of the ROLL-1 trajectories, plus the 200 iteration-1 values decision 83 retained; permitted roster = the ADV-1 disagreeing receipt, the v1r / v2 precedent; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4; label gepa-reflective-pareto-v1, operators update + selection + context_application) (Fable 5.1)

Run SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1 (4508 contacts = 4.17 per row, 1.86 GPU-h, FINALIZED at flight commit 194d4b42, SAEA-Batch-Chain-GEPACELL) against the sealed PLAN arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 63.63 -> 63.60, **-0.04 pp CI95 [-1.58, +1.39]**; intent 82.22 -> 82.13, **-0.09 pp CI95 [-1.54, +1.32]**: **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on both metrics (no observable gain on TRAIN Fold A; the GEPA family reproduces the Training-Free GRPO family's shape: fuller reach, no pooled effect, the same strata lose)**. Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.60 vs 63.63 (-0.04 pp, CI95 [-1.58, +1.39]) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.54, +1.32]); both guards fail by width only, with intervals wider than CELL-2's. The derangement twin reads 62.87 (-0.76, CI95 [-2.39, +0.76]) and 81.94 (-0.28, CI95 [-1.51, +0.89]); arm minus twin is +0.73 pp SLU and +0.19 pp intent (descriptive): the GEPA content sits slightly above its own form control, inside the noise band. Reach is far fuller than the v2 store's (299 of 448 values supplied; Solver 93 %, Reviewer 91 %, Planner 90 % of rows against 68 / 64 / 18 %) at a higher cost (prefilled tokens +14 %, GPU-h +6 %, 4.17 contacts per row), and it buys no pooled effect. The per-scenario table has the same shape as both TF-GRPO cells: general -9.4 SLU / -8.3 intent (twin -18.7 / -5.0), news -6.3, social -4.4, music -4.2 against audio +7.0 / +6.7, weather +7.8, datetime +4.7, iot +3.7. Against the Stage-2 lock B5e official the arm is +1.26 SLU [-0.22, +2.78] and +2.04 intent [+0.49, +3.54]. Two families with different authoring mechanisms (per-row advantage statements; per-group reflective proposals) reproduce one pattern: strata the store covers gain, strata it does not cover pay a form cost, the pool nets to zero -- the lever is WHERE the store is applied (iteration 3, provisional decision 110, the scenario-gated application policy now flying as CELL-3 on DEV-2000-ADDED), not which family authored it. Comparing GEPA against Training-Free GRPO head to head is a separate read with its own preregistration and is not made here. Stage-3 algorithm label gepa-reflective-pareto-v1 (decision 101). Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md`.



## 2026-09-24: cell CELL-3, the coverage-gated stage3-deltas-v2 store on the fresh roster DEV-2000-ADDED (Fable 5.1)

Runs SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1 (4,090 contacts, 1.649 GPU-h; the roster's own null h_SLU 1.2525 / h_intent 1.1520, sealed before the arm's contrast), SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1 (4,178 contacts = 4.18 per row, 1.742 GPU-h) and its derangement twin SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1 (4,084 contacts), all FINALIZED at flight commit a9b48dfc (SAEA-Batch-Chain-CELL3), scored once each with the devel official scorer, read paired and clustered by utterance against the sealed B6 PLAN arm (65.40 / 76.60): official pooled SLU-F1 65.40 -> 63.95, **-1.44 pp CI95 [-2.88, -0.05]** (measured loss: **HARMFUL** on the SLU guard by the registered rule); intent 76.60 -> 76.60, 0.00 [-1.01, +1.00] (non-inferior); twin +0.38 [-0.97, +1.75] / 0.00 (NEUTRAL), arm minus twin -1.82 pp SLU: the loss is the store's content on this roster, not the form of carrying a supply. The fresh-roster loss diagnostic (docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md) places run-to-run noise at about +-2 pp on 355-row splits, the store's attributable part at -0.35 pp above its own null (entity precision, date +29 FP), harm diffuse over 120 values, no Fold A -> DEV transfer, and a perfect-gate bound of about PLAN. Stage-3 algorithm label tfgrpo-semantic-advantage-v1 (operators update + context_application; the gate is the iteration-3 application policy). Owner decision 111 closes the semantic-delta application line. Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md`.


## 2026-09-25: complete-system evidence-path policy (root)

NOT QUALIFIED. Both 625-input arms completed and were scored once. Official SLU-F1 60.9636 -> 61.5083, +0.5448 pp CI95 [-0.8827,+1.9986]; intent 71.84 -> 71.20, -0.64 pp CI90 [-2.24,+0.96]. Neither registered gate passes. Treatment exposed tool schemas in 701 Reviewer requests but made zero tool calls. All 13/10 complete reasoning repairs survived delivery. Root source review found named-store prefixes already changed first-Perception evidence on all625 inputs; this is not a pure tool-schema contrast. No adoption, forced-call rescue, automatic repeat or RL claim. Full strata, costs, source pins and next-system decision: docs/results/2026-09-25-slurp-evidence-path-system-verdict.md; docs/receipts/continuation/2026-09-25-evidence-path-system-closure.json.

## 2026-09-25: family VAR-1, the six construction-variant arms on the 625-row R01C TRAIN roster, and the cross-flight A/A floor they measure (records closure)

Runs SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1 (2,590 contacts = 4.144 per row, 1.0589 GPU-h), -PLANR- (2,591 = 4.146, 1.0294), -EX-K10- (2,576 = 4.122, 1.0019), -EX-K30- (2,572 = 4.115, 1.0440), -EX-DIV- (2,598 = 4.157, 0.9997) and -PER-K16C5- (2,576 = 4.122, 1.1466), all six FINALIZED at flight commit 3ade29ff, plus SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1 (16 engineering contacts, attempt OPENED): 15,503 generation contacts and 6.2805 GPU-h over the six arms (15,519 contacts across the family), zero tool calls, zero ASR/encoder/scorer/network contacts in the read, paid API 0. Official pooled SLU-F1 PLAN 58.5066, PLANR 60.3755, EX-K10 60.4440, EX-K30 60.4606, EX-DIV 58.6794, PER-K16C5 58.6673: **CONSTRUCTION READ, NO STABLE SUPPLY WINNER, NO ADMISSION**. **The correction that decides this family: PLANR is the request-identical replicate of PLAN and beats it by +1.8689 pp, CI95 [0.4121, 3.3599] (CI90 [0.6427, 3.1253]) -- a pure A/A contrast at n = 625 whose interval excludes zero, and a bigger difference than any variant makes against it.** Against PLANR, EX-K10 is +0.0684 pp CI95 [-1.4816, 1.5823] and EX-K30 +0.0851 pp [-1.4704, 1.5990], while EX-DIV reads -1.6962 pp [-3.3898, -0.0611] and PER-K16C5 -1.7082 pp [-3.3709, -0.0662]; the original positive contrasts against PLAN (EX-K10 +1.9373 [0.3626, 3.5180], EX-K30 +1.9540 [0.4842, 3.4500]) are therefore the replicate gap, not a repeatable optimization benefit, and **reading a variant against PLAN instead of PLANR repeats the coordinator's own error**. Measured cross-flight A/A floor for a 625-row construction roster: the realized request-identical difference is **1.87 pp** (1.8689) with own-null CI95 half-widths h_SLU 1.4739 / h_intent 1.7600 sealed before the contrasts, against a WITHIN-flight null of h_SLU 0.735 / h_intent 0.000 at n = 200 -- the band is between flights, not inside one. Diagnostics: candidate coverage 77.76 % (PER-K16C5 80.32 %, far below the owner's 95 % priority); 191 of 625 rows have no gold entities and 108-119 of them still receive entities (56.54-62.30 %); official-count utility feedback (F0 = 0.5850662, count units) moves no variant above PLANR. Stage-3 algorithm label shared-rollout, operators rollout + scoring (no update, selection or context_application operator runs in this family). Read: `docs/results/2026-09-25-slurp-var1-complete-evidence.md` and `docs/results/2026-09-25-slurp-var1-feedback-v2.md`; read root SLURP-VAR1-VARIANT-READ-V1-CORRECTED-V2 under SPEECHRL_DATA_DIR/analysis.

## 2026-09-25: family VAR-2, per-row supply-variant interleaving at the Solver, ENGINEERING-CLOSED WITHOUT A NUMBER (records closure)

Runs SAEA-SLURP-STAGE3-VAR2-SUPPLY-VARIANTS-R01C-V1 (ABORTED after 224 realized generation contacts and 804.911625 speech-audio seconds) and its sole registered recovery SAEA-SLURP-STAGE3-VAR2-SUPPLY-VARIANTS-R01C-RECOVERY-V1 (ABORTED 2026-09-25 10:36:23 UTC after 441 contacts and 1,619.87425 speech-audio seconds), each with its four-row engineering smoke at 28 contacts: **721 generation contacts across both attempts and both smokes**, no complete manifest, no official score, no GPU-hour integral recorded. **ENGINEERING-CLOSED: NO EFFECTIVENESS RESULT, NO PARTIAL READ.** Named cause: the exk10 revisited Solver request carried 40 cumulative evidence items against a declared max_supplied_items of 38, and the payload boundary correctly refused it before sending; the first failure had been a different consequence of revisits (newly resolved increments compared against cumulative acquired evidence), and the recovery proof covered cumulative identity and simple revision but never the full cumulative cardinality envelope, so four passing engineering rows did not establish it. No partial answers, task scores, winner selection or selective row reuse was performed. **This is not evidence that supply actions are ineffective**, and a third attempt is forbidden: no appended attempt, no enlarged bound with a silent resume, no rename of the same recovery as another experiment. A future grouped-supply design must first define whether the bound covers one visit or the whole allowed revision horizon, then prove the maximum reachable cumulative supply and fit the actual request. Stage-3 algorithm label shared-rollout, operators rollout + scoring. Read: `docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md`; receipt `docs/receipts/continuation/2026-09-25-var2-final-closure.json`.

## 2026-09-25: cell VERIFY-1, self-selection over the five sealed ROLL-1 samples (recovery flight) (records closure)

Run SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-V1 (625 contacts = 1.00 per row, 2,726.847187 speech-audio seconds, 0.08165 monitored active generation GPU-h, FINALIZED 2026-09-25 09:04 UTC at flight commit 5366949c) with its four-row smoke at 4 contacts; the original SAEA-SLURP-STAGE3-VERIFY-1-V1 opened no attempt and its smoke charged 0 contacts, because the complete live-phase fit count had been registered as the generation ceiling (one named recovery, receipt `docs/receipts/continuation/2026-09-25-verify1-fit-count-recovery.json`). 625 of 625 rows, every choice parsed, no malformed placeholder selected. Official pooled SLU-F1: chosen 58.5816 against single-sample mean 57.8807, **+0.7009 pp CI95 [-0.2551, 1.6507]** (the primary benefit gate needs a lower bound above zero, so it fails); medoid 57.9064, chosen minus medoid +0.6751 pp [-0.3923, 1.7348]; the label-informed references row_f1_oracle 64.4664 and utility_oracle 66.6360 are offline bounds, not runtime policies. Intent 70.7200 against 70.1760, **+0.5440 pp CI95 [0.0320, 1.0880]** -- the registered operational non-inferiority guard passes, and **this interval excluding zero makes self-selection the only non-noise signal in the Stage-3 record so far**, which is a reason to keep the line open, not a demonstrated benefit: **BENEFIT NOT PROVEN, NO SYSTEM ADMISSION**. Subgroups are descriptive only (420 content-distinct rows +0.9973 [-0.2734, 2.2731]; the 225 label-differing rows +2.0621 [0.3987, 3.7842] depend on labels and can never be an online trigger); all 205 identical-answer rows chose position 1, compatible with deterministic tie-breaking. Paired utterance-cluster bootstrap, 10,000 draws, seed 20260915. Do not enlarge sampling, promote the selector or open the evidence-driven Reviewer successor on this read. Stage-3 algorithm label inference-time-verification-v1, operator selection only (no per-candidate score, ranking or margin is claimed). Read: `docs/results/2026-09-25-slurp-verify1-complete-evidence.md` (report SHA-256 a3f9d7c71dc44b309cd995063ad3a2e952b81960823ce9b05a39c2c5fbca7060).

## 2026-09-25: cell F10, the explicit empty-answer demonstration form in the exemplar view (records closure)

Runs SAEA-SLURP-STAGE3-F10-CONTROL-R01C-V1 (2,585 contacts, 11,295.736625 speech-audio seconds, campaign 10:48:53-12:04:40 UTC = 75m47s) and SAEA-SLURP-STAGE3-F10-EMPTY-R01C-V1 (2,552 contacts, 11,148.6175 s, 12:05:11-13:15:34 UTC = 70m23s), both FINALIZED with exactly one complete official scoring job each, plus a four-row smoke at 16 contacts: **5,153 contacts across the family**; source frozen at 54b6e151481129f4e1915c37f42a88ade687930b through generation and scoring; the manifests separate no preparation, sealing, scoring or idle category, so **no GPU-hour integral is asserted for this family** and the wall times above are campaign windows, not utilization. Official pooled word/character SLU-F1 59.5717 -> 59.9083, **+0.3366 pp CI95 [-1.4185, 2.2853]**: the lower endpoint does not exceed zero, so the primary quality criterion fails -- **BENEFIT_NOT_PROVEN, NOT_QUALIFIED, CLOSED**. Intent 70.72 -> 70.88 with a one-sided 95 % lower bound of -1.12 pp against the frozen -1.44 pp protection margin (guard passes; passing protection cannot replace primary efficacy). Equal-scenario SLU-F1 +1.4275 pp [-0.6905, 3.4153], intent +0.3193 pp [-1.2166, 1.9048]; 10,000 paired utterance-cluster draws, seed 20260915. The mechanism did what it was designed to do and it was not enough: empty-gold exact-entity FP -22 (QA contributes -21 of them) against nonempty-gold FN +13 and mean per-row SLU-F1 -0.6774 pp -- a specificity/omission tradeoff, not a reliable correction rule, and no post-hoc QA-only application is licensed. First Solver requests used exactly 20 examples with identical ordered example IDs on all 625 pairs, 2,414 of 12,500 first-visit selections empty (19.312 %) in each arm. The first derived comparison undercounted terminal dispositions (a reader that checked a legacy location instead of terminal_disposition.reason); comparison.json is preserved as superseded and comparison-v2.json is authoritative, with no generation or official scoring repeated. Stage-3 algorithm label shared-rollout, operators rollout + scoring. Read: `docs/results/2026-09-25-slurp-f10-complete-verdict.md`; receipt `docs/receipts/continuation/2026-09-25-f10-complete-verdict.json`.

## 2026-09-25: the evidence-path tools-availability policy, its cost accounting and its input-isolation defect (records closure; completes the root note above, which it does not re-decide)

Runs SAEA-SLURP-STAGE3-EVIDENCE-PATH-CONTROL-R01C-V1 (2,704 contacts, 11,891.7161 speech-audio seconds, 0.8493 GPU-h observed generation utilization integral at a mean 76.08 % utilization) and SAEA-SLURP-STAGE3-EVIDENCE-PATH-TOOLS-R01C-V1 (2,728 contacts, 11,956.5544 s, 2.0944 GPU-h at a mean 87.12 %), both FINALIZED with exactly one complete official score each, plus a four-row smoke at 16 contacts and zero tool calls: **5,448 contacts across the family**; source checkout clean at da443cdc1027b3c01034c26485805240ec0e671d through source validation; the utilization integrals are trapezoid-integrated monitor samples inside the recorded generation windows, and the fixed control-then-tools order forbids reading the speed difference as tool-execution cost. Official pooled SLU-F1 60.9636 -> 61.5083, **+0.5448 pp CI95 [-0.8827, +1.9986]** (lower bound not above zero); intent 71.84 -> 71.20, **-0.64 pp CI90 [-2.24, +0.96]** (lower bound not above the frozen -1.44 pp margin, and failing to establish protection is not a proven loss): **NOT QUALIFIED**; no default adoption, no subgroup rescue, no forced-tool recovery, no larger sampling. The treatment exposed native lookup schemas in all 701 Reviewer requests and recorded zero tool attempts, accepted calls, rejected calls or result events across all 625 episodes, so this measures a realized availability policy, not the value of an invoked tool. **The named defect belongs in this ledger: input isolation held only up to a prefix.** All 625 paired first-Perception requests shared the speech-packet hash, task instruction, history, empty tool-schema list and supplied evidence IDs, and none shared evidence bytes -- the tools arm prepended the exact string [knowledge store=intent-boundaries role=intent-boundaries] to every evidence card, 293,938 extra characters over 625 requests, before any Reviewer decision. The named-store renderer in rails/knowledge_stores.py produces it and rails/phase_tools.py applies it under named-store authority, so tool configuration changed earlier model context as well as later schemas: the interpretation that this arm isolates Reviewer tool-schema availability is **withdrawn**, the sealed inputs and answers are preserved, and any future matched policy must prove rendered-prefix identity before the intended action boundary. Stage-3 algorithm label shared-rollout, operators rollout + scoring (fixed-policy comparison, no learned-policy claim). Read: `docs/results/2026-09-25-slurp-evidence-path-system-verdict.md`; receipt `docs/receipts/continuation/2026-09-25-evidence-path-system-closure.json`.

## 2026-09-27: cell CONV, the 70-row conversion probe of the AGREE arm on TRAIN Fold A (Fable 5.1)

Run SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1 (attempt FINALIZED, manifest COMPLETED at flight commit 9255ac71; 289 generation contacts of the 770 cap, 707.123 speech-audio seconds, 7.43 monitored GPU-active minutes = 0.1239 GPU-h; the FIT identity opened no attempt) flew the registered AGREE treatment, treatment only, on the 70 TRAIN Fold A rows whose gold intent boundary entry it newly delivers, read per row and offline against the sealed PLAN comparator's answers on the same rows. The recipe's delivery gate held on all 70 rows. **m = 32 of 70 rows moved from a wrong intent to the gold intent: P(correct given newly delivered) = 45.71 %, Wilson CI95 [34.57 %, 57.30 %], Clopper-Pearson [33.74 %, 58.06 %]**; reverse count 0 (zero by construction, confirmed); 22 rows keep the same wrong intent (13 byte-identical to the comparator, 59.1 %) and 16 deliver a different wrong intent. Dispositions all zero; Planner REVISE on 3 rows. **DESCRIPTIVE: a conditional rate on a gold-selected roster; no pooled, roster-level, effectiveness or generalisation claim, and no admission.** Stated, not applied: under owner decision 133 (intent primary) the AGREE arm's re-declared expectation is 32 x 0.092615 = 2.9637 pp intent against its 2.5 pp bar at n = 1,080, which needs m >= 27 (m is above it by 5 rows; the CI95 in rows, [24.2, 40.1], spans that line); under the retired SLU-F1 framing 1.3317 pp against a threshold of 61 rows (below). The prior: 86 of the 191 intent-wrong Fold A rows already received the gold entry and were wrong anyway. Whether the arm is re-declared, flown as a no-harm base item under decision 127, or closed is not decided here. Source: [read](2026-09-27-slurp-conv-probe-read.md), SHA-256 `693c9e2707c981952222997931c8c2dbbe1122ef558b3b67d3901b986bfc80c5`; machine result `analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1/read-v1.json` under `SPEECHRL_DATA_DIR`, SHA-256 `c1aa690c93ed1600ee08fefb35e5944c995190a167eacb82f2c0cd8a63af7ce8`; driver `scripts/analysis/slurp_conv_probe_read.py`, SHA-256 `8866a52aceb4b9dc2778824da8fea752955ac0cb64077c336a698502b0948b3d`.
