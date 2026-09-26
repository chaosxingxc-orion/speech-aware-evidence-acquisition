# SLURP complete-system semantic-update preparation and prospective protocol

## Verified assets and limits

The model-free preparation registered in
[the preparation receipt](2026-09-26-slurp-system-round-assets-registration-v1.json)
is complete. The [asset audit](../receipts/continuation/2026-09-26-slurp-system-round-assets-audit-v1.json)
binds every source file and uses the existing released-knowledge and speech
feature loaders. It is not GPU or generation authority.

| Existing TRAIN cohort | Samples | Original audio seconds | Verified feature packets |
| --- | ---: | ---: | ---: |
| R01C | 625 | 2726.8471875 | 625 |
| Fold A v2 | 1080 | 3084.5284375 | 1080 |
| Fold B v2 | 1080 | 3154.797375 | 1080 |

All 2785 packet manifests, feature bytes and position bytes passed the production
loader. Packet audio hashes match the sealed full-utterance query vectors.
The existing R01C/A content vectors and the newly derived B content vectors
equal their parent vectors exactly. The B derivative uses the existing
build_slurp_query_content_derivative.py; it performs no encoding or model call.

Use the R01C PLAN knowledge binding as the common store set across rounds:

| Store | Values | Source sample IDs | Overlap with each of R01C, A and B |
| --- | ---: | ---: | --- |
| intent-boundaries-v1 | 60 | 2037 | Zero samples and utterances |
| slot-contracts-v2 | 54 | 3162 | Zero samples and utterances |
| annotated exemplars minus R01 | 8554 | 34474 | Zero samples and utterances |

The audit checks snapshot, facet and value source scopes separately. Each
release's source and snapshot bindings are verified through the shared loader.
All three cohorts are also mutually disjoint by sample and utterance.
This verifies declared source provenance, not the absence of every possible
form of historical model or researcher exposure. These are exposed TRAIN lists.

The old Fold A PLAN used the original exemplar pool; the common minus-R01
pool is a changed knowledge input there. Do not compare a new learned policy
against only the historical Fold A score and attribute the difference to
memory. Match the common knowledge in all new evaluation controls.

The check configuration is
configs/analysis/slurp-system-update-round-assets-v1.json.
It is deliberately an asset specification, not an executable experiment cell.
To re-audit without changing historical receipts, run in WSL:

```sh
/home/chao/.venvs/speechrl/bin/python -B scripts/audit_slurp_system_round_assets.py \
  --config configs/analysis/slurp-system-update-round-assets-v1.json \
  --data-root "$SPEECHRL_DATA_DIR" --output /absolute/new-audit.json --workers 8
```

Use an unused output path. The audited feature count does not replace final
runtime/dataset-view binding or real request capacity checks.

Validation: 27 existing derivative/store tests and three populated/empty-memory
runtime tests passed, with Ruff and all nine offline gates. See the
[validation receipt](../receipts/continuation/2026-09-26-slurp-system-round-assets-validation-v1.json)
for exact sources, checks, substituted boundaries and historical warnings.

## Complete-system sampling proposal

The existing model fragment uses temperature 0, seed 20260913 and max_tokens
512. Repeating it measures execution variation; it does not establish a
registered stochastic trajectory sampler. Keep that greedy decoding as the
evaluation setting.

The proposed construction default is four complete trajectories per input,
temperature 0.7, with replica seeds 2026092601 through 2026092604. Apply the
construction decoding to all four model roles. Keep one Solver answer per
visit and the existing bounded review/revision graph; do not use the old
Solver-only samples=5 mechanism. Every replica must independently execute
Perception, Solver, Reviewer, Planner, any revision and final delivery.

These are prospective repository hyperparameters, not claims about optimal
settings or exact upstream defaults. Freeze the full effective decoding
configuration, including server defaults that could affect sampling, before
contact. Keep the policy and memory fixed for a whole construction round.
Do not change temperature, group size or seeds after viewing that round's
outcomes to obtain more favorable disagreement. If no eligible terminal
feedback groups exist, retain that result rather than silently resampling.

A pinned seed is reproducibility metadata, not a measured action probability
or a guarantee of independent trajectories. Do not describe the semantic
update as an importance-weighted policy-gradient estimator. The registered
membership check introduced by the
[round contract](2026-09-26-system-update-round-runtime.md)
must be paired with a prospective common-policy audit, not a post-hoc assertion
that any four configurations are samples of one policy.

## Rounds and evaluation arms

Use R01C for the first round, producing M1. The initial system has the locked
complete graph and no learned experience. After the full round and official
scores seal, execute the already implemented summary, feedback comparison,
group update and batch synthesis stages.

Use Fold A for the second round with the full ordered M1 pool frozen for
every replica. M1 is exposed through the registered memory tool; final answer
authority remains with Solver. The updater produces M2 only after the round
seals. Its cumulative exposure is R01C union A. The addition of the memory
tool after the initial no-memory round is a declared system-policy change,
not a hidden claim that every round has identical actions.

Freeze M1 and M2 before evaluating Fold B. The proposed arms are:

| Arm | Purpose |
| --- | --- |
| D: matched locked default | Measure complete-system benefit against the qualified default, using common knowledge |
| E: empty-memory tool control | Same memory-aware prompt, tool schema, role budget and delivery as M2, with an explicitly empty ordered memory selection |
| M1: one-round memory | Measure the one-update policy on the same population as M2 |
| M2: two-round memory | Primary learned policy, chosen prospectively rather than after seeing B scores |

E can use the same source-attested candidate artifact and cumulative
construction receipt as M2, while an independently pinned evaluation decision
selects zero records. It cannot use an arbitrary fabricated memory file.
The production reader already permits this empty selection, and the connected
synthetic native test verifies that the tool returns no guidance through the
real shared runtime. It does not bypass source attestation.

Use identical greedy decoding, source knowledge, roster, tool budget and
delivery rules for E, M1 and M2. D retains the locked tool-free interface and
therefore measures the aggregate system change. M2 versus E isolates the
availability of learned guidance given the same tool interface; it does not
establish causal credit for an individual rule or role.

Current VAR-1 evidence does not qualify K10, K30 or EX-DIV as a stronger fixed
policy than the locked default. Do not add a duplicate arm merely named
"strongest fixed." If a distinct qualified fixed complete policy exists at
registration, identify it with its verdict and include it prospectively.
Keep the closed VAR-2/F10/delta/candidate-recovery lines closed.

The primary policy remains M2. Require full-task benefit against D and E,
with the registered intent protection and all harm accounting. Compare M2
versus M1 as the incremental-update question on the same B population, not
by comparing the different construction cohorts' scores. Do not switch the
primary policy to M1 after seeing a failed M2 comparison.

Replicate the qualifying M2/D/E comparison on the same B roster before
claiming stable execution gains. Preserve balanced registered arm ordering
across initial and repeat campaigns, all rows, the official pooled SLU-F1,
natural/equal-stratum estimates and paired utterance-cluster uncertainty.
Freeze exact statistical thresholds and the joint decision rule in the
generation registration. Neither construction fit nor exposed-list replication
is evidence of fresh-data generalization.

## Structural workload before final registration

The unchanged bounded graph allows at most 11 model contacts per input.
Four replicas on R01C and A total 6820 complete episodes, at most 75020
actor contacts. Four B evaluation arms total 4320 episodes, at most 47520
contacts. The conditional three-arm matched replication totals 3240 episodes,
at most 35640 contacts.

A conservative semantic-stage count is at most four summaries plus one
comparison and one group update per construction input, plus one batch
synthesis per round: at most 10232 additional generation contacts.
This gives 168412 structural generation contacts across the full proposed
sequence including the conditional replication. These are ceilings, not
targets or approved budgets. They exclude separately registered smoke,
tokenizer/fit endpoints and any explicitly approved recovery. No automatic
retry or second recovery is implied.

No benefit is assumed. Ineligible groups can reduce semantic-stage contacts,
but retain their population and exposure. If a full batch or memory pool does
not fit, stop before generation and register an explicit adaptation. Do not
select convenient groups or truncate records to make this proposal fit.
Semantic-stage output limits, actual capacity, cumulative audio exposure,
GPU-time caps, concrete run IDs, scoring jobs and effective configuration
hashes still require final registration. The proposed actor/evaluation manifests
each receive one official full score; summary/update artifacts receive none.

## Next executable boundary

The reuse and exclusion questions are now answered with source-bound evidence.
Next derive the shared actor/sampling configurations and E/M1/M2 evaluation
templates, verify actual effective requests with synthetic transport, and
freeze the prospective policy contract and full plans. Do not create a new
execution framework.

Resolve the CUDA/host failure before any new GPU admission. The earlier
candidate recovery is closed and its isolated control quality remains unread.
No service, queue, STOP, frozen worker, historical roster or historical
preparation output was changed by this preparation.
