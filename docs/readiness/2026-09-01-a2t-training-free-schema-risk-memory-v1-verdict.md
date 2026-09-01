# Audio2Tool training-free schema-risk memory v1 — live state, no safe utility signal

Date: 2026-09-01. Status: **MODEL-FREE SCREEN FAILED; DO NOT SCALE**.
Experiment: `SAEA-A2T-MF-TFRL-SCHEMA-RISK-MEMORY-V1`. Committed artifacts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-schema-risk-memory/policy-v1.json`
and `result-summary.json` in the same directory.

## Verdict

Registry-aware schema risk does not safely identify when the existing evidence-supply action helps.
Promotion failed, no candidate was selected, and both registered training-free policies returned
frozen M0 for all 104 samples. The method therefore produces zero gain and cannot expand to a
fresh approximately-100-sample support flight or an approximately-1,000-sample experiment.

This result establishes neither agent-over-single-call superiority nor a positive training-free RL
contribution. It closes schema-risk targeting for `SUPPLY_UNION_STRIPPED` on these returns. The
next design must change information acquisition or evidence generation; it cannot tune another
schema category or relax the frozen support, save, harm, or promotion thresholds.

## What the screen learned

The parser resolved all 152 deployment registry signatures, covering 179 parameters, including 18
optional parameters. It classified 80 explicit enum constraints and 33 numeric ranges; one compound
constraint was correctly left uncheckable rather than guessed. The state channel was live: M0 had
seven risk classes, the re-observation had six, and the pair relation split into 75 exact, three
M0-lower, three observation-lower, and 23 unresolved rows.

The live state did not separate utility. The largest detailed clean/clean/exact cell contained 61
available returns with three saves and seven harms. The only notable harm-free positive cell had
support seven but only one save, below the preregistered minimum of two. No supported cell had at
least two saves and zero harms.

## Training-free control result

Both `schema-risk-coarse-v1` and `schema-risk-detailed-v1` chose `STOP_M0` on 104 of 104 samples.
Each produced zero supplies, zero saves, zero harms, zero exact-match gain, zero tool-accuracy gain,
five fold gains of zero, and grouped CI90 `[0.0, 0.0]`. State-liveness, harm-avoidance,
harm-maximum, every-fold-nonnegative, and tool-nondegradation gates passed. Both-actions,
supply-range, saved-minimum, net-gain, positive-CI, positive-fold-count, and save-retention gates
failed. The safe all-stop result is correct behavior for the frozen controller, but it is not an
agent improvement.

## Integrity and scope

The one-shot reader ran from clean study commit
`4d6932a459c15c5afdd2ac440dd71e99642997fc`. It reproduced the predecessor's 104 samples, 92
available supplies, four always-supply saves, ten always-supply harms, fold identity, and decision
identity before forming schema state. The external result is 19,602 bytes with SHA-256
`be88b018c11183173bd3cb22cb132b03c9d09fbb17dfeab6c54ce0e5f582120a`, internal self-hash
`7837e9e0a821af5809cfa96e0eefbb8caf7ceb3dcafb52988f7149c26fa4960b`, and policy self-hash
`85872638953f31fe16f24687017997f2aa5d1ac3980fbd1b0427f7cc09214b26`.

The offline guard recorded zero outbound attempts and zero frozen-core, embedding, tokenizer,
HTTP, socket, audio, or GPU contact. No remaining exposed-296 sample, unexposed Audio2Tool sample,
G2, FINAL60, test annotation, future turn, Stage-3, or paper-scale surface was opened. The baseline,
model, registry, prompts, scorer, and prior prediction bytes are unchanged.
