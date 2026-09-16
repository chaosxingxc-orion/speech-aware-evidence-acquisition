# Stage-2 results ledger

One row per cell, grouped by carrier and by layer. Owner Decision 14-Q, 2026-09-09. Model-free: this document was assembled with zero model, GPU, tool, embedder, tokenizer, network and audio-decode contacts, from existing verdict notes and receipts, with the owner recovery adding an operational metadata snapshot.

**Scope.** Every cell decided by a verdict note dated 2026-09-04 to 2026-09-09, plus the four entries of docs/receipts/harness-admission.json and registered cells whose scientific decisions remain pending; the 2026-09-09 owner recovery adds operational completion for all seven KV flights without inspecting their score values. Machine-readable twin: `docs/results/stage2-results-ledger.json`. Checked by `scripts/checks/results_ledger_check.py`.

## Current continuation status — source-bound 2026-09-10/11 updates

This table is the current routing layer. The 53 detailed rows and their counts below are an immutable **2026-09-09 historical snapshot**. Their `PENDING`, `not measured`, `verdict note: none`, and `named next step` fields describe what was known then and are superseded where this table names the same historical cell. Current entries do not retroactively alter those decisions, count deterministic derivatives as independent flights, or turn preparation run IDs into generation runs. Every source hash is the SHA-256 of the cited repository file at this ledger revision.

| Current entry | Current status | Registered generation run(s) | Meaning | Authoritative repository source and SHA-256 | Superseded historical row |
|---|---|---|---|---|---|
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
