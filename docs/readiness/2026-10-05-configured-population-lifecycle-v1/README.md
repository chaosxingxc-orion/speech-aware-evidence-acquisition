# Configuration-driven population lifecycle

The direct owner instruction requires population settings to come from one file
throughout the experiment. The new prospective entry uses
`configs/experiments/slurp-context-template-configured-continuation-v1.json`.
`config-pin.json` identifies its exact bytes. This preparation grants no GPU,
proposer, scoring, recovery or scientific READ admission.

## Single source and derived values

Declare ordered candidate IDs, control IDs and sample IDs for every cohort.
Derive K and N from those lists, and M from the supported node list. Do not
maintain a separately editable K, member count or trajectory total. The file
also declares deterministic sampling, sample slots, queue depth, sequential
execution, proposer settings and per-trajectory contact limits. Model weights,
knowledge, supply bytes, policies, scorer and serving capacity remain pinned by
their existing independent contracts; this config cannot override those gates.

The prepared file preserves the original sixteen candidates as two eight-policy
cohorts with independent seed/A/A controls on the same twenty inputs. It derives
320 candidate trajectories, 80 control trajectories, 400 total trajectories,
5,200 generation contacts and 20,800 FIT endpoint contacts as caps. Every member
has a 260/1,040 cap. These are accounting limits, not completed work or contact
authorizations. K does not specify concurrent GPU groups.

Use the existing shared compiler and runtime. Load the file with
`load_population_config`; obtain stage inputs with `population_stage_spec`.
The command below validates the exact hash and prints all derived stage inputs:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B \
  scripts/checks/experiment_population_config_check.py \
  --repo-root . \
  --config configs/experiments/slurp-context-template-configured-continuation-v1.json \
  --sha256 2382188de80753c13d74afd617bab7fbd784ef3728a1692f03e4d694c43e82fc
```

The checked output is preserved in `derived-stage-specs.json`. Do not edit that
derived file as an independent source of settings.

## Carry the identity through every stage

1. Bind the same `experiment_population` file pin and `population_cohort` to the
   authoring request, protocol, registration and analysis recipe. Put derived
   `population_budget` into the protocol, registration and recipe.
2. Generate candidate/control lists, exact roster, deterministic sampling,
   execution settings and caps from `population_stage_spec`. Build a fresh
   baseline with that binding before forming its policy seed hash. The shared
   policy compiler verifies the file and retains the binding. It does not change
   policy content, templates, knowledge or the scorer to repair a mismatch.
3. Bind the same configuration to the cell, effective runtime configuration and
   every registered generation/FIT plan. Prelaunch compares actual decoding,
   slot/queue/schedule, FIT cap and registered plan caps. The generation config
   hash remains the standard manifest/scoring identity; no second scoring path
   or changed score-job schema is introduced.
4. Keep ordinary exposure registration, actual-request FIT, source/roster checks,
   complete manifests, verified seals, unique official scores and exact root
   READ. Config equality is not a replacement for any of these requirements.
5. Qualified feedback preparation copies the identical configuration bytes into
   the private archive. Actor views, reservations, original response envelopes,
   compiled update records, trial qualification and root reports retain its pin.
   A changed or missing file fails before further proposal reservation.
6. Derive feedback cohorts from the configured lists. Keep returns and comparison
   frontiers within their original batches. Never flatten two cohorts into a
   synthetic single simultaneous rollout group. The learner view stays abstract
   and contains no runtime knowledge, source lists or concrete task answers.

For a configuration change, write a successor file and fresh registration. Do
not rewrite the pinned file in place or add command-line K overrides. Compile
and freeze new identities only after the independent admission requirements
pass. Invalid and no-change proposals remain spent.

## Compatibility and validation limits

Historical no-config protocol readers retain their exact old K4/K16/partition
authorization checks so existing frozen runs and signed evidence keep their
original meaning. They are compatibility readers, not the prospective authoring
or launch interface. New preparation uses the pinned-file interface above.
Disabling the shared policy compiler still returns the historical baseline
unchanged. No active or failed frozen checkout was edited or migrated.

Tests cover K=3, K=8, K=16, asymmetric cohorts, explicit sampling, derived caps,
file mutation, missing stage pins, missing plans, incomplete populations,
archive path confinement, the real shared compiler and abstract feedback.
Synthetic source adapters in unit tests do not prove a real complete-family
READ. The actual config was loaded and checked without model/scorer contacts.
See the [validation receipt](../../receipts/continuation/2026-10-05-configured-population-lifecycle-validation.json) for evidence: 429 primary and 190 additional/updated test invocations pass (overlapping suites); the config and authoring validator have 100% branch-aware coverage, and the shared learning module has 95%. The existing algorithm-label checker still reports two unchanged historical capacity cells with empty operator lists, reproduced on the unchanged primary checkout. The other executed gates pass; results-ledger and handoff checks retain their documented advisory findings. This is not a claim that every repository-wide check is green.

The K8B runtime stopped independently at 2026-10-05T12:28:29Z on unavailable
Windows memory observation. Preserve its frozen checkout, STOP and outputs.
It has not exercised this new configuration interface on GPU. No complete B
feedback or optimizer export is available. Diagnose and record any incident
disposition separately; do not resume a failed one-shot attempt.
