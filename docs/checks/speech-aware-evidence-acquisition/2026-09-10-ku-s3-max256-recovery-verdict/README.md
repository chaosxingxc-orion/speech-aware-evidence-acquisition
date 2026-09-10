# Recovered KU-S3 max256 component readout

Status: **ADMITTED_COMPONENT: numerical gates and inherited joined-intent protection pass.**

All three new arms completed 1,000 generations and one whole official score each on frozen source `05b0f05e` in one resident decoder-only process. The previous max256 control is descriptive only and was not rescored. All counts and contrasts below come from sealed products; this report adds zero model, tokenizer, encoder or scorer contacts.

The historically exposed NEW500 population is primary. Both registered per-row SLU-F1 CI90 lower bounds exceed zero. The historical scenario-stratified bootstrap is primary; speaker-cluster intervals are sensitivity. Each uses 10,000 replicates and the predeclared seed/metric offsets. These F1 results are row means, not aggregate micro F1.

| Contrast | Population | Metric | Natural delta (pp) | Primary CI90 (pp) | Speaker CI90 (pp) | Equal-scenario delta (pp) |
|---|---|---|---:|---|---|---:|
| form_twin_minus_matched_control_descriptive | DEV1000 | slot_f1_exact_f1 | 2.5400 | [1.3700, 3.7200] | [1.4678, 3.6645] | 2.6036 |
| form_twin_minus_matched_control_descriptive | DEV1000 | slu_f1_f1 | 2.8136 | [1.6068, 4.0089] | [1.7178, 3.9028] | 2.8574 |
| form_twin_minus_matched_control_descriptive | NEW500 | slot_f1_exact_f1 | 3.0400 | [1.4533, 4.6800] | [1.5811, 4.6692] | 4.0495 |
| form_twin_minus_matched_control_descriptive | NEW500 | slu_f1_f1 | 2.9831 | [1.3540, 4.6684] | [1.3607, 4.6324] | 3.7123 |
| form_twin_minus_matched_control_descriptive | OLD500 | slot_f1_exact_f1 | 2.0400 | [0.3930, 3.7333] | [0.3178, 3.8197] | 2.0571 |
| form_twin_minus_matched_control_descriptive | OLD500 | slu_f1_f1 | 2.6442 | [1.0272, 4.2980] | [1.0538, 4.3477] | 2.6633 |
| new_minus_old_control_process_replication_descriptive | DEV1000 | slot_f1_exact_f1 | -0.5600 | [-1.3168, 0.1968] | [-1.2999, 0.1429] | -0.5945 |
| new_minus_old_control_process_replication_descriptive | DEV1000 | slu_f1_f1 | -0.7388 | [-1.5511, 0.0966] | [-1.5646, 0.0686] | -0.7949 |
| new_minus_old_control_process_replication_descriptive | NEW500 | slot_f1_exact_f1 | -1.2533 | [-2.4000, -0.1600] | [-2.3819, -0.2261] | -2.0609 |
| new_minus_old_control_process_replication_descriptive | NEW500 | slu_f1_f1 | -1.0641 | [-2.2493, 0.1221] | [-2.2097, 0.0565] | -1.9024 |
| new_minus_old_control_process_replication_descriptive | OLD500 | slot_f1_exact_f1 | 0.1333 | [-0.8333, 1.1000] | [-0.9018, 1.1651] | 0.1494 |
| new_minus_old_control_process_replication_descriptive | OLD500 | slu_f1_f1 | -0.4136 | [-1.5576, 0.7160] | [-1.5770, 0.7537] | -0.4048 |
| speech_minus_form_twin | DEV1000 | slot_f1_exact_f1 | 2.0324 | [0.6757, 3.4010] | [0.6838, 3.3461] | 1.8853 |
| speech_minus_form_twin | DEV1000 | slu_f1_f1 | 2.9811 | [1.6400, 4.3371] | [1.7628, 4.2034] | 2.8659 |
| speech_minus_form_twin | NEW500 | slot_f1_exact_f1 | 2.2076 | [0.1410, 4.3477] | [0.1609, 4.1130] | 1.4053 |
| speech_minus_form_twin | NEW500 | slu_f1_f1 | 3.6544 | [1.6033, 5.7033] | [1.6853, 5.6432] | 2.8875 |
| speech_minus_form_twin | OLD500 | slot_f1_exact_f1 | 1.8571 | [0.1238, 3.5571] | [-0.2420, 3.9088] | 1.9033 |
| speech_minus_form_twin | OLD500 | slu_f1_f1 | 2.3078 | [0.6228, 4.0253] | [0.3301, 4.2547] | 2.3499 |
| speech_minus_matched_control | DEV1000 | slot_f1_exact_f1 | 4.5724 | [3.2585, 5.9391] | [3.2102, 5.9050] | 4.4890 |
| speech_minus_matched_control | DEV1000 | slu_f1_f1 | 5.7947 | [4.4401, 7.1343] | [4.4780, 7.1084] | 5.7233 |
| speech_minus_matched_control | NEW500 | slot_f1_exact_f1 | 5.2476 | [3.2485, 7.2886] | [3.4225, 7.1012] | 5.4548 |
| speech_minus_matched_control | NEW500 | slu_f1_f1 | 6.6374 | [4.6451, 8.6327] | [4.8439, 8.4428] | 6.5998 |
| speech_minus_matched_control | OLD500 | slot_f1_exact_f1 | 3.8971 | [2.1463, 5.6305] | [1.9263, 5.8378] | 3.9604 |
| speech_minus_matched_control | OLD500 | slu_f1_f1 | 4.9520 | [3.1730, 6.7762] | [3.0009, 6.9162] | 5.0133 |

## Per-scenario primary-population results

Report small strata descriptively; the audio stratum here is a SLURP speech-command scenario, not an environmental-audio carrier.

| Scenario | n | Speech minus control row-SLU (pp) | Speech minus twin row-SLU (pp) |
|---|---:|---:|---:|
| alarm | 30 | 1.2224 | 4.2222 |
| audio | 2 | 0.0000 | 0.0000 |
| calendar | 33 | -7.0617 | -2.8143 |
| cooking | 9 | 22.2222 | 7.5036 |
| datetime | 33 | 23.0463 | 10.5660 |
| email | 33 | -3.6580 | -1.7544 |
| general | 33 | 9.0909 | 2.0202 |
| iot | 33 | 0.7337 | 6.2828 |
| lists | 32 | 3.1250 | 0.0000 |
| music | 23 | 3.2313 | 1.9069 |
| news | 32 | 18.5124 | 15.6818 |
| play | 32 | -3.0244 | -4.7321 |
| qa | 32 | 9.3750 | 6.2500 |
| recommendation | 32 | 4.2438 | 8.9491 |
| social | 33 | 13.9554 | 5.2971 |
| takeaway | 12 | 0.0000 | -16.6667 |
| transport | 33 | 4.6702 | -1.5846 |
| weather | 33 | 19.1112 | 10.8468 |

## Official aggregate micro and operational costs

The following micro values are full DEV-1000 values from the already-completed official evaluator, not NEW500 row means. Summed request latency includes concurrent requests and is not wall time.

| Arm | Official entity micro F1 (%) | Official SLU micro F1 (%) | Calls | Prompt tokens | Output tokens | Sum request latency (s) |
|---|---:|---:|---:|---:|---:|---:|
| control | 32.0435 | 45.1156 | 1000 | 2965694 | 22567 | 1899.187 |
| speech | 36.5217 | 49.9376 | 1000 | 3140548 | 20465 | 2183.920 |
| twin | 34.0475 | 46.6207 | 1000 | 3140548 | 20548 | 2201.676 |

## Delivery, attribution and limits

The raw slot-phase outputs may contain entities only. Parsing raw outputs as complete SLU answers produces different scenario/action tuples on 456 of 1,000 IDs across the three arms. The inherited full-row intent protection must instead use the historical exact predecessor-intent plus slot-entities join. The shared runtime deliberately seals the raw last phase; a joined read-side derivative was not yet recorded. The historical join has now been restored uniformly under `2026-09-10-ku-s3-read-side-delivery-restoration.md` using the tested shared pure implementation. All 1,000 joined intents match the same predecessor in every arm, and every parsed entity sequence remains unchanged. All source hashes remain unchanged. This restores component protection; it is not live full-system evidence.

| Arm | Responses | Length stops | Wire JSON valid | Entities-only wire contract | Delivered parser valid | Missing responses |
|---|---:|---:|---:|---:|---:|---:|
| control | 1000 | 1 | 998 | 499 | 998 | 0 |
| speech | 1000 | 0 | 999 | 723 | 999 | 0 |
| twin | 1000 | 0 | 1000 | 716 | 1000 | 0 |

Preserve the control length stop and malformed outputs in the comparison. Do not rewrite, drop or retry them. Original outputs are retained for every arm.

- OBS: the same prepared DEV-1000 speech packets and frozen decoder input geometry are used. No additional encoder contact occurred during generation.
- ORG: retain original KC-S1b schema examples and the same sealed unprojected intent predecessor.
- SUPPLY: speech-aligned retrieved fillers versus matched form twin isolates the selection contribution; twin versus no retrieval shows that extra typed blocks themselves also contribute. Do not attribute the entire speech-versus-control delta to alignment alone.
- USE: the same shared slot controller consumes the supply. This is a sealed-predecessor component test; live intent-to-slots assembly remains G6.

Full-roster and OLD500 results support the same directional entity conclusion. The old-versus-new control variation remains descriptive process/code replication. No fresh holdout, independent treatment replication, final superiority or generalization is claimed.

## Service accounting

The service receipt includes `--no-mmproj`, only the decoder GGUF, four slots and total context 65,536. The service has been stopped after the completed trio. The monitor observed 3,041.55 seconds: 1,621.46 active and 1,420.09 parked (46.69%). Its sampled request delta of 576 is a lower bound and cannot replace the verified 3,000 model calls. Mean utilization was 46.85%; mean power 52.48 W, peak 98.19 W. Decompose request validation and handoff waiting before claiming an efficiency improvement.

## Source bindings

- Registered analysis: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3-MAX256-RECOVERY-READOUT-V1/paired-contrasts.json`; SHA-256 `451a107150079450a9eaf8983657f2fc1a77e75fb9d6940b9117bf707bae128f`.
- Source/cost bindings: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3-MAX256-RECOVERY-READOUT-V1/source-bindings.json`.
- Raw completion protection diagnostic: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3-MAX256-RECOVERY-READOUT-V1/completion-protection-summary.json`.
- All source bundle and score hashes are retained in the registered analysis product; the report does not replace a source artifact.

## Inherited joined-read protection

The zero-contact restoration is recorded at `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3-READ-DELIVERY-RESTORATION-V1/receipt.json` (SHA-256 `1bfa696c26e6580f12777b66afd6df0815da24321b78e9dde9c946466281ebc4`). The common predecessor has three unparsed rows; its existing empty-label convention is preserved uniformly. Control/speech/twin retain respectively 2/1/0 unparsed arm outputs in the restoration statistics. The shared join adds no entities, model response, scoring run or bootstrap run. Derived read files remain separate from every original manifest.

Root decision: admit the retrieved-filler component under this recovered scope and proceed to G2 technical readiness. Keep live complete-system and inherited replication requirements open.
