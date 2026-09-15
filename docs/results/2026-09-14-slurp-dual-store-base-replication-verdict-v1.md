# SLURP agent-base matched replication: root verdict

The matched replication passes the unchanged exploratory advancement rule. This is the second positive direct-versus-native comparison of this exact max512 dual-store package on the same discovery roster. Freeze the package as the current useful agent base; retain its substantial remaining errors as the optimization workspace.

## Complete paired quality

| Population | Direct official SLU micro F1 | Agent official SLU micro F1 | Delta (pp) | Speaker-cluster CI90 (pp) | Equal-scenario delta (pp) |
| --- | ---: | ---: | ---: | --- | ---: |
| NEW500 | 35.8906 | 50.6876 | +14.7970 | [+11.5245, +18.0112] | +12.1257 |
| DEV1000 | 35.6750 | 50.2983 | +14.6233 | [+12.5159, +16.8040] | +13.2395 |
| OLD500 | 35.4531 | 49.8985 | +14.4455 | [+11.1780, +17.5594] | +13.4441 |

NEW500 is the registered primary population. DEV1000 and OLD500 are sensitivity populations. All were historically exposed; NEW500 is not a fresh holdout. Use 10,000 whole-speaker paired bootstrap draws, seed 20260913, with the frozen metric-specific seed offsets for row-mean outcomes. Scenario-stratified sensitivity intervals remain in the complete machine result. Pooled official micro F1 is derived from aggregate word/character TP, FP and FN; it is not mean per-sample F1.

The first same-package pair reported NEW500 36.1437 to 50.4479 (+14.3042 pp, CI90 [11.2445, 17.5009]). The fresh pair passes independently; no averaging is used to rescue a failed replica. This establishes useful exploratory repeatability, not unseen-data generalization, component causality or training-free RL.

## NEW500 secondary outcomes

| Metric | Direct | Agent | Delta (pp) | Cluster CI90 (pp) |
| --- | ---: | ---: | ---: | --- |
| scenario_action_exact | 73.2000 | 77.0000 | +3.8000 | [+0.9434, +6.7308] |
| scenario_exact | 81.4000 | 85.2000 | +3.8000 | [+0.8386, +6.7310] |
| action_exact | 75.2000 | 78.2000 | +3.0000 | [+0.1838, +6.0241] |
| slot_f1_exact_f1 | 13.2667 | 22.5643 | +9.2976 | [+6.4579, +11.9392] |
| slu_f1_f1 | 18.8829 | 35.5190 | +16.6360 | [+13.9553, +19.2583] |

## Root diagnosis and next mechanism boundary

The complete DEV1000 native trajectory has 831 candidate-covered and 169 candidate-missing samples. Of covered samples, 756 end with the correct intent and 75 do not. Final intent correctness is 756/1000; among these, 477 have nonexact entities and 279 have exact entities. Perception rank one is correct for 765 rows: downstream resolution rescues 11 and harms 20. Candidate lists do not constrain the final legal answer space, but no missed-gold sample is rescued here. The observed candidate coverage is therefore a practical bottleneck, not a formal architectural ceiling.

There are 5,040 model contacts: Perception 1,000; Solver 1,011; Reviewer 2,018; Planner 1,011. Reviewer makes 1,007 successful task-contract calls, with zero failed/rejected tool events and no speech-observation tool use. Planner requests 11 revisions across 1,000 episodes. All 2,018 Reviewer requests already expose slot-contract value IDs in the verified supplied-evidence metadata. Adding access to those same cards is not a justified remedy. The shared omission and spoken-surface instructions are also already present. Static contract lookups can validate legal labels and types, but provide no newly decoded speech evidence. These observations motivate testing information gain and actual correction behavior; they do not prove that review itself caused the errors.

Prioritize two parallel design questions on released TRAIN evidence: (1) what discriminative evidence or bounded candidate expansion can raise gold inclusion toward 95%; (2) what observable disagreement, task-specific value explanation or targeted speech tool output can resolve covered ambiguities and entity errors. Do not force extra calls on every episode, equate lexical overlap with understanding, use evaluation gold as a runtime trigger, or add unchanged reminder text as if it were a new mechanism. An observation should answer a named uncertainty. Reviewer identifies the problem, Planner selects and budgets the action, and Solver retains answer authority.

The previous enhanced-tool/refresh flight exhausted its recovery allowance and remains closed. A concrete distinct successor requires root design and normal prospective admission; this result is not permission for a third replay. Training-free RL trajectory factors and policy updates follow a stable base and a demonstrated optimization workspace. Root-led engineering is not algorithm innovation.

## Reliability and scope

Five final native outputs are malformed; all remain in the complete analysis. No final response hits the 512-token limit or ends by length. The primary outcome improves despite heterogeneous scenario deltas. Full task quality, failure cases and the complete strata remain visible. Candidate-to-card selection auditing is unavailable for this older campaign producer because it did not persist genuine FlightReceipts; it must not be reconstructed. The new Audio2Tool proof uses the repaired shared persistence path.

Both raw attempts are FINALIZED and each complete manifest was officially scored once. Direct used 1,000 model calls and 2,884.7936875 repeated speech seconds; the agent used 5,040 calls and 14,552.029125 seconds. These are descriptive compute measures. No new scorer, model, ASR, encoder or tokenizer was invoked for this paired read.

## Complete scenario tables

### NEW500

| Scenario | n | Direct micro F1 | Agent micro F1 | Delta (pp) |
| --- | ---: | ---: | ---: | ---: |
| alarm | 30 | 32.9598 | 48.7188 | +15.7590 |
| audio | 2 | 0.0000 | 0.0000 | +0.0000 |
| calendar | 33 | 36.8896 | 48.9983 | +12.1087 |
| cooking | 9 | 46.2908 | 62.5000 | +16.2092 |
| datetime | 33 | 29.9412 | 50.3613 | +20.4201 |
| email | 33 | 21.7391 | 43.2114 | +21.4722 |
| general | 33 | 17.4515 | 20.5882 | +3.1367 |
| iot | 33 | 55.8069 | 67.1854 | +11.3785 |
| lists | 32 | 38.0561 | 45.1081 | +7.0519 |
| music | 23 | 34.6502 | 38.0228 | +3.3726 |
| news | 32 | 35.4831 | 42.9661 | +7.4830 |
| play | 32 | 44.2451 | 51.2704 | +7.0253 |
| qa | 32 | 50.3709 | 68.2424 | +17.8714 |
| recommendation | 32 | 62.7368 | 55.5974 | -7.1394 |
| social | 33 | 18.5333 | 47.1683 | +28.6351 |
| takeaway | 12 | 38.3234 | 31.7881 | -6.5353 |
| transport | 33 | 27.5120 | 57.9567 | +30.4447 |
| weather | 33 | 21.4582 | 51.0268 | +29.5686 |

### DEV1000

| Scenario | n | Direct micro F1 | Agent micro F1 | Delta (pp) |
| --- | ---: | ---: | ---: | ---: |
| alarm | 58 | 29.3069 | 52.1988 | +22.8918 |
| audio | 30 | 29.3785 | 39.2860 | +9.9075 |
| calendar | 61 | 35.2482 | 43.3951 | +8.1469 |
| cooking | 37 | 46.1037 | 63.0857 | +16.9820 |
| datetime | 61 | 32.0729 | 50.2828 | +18.2099 |
| email | 61 | 27.3408 | 40.4325 | +13.0916 |
| general | 61 | 23.5272 | 28.0350 | +4.5078 |
| iot | 61 | 54.5701 | 63.1007 | +8.5306 |
| lists | 60 | 40.6531 | 45.1421 | +4.4889 |
| music | 51 | 38.8187 | 39.3426 | +0.5239 |
| news | 60 | 31.3582 | 45.9305 | +14.5723 |
| play | 60 | 45.6303 | 51.5988 | +5.9686 |
| qa | 60 | 51.2852 | 64.6522 | +13.3670 |
| recommendation | 60 | 48.9577 | 53.1611 | +4.2034 |
| social | 60 | 18.7064 | 49.7304 | +31.0240 |
| takeaway | 39 | 39.8190 | 43.1024 | +3.2834 |
| transport | 60 | 30.7681 | 56.5292 | +25.7611 |
| weather | 60 | 17.2782 | 50.1276 | +32.8494 |

### OLD500

| Scenario | n | Direct micro F1 | Agent micro F1 | Delta (pp) |
| --- | ---: | ---: | ---: | ---: |
| alarm | 28 | 24.9600 | 55.6557 | +30.6957 |
| audio | 28 | 29.3785 | 39.2860 | +9.9075 |
| calendar | 28 | 32.2034 | 33.9992 | +1.7958 |
| cooking | 28 | 46.0530 | 63.2504 | +17.1974 |
| datetime | 28 | 34.5314 | 50.1784 | +15.6470 |
| email | 28 | 32.5893 | 37.6395 | +5.0502 |
| general | 28 | 30.6383 | 35.8056 | +5.1673 |
| iot | 28 | 52.9279 | 58.6439 | +5.7160 |
| lists | 28 | 42.5908 | 45.1728 | +2.5820 |
| music | 28 | 42.2034 | 40.5145 | -1.6889 |
| news | 28 | 26.7020 | 49.9032 | +23.2012 |
| play | 28 | 47.2321 | 51.9315 | +4.6994 |
| qa | 28 | 52.4094 | 60.0096 | +7.6001 |
| recommendation | 28 | 34.0157 | 50.7053 | +16.6896 |
| social | 27 | 18.9723 | 53.8234 | +34.8511 |
| takeaway | 27 | 40.2377 | 46.4058 | +6.1681 |
| transport | 27 | 34.5417 | 54.9501 | +20.4084 |
| weather | 27 | 13.0435 | 49.3495 | +36.3060 |

## Source custody

Root verdict: DATA/coordination/slurp-dual-store-base-replication-v1/root-verdict-v1.json, SHA256 c0d99f1aab031f83c8f75288e08cc18e01ede79323f4134fb04a55a65611a3c8.

Complete paired result: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-DIRECT-VS-NATIVE-DUAL-STORE-BASE-REPLICATION-PAIRED-ANALYSIS-V1/score-contrasts.json, SHA256 ae7f4ed06b76eaa513edbb3d4589d95ca351e32492103d78ce544b26755042ab.

Native diagnostics: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-DIRECT-VS-NATIVE-DUAL-STORE-BASE-REPLICATION-PAIRED-ANALYSIS-V1/native-perception-diagnostics.json, SHA256 75a1df53f2ee80e53a84fa6c6d012733a09a540f5a9ac29ccbe79338310b7687.

Read-order deviation is retained: before the registered paired read, a campaign-log tail exposed the last native output and self-review while retrieving terminal metadata. No aggregate scores or gold were exposed by that tail, and no method, cohort, seed or decision rule changed. The root release binds this event and the immutable sources.
