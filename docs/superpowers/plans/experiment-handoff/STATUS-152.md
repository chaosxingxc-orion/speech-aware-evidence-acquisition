# STATUS-152: registered typed-context comparison launched

Date: 2026-09-16. Root owns analysis, decisions and serving.
Supersedes STATUS-151 for execution state.

## Running campaign

Root launched PID 404247 at 2026-09-16T09:39:37.159225+00:00.
Unified execution wrapper session is 35269; do not read its raw campaign log.
Frozen checkout: /home/chao/saea-worktrees/slurp-typed-context-registration-v1.
Frozen commit: bae1e743e66c0ee8189851bb1ec35ddc37ab2c49. Source freeze contains 5827 tracked files.
Freeze SHA256: a44e364cac741ccbb5c04479b894f7aa1d720ff019402b82faafae4e06eb2f93.
Canonical registration commit: cf3433d457327ff740b6b9d528791cc5c5287f80.

Service remains serving-slurp-native-candidate-five-train-a-np4-v1,
PID364846, monitor364981. It is healthy and its full identity was verified;
four decoder-only 24576-token slots,98304 total,max512,prepared speech,no mmproj.
No service reload was needed. Reuse receipt SHA256:
b74fe90a6b62e4a6b1cd4234b72502f97ca4e7e1207c421c079483fc7afbabf7.

Run order:
1. SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-V1,
   attempt-slurp-direct-max512-train-fold-a-generation-v1.
2. SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-V1,
   attempt-slurp-native-typed-role-context-train-fold-a-generation-v1.

The campaign acquires one exclusive generation lease at a time. Direct's existing
whole-roster gate fits1080 exact requests using3241 registered endpoints before
generation; system fits each realized immutable native request. Do not run a second
static fit. First official direct scoring can overlap system generation.
Both configurations are frozen before either outcome is read.

## Registration and checks

Authoritative protocol:
docs/readiness/2026-09-16-slurp-typed-role-context-system-vs-direct-train-fold-a-v1/protocol-registered-v2.json.
The four *-plan-registered-v2.json plans and four active exposure rows bind it.
Earlier unexecuted registrationv1 is preserved. Its preparation-only cache did not
match the contact-bearing config identity; one model-free rebuild preserved byte-equal
K8 output, then final config warm validation passed. This was before all contact,
not an experiment recovery or extra generation authorization.

Direct ceilings:1080 generations,3241 FIT endpoints,3085 speech seconds,3 fit-inclusive
GPU hours,one complete official score. System:11880 generations,47520 FIT endpoints,
4320 analytical tools,33930 repeated speech seconds,12 fit-inclusive GPU hours,one
complete score. These are refusal bounds,not targets. Zero ASR/encoding/paid API.
Generation and FIT are within the same arm window; do not double-count their hour caps.

Root verified both complete1080 preflights, exact registered ExecutionPlans and both
generation/FIT exposure gates, source cleanliness, prepared-cache identity and complete
resident identity. Existing implementation suites passed163 typed-context tests and86
registration/config/campaign tests; engineering-base and diff checks passed.
There is no new real-model task-quality result yet.

## Observation and next action

One-job observer /root/a2t_contrast_value_sol checks metadata no more than once per60s,
keeps unchanged states quiet, and reports startup/terminal transitions only.
No raw prompts,outputs,score values or Fold B are allowed.
Mechanical postseal-template preparation is assigned to /root/slurp_stage_attribution_sol.

On failure preserve the exact attempt,contacts and service; root diagnoses before any
separately registered recovery. No automatic replay/restart.
On success verify both finalized full1080 bundles and first saved scores,write root paired
quality release,then root interprets official primary and diagnostics.
Primary is pooled official SLU,system minus direct,10000 speaker draws,seed20260915,
CI95 lower bound>0 with positive point gain. Report all18 strata/equal weighting,
common-correct-intent slot quality,system candidate coverage,review saves/harms,
evidence availability versus actual use,and full costs. Never invent direct candidate coverage.
A first positive new pair needs a fresh same-roster replication.

A1 is NOT_ADVANCED and closed; report docs/results/2026-09-16-slurp-candidate-five-train-a.md.
Keep max3. This package tests typed context plus structured evidence-directed review,
target-knowledge access and reserved reporting; it is not an isolated compiler ablation.
Keep no-example contract,history-only,largerN,new knowledge and acoustic tools separate.
Historical useful DEV replications remain valid within their stated scope.
SLURP only; E21/Audio2Tool held. No training-free RL claim.
Preserve canonical untracked integration_native_finite.py and wsl$/.
