# SLURP complete-task agent: intent signal, entity outcome unresolved

Status: INTENT_SIGNAL_ENTITY_UNRESOLVED_NO_FULL_TASK_ADMISSION.
Date: September 11, 2026. Authority: OWNER014-021. This closes the registered three-arm bounded discovery family; it does not close the broader system or training-free optimization objective.

## Root decision

Retain the compact intent-association agent as a provisional candidate for matched full-system replication. The historical-knowledge fixed agent reduces intent accuracy. Adding observed TRAIN intent beside the same retrieved fillers improves intent relative to that agent, and its derived comparison against direct is positive on the primary population. Primary entity micro SLU F1 remains unresolved. Do not select a favorable secondary population in place of NEW500, claim a complete SLU gain, or describe the whole contrast as a pure semantic-knowledge effect.

The operational audit found malformed raw responses and initial-state variation. These are disclosed below; their cause is not established. No configuration, stopping rule, raw answer, scorer or estimator was changed using intermediate results. Preserve this family and its first scores unchanged.

## What actually ran

All arms used current shared FlightRuntime, EvidenceAgentController and OpenJiuwen, the same retained decoder-only process, no mmproj, c65536/np4 and max256. Direct generated its own full task output. Knowledge and frame each generated a live full-task hypothesis, invoked the registered fixed knowledge tool and generated their own full final answer. This is fixed tool invocation, not model-selected adaptive acquisition. No reviewer, additional observation or admitted corrective memory was used.

Each arm covers the exact same DEV1000. NEW500 is primary and historically exposed; OLD500 and DEV1000 are secondary. All60 legal paired intents and55 entity types remained available. The frame adds an observed intent-role association, not a required-slot rule or a fully developed contrastive ontology.

The two knowledge snapshots preserve11514 keys/values and50628 TRAIN memberships. Query/key vectors and selected IDs/order are identical across the two agent arms for all1000 queries; each supplies five values. Root joined1000 tool attempts/results per agent to the same sample's actual first response and query-state hashes. No failed tool dispatch occurred. The legacy manifest cost.tool_calls=0 does not count these harness tool invocations; the USE records do.

| Arm | Final outputs | Core generations | Actual fit endpoints | Malformed final outputs |
|---|---:|---:|---:|---:|
| Direct | 1000 | 1000 | 3001 | 0 |
| Historical knowledge agent | 1000 | 2000 | 6002 | 42 |
| Compact intent-frame agent | 1000 | 2000 | 6002 | 0 |

All5000 wire responses finished with stop. Maximum completion tokens were77,81,121 respectively; none reached256. No final response text was empty. There is one contact per declared phase, with no additional generation retry contacts. Do not infer a rich fallback count merely from an absent event name.

## Primary results and uncertainty

Each full manifest was scored once with slurp-slu-official, slurp-slu and cost, retaining per-sample statistics on that first pass. Official/ported micro identities align within1e-6, with no label projection. All attempts are FINALIZED from verified saved scores without rescoring. Root independently recomputed every natural point estimate and810 scenario/metric checks.

Paired speaker-cluster bootstrap:10000 replicates, seed20260903 with the frozen metric offsets, CI90. NEW500 contains115 speakers; OLD500111 and DEV1000124. These exploratory intervals are unadjusted across the two main contrasts and two main outcomes; they do not measure between-run variability or provide confirmatory familywise guarantees.

| NEW500 outcome | Direct | Historical knowledge | Compact frame |
|---|---:|---:|---:|
| Intent accuracy, % | 73.000 | 67.600 | 75.600 |
| Official pooled micro SLU F1, % | 37.363 | 38.099 | 39.597 |
| Mean per-row SLU F1, % | 19.770 | 21.833 | 23.664 |
| Unparsed final rows | 0 | 20 | 0 |

| Contrast | Intent delta pp, speaker CI90 | Micro SLU F1 delta pp, speaker CI90 | Registered description |
|---|---:|---:|---|
| Knowledge minus direct, main | -5.400 [-7.371,-3.390] | +0.736 [-2.137,3.602] | Intent negative; entity unresolved |
| Frame minus knowledge, main | +8.000 [5.882,10.115] | +1.498 [-0.554,3.692] | Intent positive; entity unresolved |
| Frame minus direct, derived | +2.600 [0.693,4.398] | +2.234 [-0.378,4.826] | Intent positive; entity unresolved |

Frame versus direct repairs25 intent decisions and harms12 on NEW500. Frame versus knowledge repairs49 and harms9. Knowledge versus direct repairs10 and harms37. These paired counts do not turn the derived comparison into a preregistered main contrast.

Equal-scenario NEW500 intent deltas are-5.732,+8.570,+2.838pp, and micro deltas+1.137,+2.312,+3.449pp in the same contrast order. The complete [population table](2026-09-11-slurp-task-agent-all-populations.md) and [scenario appendix](2026-09-11-slurp-task-agent-strata.md) retain every main-outcome stratum. All additional metrics and the scenario-stratified row-bootstrap sensitivity are in the hash-pinned paired artifact.

Do not hide the secondary conflict: frame minus knowledge micro F1 is-2.405pp on OLD500, CI90[-5.236,0.251], and-0.407pp on DEV1000, CI90[-2.150,1.313]. The derived frame-minus-direct DEV1000 micro interval is positive,+1.928pp [0.160,3.666], but this cannot replace the unresolved primary NEW500 entity result.

Mean row F1 is not pooled micro F1. Under the official-compatible convention, empty gold and empty prediction have row F1=0; pooled metrics sum word/character TP, FP and FN before calculating F1.

## Entity mechanism and remaining knowledge gap

Saved official-count reconciliation uses locked devel entities only for offline attribution and the unchanged parsed final outputs. It invokes no scorer or model. A type swap is a descriptive equal-normalized-filler heuristic, not a causal diagnosis.

| NEW500 diagnostic | Direct | Historical knowledge | Compact frame |
|---|---:|---:|---:|
| Matched same-type surface pairs | 155 | 162 | 170 |
| Heuristic type swaps | 20 | 23 | 19 |
| Spurious entities | 75 | 86 | 95 |
| Missing entities | 314 | 304 | 300 |

The frame supplies more matched entity surfaces and fewer omissions than direct, but also introduces more spurious entities. On DEV1000, missing entities change627 to597 and spurious entities164 to185. Intent associations alone do not settle whether an entity is present, which role it serves, or which surface value current speech supports. These presence/role/grounding distinctions remain useful construction hypotheses, not validated new rules. Preserve the earlier negative source-span result; more source text is not an established remedy.

Attribution v2 supersedes only v1's displayed parsed-count extraction. V1 mistakenly counted a field absent from its numeric-only view; its attribution masses are unchanged. Neither correction modifies a score or raw output.

## Operational and inference limitations

Knowledge's42 unparsed final outputs are malformed raw JSON and contain an unexpected token pattern. All42 match the original wire message content, so scoring or delivery did not introduce the corruption. Exact standalone oho occurs in57 knowledge finals and15 frame first-phase outputs, but in no direct output, no frame final and no supplied knowledge view. It is absent as a word from the frozen src/configs. This establishes a symptom and provenance, not its cause.

Knowledge/frame first-phase responses are byte-identical for823/1000 samples. The remaining177 differ in raw text; the identity diagnostic found either different strict JSON or a non-JSON response, so it does not establish uniform semantic equivalence. Their model-visible first-phase request semantics were matched in the prior whole-roster wire proof, but realized live states are not all identical. The frame contrast therefore includes live initial-state variation, added-label/format/length differences and output-validity differences. Neither semantic causation nor a service/cache fault is established. A subsequent matched replication should audit this stability before declaring the system locked.

Root also accidentally serialized a response-bearing VerifiedBundle after the direct seal and before the later seals. No score/reference or intentional quality review preceded the formal read release, and no adaptation followed the serialization, but an untouched result-read barrier cannot be claimed. See the [deviation record](2026-09-11-slurp-task-agent-read-deviation.md). Keep this limitation with every report of the family.

## Resource and pipeline accounting

No model reload or service geometry change occurred. Root worker leases were explicitly released after each verified seal; the service remains resident.

| Measurement | Direct | Historical knowledge | Compact frame |
|---|---:|---:|---:|
| Prompt tokens | 2279117 | 5472410 | 5456068 |
| Completion tokens | 25520 | 51857 | 51642 |
| Speech seconds, repeated phases charged | 2884.794 | 5769.587 | 5769.587 |
| Fit-inclusive device-utilization GPU hours | 0.064288 | 0.207533 | 0.209570 |
| Contact-window seconds | 413.316 | 1054.629 | 1040.968 |
| Time-weighted device utilization, % | 55.995 | 70.842 | 72.476 |

Total fit-inclusive utilization GPU time is0.4813917947 hours, within the registered2.5-hour family cap; actual generations5000 and fit endpoints15005 remain within their registered ceilings. The measure is device-wide sampled utilization, not generation-only kernel time, billable cost or a reward. Root recomputed the right-endpoint integral with a20-second interval cap; missing coverage and server-not-ok samples are zero.

The contact-window gaps are503.750 seconds direct-to-knowledge and154.498 seconds knowledge-to-frame. Neither meets the one-minute contact-window target. The first includes root interruption/context handoff and serial worker preparation; the second includes worker validation/preparation. Retaining the service avoided reloads, but does not justify calling these gaps useful GPU work. Endpoint logs have no timestamps, so exact fit CPU-preparation versus generation wall time cannot be reconstructed from these receipts. The sequential three-manifest official scoring batch took97.972 seconds after all seals; subsequent statistical computation/review is scientific decision wait. Report these limits instead of fabricating a detailed time split.

## Next bounded work

1. Complete this closeout and preserve the frame as a provisional candidate. Register a same-roster, unchanged-task direct/frame replication with explicit run/process-stability and unexpected-output checks before any new contact. A fresh internally matched process is a candidate way to separate prior sequence effects; it is not yet a registered run or an established fix.
2. Investigate the output-format symptom from existing evidence before choosing a targeted change. Do not silently repair/rescore this family or infer a memory rule from one malformed-output episode.
3. Construct TRAIN-grounded entity-presence, role and value-form distinctions with supporting cases and limits; validate construction and consumption together. Keep real corrective memory admission separate.
4. Use the [Audio2Tool full-task readiness](2026-09-11-audio2tool-full-task-card-readiness.md) to connect live current observations to the existing card organizer/router through the shared phase/tool path. Its old sealed-predecessor16-row route is not a full all-eight-tier agent.
5. Retain native E21/E22 ASR/entity outcomes. Defer external training-free policy/memory updates until this system and its available decisions have a stable task baseline.

This note admits no new generation, reopens no historical flight and makes no paper-scale claim.

## Reproducibility bindings

Frozen generation/scoring source:1c11d910b1d19c7a862ca67f9b2a535bf830c36a. Protocol SHA2568df5f5df06544f9b17a6def7f2b7b5456008bd35a80cf513fd0f56591120a08a. Root decision DATA coordination/slurp-task-agent-root-decision-v1.json SHA256 62a81d18bc65841cf6b7b2d7e9a3bcc99bc36096fc7213969ffe62925cd5453d.

- paired: DATA analysis/SAEA-SLURP-TASK-AGENT-PAIRED-ANALYSIS-V1/paired-analysis-v1.json, SHA256 a30ef3eb837f5294749caadac8ae1d1e260b6627e29e430e118934ae94d95975.
- entity_attribution: DATA analysis/SAEA-SLURP-TASK-AGENT-PAIRED-ANALYSIS-V1/entity-attribution-v2.json, SHA256 da57ec0f46555914f1a1a5418f19b25680b141bf566cdc8ad2ec91f18a9d2a1d.
- bound_config: DATA analysis/SAEA-SLURP-TASK-AGENT-PAIRED-ANALYSIS-V1/analysis-bound-v1.json, SHA256 b9e40c5cee11a15b4ed794ece1ce6d7a47ce3b376613be7a5679e91a2f31fab3.
- first_scores_settlement: DATA coordination/slurp-task-agent-first-scores-settlement-verification-v1.json, SHA256 99850b935018b0ac38b4b4e9a9b610bcfc4973f80a54d16fb03ee798129a1e95.
- root_paired_check: DATA coordination/slurp-task-agent-root-paired-verification-v1.json, SHA256 04a387e39fabf17e4bcf6e348ff6b5146e7049771977e718a156aac685f75989.
- root_operational: DATA coordination/slurp-task-agent-root-operational-verification-v1.json, SHA256 b6489603273ab2f3ac7713f44c910314f9f4c5f8ab55824c5cdf1ee4ebe08fbc.
- unexpected_token: DATA coordination/slurp-task-agent-unexpected-token-provenance-v1.json, SHA256 4ea0b2c0da25e98ad44a2b565260fdf6d567c4ae15a2f1c7d09f3e8bf17fae24.
- read_deviation: DATA coordination/slurp-task-agent-response-serialization-incident-v1.json, SHA256 34e4c5cbca085906dcd50b07f5c72c0679f6b5b34d35e3e4ff2ca0f63814a9b1.
- direct raw manifest: SAEA-SLURP-TASK-AGENT-DIRECT-V1, SHA256 4d1dec6bd3695553c25041288cb4c536a194ea6b028acd90a2775c492b5108ff.
- knowledge raw manifest: SAEA-SLURP-TASK-AGENT-KNOWLEDGE-V1, SHA256 7065a814a7a2eb0bafc3fbba4dc66adf875d2ee117997ca525a0a1f00f63fd29.
- frame raw manifest: SAEA-SLURP-TASK-AGENT-FRAME-V1, SHA256 4cbd2fac60e35cd9a4f4aa608882e3bf37c2fc814cf5cdc3090552bd50fa2a07.
