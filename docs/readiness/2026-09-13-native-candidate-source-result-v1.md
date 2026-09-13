# Native candidate source pair: root result and closure

Both DEV1000 source flights are finalized and were scored once on their complete manifests. The registered implementation is not promoted as an effective agentic baseline. The primary NEW500 official SLU micro F1 decreased, and only one requested candidate lookup returned knowledge. This result does not test the promised full-roster Top-N commitment mechanism.

## Evidence and analysis

Generation used frozen commit 49c30968db4580b7a3377ff0b5fcbe66c64e1f97 and one resident Qwen3-Omni Q4_K_M decoder-only service: c65536, four slots, prepared speech packets, no mmproj, maximum 256 output tokens. DIRECT and LOOKUP used the shared controller, FlightRuntime and OpenJiuwen executor. All populations were historically exposed discovery data; NEW500 is a name, not an untouched-data claim.

The analysis was released only after both final bundles and their first attached official scores were verified. It reuses the registered recipe and saved per-sample statistics without invoking a scorer. The primary confidence interval uses 10,000 paired speaker-cluster bootstrap draws. Scenario-stratified resampling remains sensitivity analysis. Micro F1 pools the six word/character TP/FP/FN counts; row-mean F1 is a different estimand.

| Population | Direct SLU micro F1 (%) | Lookup SLU micro F1 (%) | Natural delta (pp) | Speaker CI90 (pp) | Equal-scenario delta (pp) |
| --- | ---: | ---: | ---: | --- | ---: |
| NEW500 | 37.0472 | 33.1696 | -3.8776 | [-6.0900, -1.6549] | -3.9404 |
| OLD500 | 35.4624 | 32.7191 | -2.7433 | [-5.3076, -0.3317] | -1.2536 |
| DEV1000 | 36.2692 | 32.9437 | -3.3255 | [-5.0438, -1.5980] | -2.2365 |

## Primary population secondary metrics

| NEW500 metric | Direct (%) | Lookup (%) | Natural delta (pp) | Speaker CI90 (pp) | Equal-scenario delta (pp) |
| --- | ---: | ---: | ---: | --- | ---: |
| Intent accuracy | 73.2000 | 73.4000 | +0.2000 | [-1.7622, +2.0284] | +0.1252 |
| Scenario accuracy | 80.8000 | 80.4000 | -0.4000 | [-2.3504, +1.5351] | -0.9241 |
| Action accuracy | 75.6000 | 75.2000 | -0.4000 | [-2.3891, +1.4468] | -0.2335 |
| Mean per-sample exact slot F1 | 14.7505 | 11.2781 | -3.4724 | [-4.9350, -2.1075] | -3.6128 |
| Mean per-sample SLU F1 | 20.4590 | 16.2100 | -4.2490 | [-5.8454, -2.7060] | -4.3891 |

The one-sided 95% lower endpoint is the CI90 lower endpoint from the same bootstrap draws. No historical null margin, non-inferiority gate or effectiveness threshold was borrowed for this new comparison. The positive intent point estimate is inconclusive.

## Primary population per-scenario results

| Scenario | n | Direct intent (%) | Lookup intent (%) | Direct SLU micro (%) | Lookup SLU micro (%) | Micro delta (pp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 30 | 86.67 | 90.00 | 32.68 | 35.80 | +3.12 |
| audio | 2 | 100.00 | 100.00 | 0.00 | 0.00 | +0.00 |
| calendar | 33 | 60.61 | 60.61 | 33.33 | 31.86 | -1.47 |
| cooking | 9 | 55.56 | 66.67 | 58.67 | 50.16 | -8.51 |
| datetime | 33 | 84.85 | 81.82 | 29.94 | 19.49 | -10.45 |
| email | 33 | 87.88 | 87.88 | 25.00 | 16.67 | -8.33 |
| general | 33 | 36.36 | 36.36 | 8.78 | 9.18 | +0.40 |
| iot | 33 | 87.88 | 90.91 | 59.03 | 47.40 | -11.63 |
| lists | 32 | 84.38 | 81.25 | 42.06 | 38.24 | -3.81 |
| music | 23 | 65.22 | 52.17 | 33.21 | 28.67 | -4.54 |
| news | 32 | 81.25 | 75.00 | 41.43 | 39.23 | -2.20 |
| play | 32 | 18.75 | 31.25 | 48.09 | 53.66 | +5.56 |
| qa | 32 | 68.75 | 75.00 | 59.01 | 59.27 | +0.26 |
| recommendation | 32 | 71.88 | 65.62 | 63.99 | 46.86 | -17.13 |
| social | 33 | 78.79 | 81.82 | 16.04 | 3.83 | -12.21 |
| takeaway | 12 | 91.67 | 83.33 | 36.57 | 34.35 | -2.22 |
| transport | 33 | 84.85 | 87.88 | 27.77 | 27.00 | -0.77 |
| weather | 33 | 93.94 | 93.94 | 18.93 | 21.93 | +3.00 |

The hash-pinned paired contrast artifact includes every metric and per-scenario result for OLD500 and DEV1000 as well. Small individual strata are descriptive and were not used to select a new roster or threshold.

## Mechanism and interface diagnosis

- DIRECT used 1,000 generation contacts. LOOKUP used 1,042: 958 early-direct paths and 42 two-contact paths.
- Only one candidate lookup succeeded. Forty calls contained unknown legal IDs and one contained a duplicate ID. The 41 rejected paths received typed tool-error feedback and zero candidate-contract knowledge.
- The displayed inventory used scenario: action. The decision instruction requested legal intent IDs without defining scenario_action. The tool schema accepted unrestricted nonempty strings, while the provider required exact canonical IDs. This mismatch is a system interface defect.
- Across 106 attempted ID occurrences, 57 used a colon, 13 a colon plus space, 21 a hyphen, three were exact canonical IDs, six were nonexistent labels and six were source identifiers. These counts characterize arguments, not independent examples.
- Raw string comparison reported 40 first-candidate changes and 40 outside-shortlist final labels. Diagnostic-only separator interpretation yields 38 calls with a legal candidate, 10 semantic first-candidate changes and one outside that interpretable shortlist; four calls have no interpretable legal candidate. No normalized ID was fed back into runtime or official scoring.
- The model-selected 42 attempted paths had nine descriptive intent rescues and no harms relative to DIRECT. All nine occurred after rejected calls. This is neither randomized nor powered subset evidence and cannot be credited to knowledge consumption.

OBS retained the same source speech packets. ORG prepared one compact TRAIN catalog. SUPPLY returned that catalog in one valid call; error messages are not catalog evidence. USE includes early answers and second-contact answers after errors. The source pair changes the native tool invitation and possible extra contact together, so it cannot isolate knowledge, deliberation or delayed commitment.

## Resource receipt

DIRECT consumed 2,884.7936875 request-audio seconds; LOOKUP consumed 3,032.2040625. They used 3,001 and 3,128 actual fit endpoints respectively, with zero generated fit tokens. No ASR or encoder ran. The minimum recorded fit margins were 13,721 direct, 13,337 lookup-first and 12,804 lookup-final tokens.

The monitor audit measured generation-window GPU utilization integrals of 0.0638282892 and 0.0786238479 hours, with gap-aware bounds [0.0638282892, 0.0687562734] and [0.0786238479, 0.0806392782]. These are not full-flight or fit-inclusive GPU totals. Exact fit timing and its GPU integral are unavailable in that audit.

The observed generation handoff gap was 97.225121 seconds, exceeding the one-minute target. DIRECT scoring completed 37.681239 seconds before LOOKUP generation began: this pair did not realize scoring/generation overlap. Preserve these observations rather than claiming full utilization or ideal pipelining.

## Root disposition

Close the native source pair with its original outputs, scores and failure evidence intact. Do not silently repair its IDs or retry the same experiment after quality inspection. Correct the ID contract prospectively and prepare the distinct common-first-pass commitment comparison. Require full candidate coverage, registered delivery authority and a real request proof before generating that comparison. Component experiments do not substitute for autonomous tool selection or a complete system trajectory.

## Artifact bindings

- Root verdict: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/root-verdict-v1.json; SHA-256 3b5641902ca8c1d487a9b31b5f381ffc457725b6402b41ebf500080a29eddddc.
- candidate-source-paired-contrasts.json: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/candidate-source-paired-contrasts.json; SHA-256 0638897b78d9ba10fdce95f2455d435afbf0403675386eb9ea6bc453a5bd252b.
- sealed-lookup-trace-diagnostics-v2.json: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/sealed-lookup-trace-diagnostics-v2.json; SHA-256 3b5fa1dc5b44aa453f0332b90ba0870d251e7de89971f32fb56245f5613bbec1.
- sealed-lookup-id-interface-diagnostics-v1.json: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/sealed-lookup-id-interface-diagnostics-v1.json; SHA-256 a8d9651408c1b2ec32c1bd6eefe14fcb53bbf79c6458a9952d1016f12785ed5f.
- source-pair-timing-cost-audit-v1.json: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/source-pair-timing-cost-audit-v1.json; SHA-256 90395443c87197f06add287d547cb6c1c4f2e350586bea5f3a19de9cd15ca43b.
- comparison-exit-v1.json: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NATIVE-CANDIDATE-SOURCE-PAIRED-ANALYSIS-V1/comparison-exit-v1.json; SHA-256 bd9b5ab01cf3d3513bc03482352613575cb3045c5348185d71dc91c9a0d8c4ad.
