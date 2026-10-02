# Earnings native branch and terminal-custody proof

Recorded by ChatGPT root at 2026-10-02T03:13:30Z.

## Scope and failure

The previous Earnings proof exercised immediate ACCEPT through the shared
native graph. This extension exercises the actual Earnings21/Earnings22
runtime adapters, source-bound speech windows, FlightRuntime dispatch,
OpenJiuwen roles, acquisition policy, delivery normalisers and final
output/trace binding together. It adds no experimental cell or model contact.

A synthetic empty Solver response reproduced a failure before the registered
`deliver-latest-or-abstain` policy could handle it: sealing a phase state
raised `AgentStateArtifact.content must be a non-empty string`. Both Earnings
carriers failed. An empty second Solver revision failed in the same way.

After routing that response through the existing completion-contract refusal
path, two additional integration defects became observable:

1. A rejected completion was absent from the result's contact count, even
   though the core client had recorded the actual request.
2. FlightRuntime's canonical output builder treated every abstention as a
   wire-level finite completion and required `finish_reason`. A seal refusal
   instead has the existing `seal_refusal` record and its own derivation.

## Repair

Count each source-bound completion before interpreting its answer. Keep the
rejected answer outside pending/completed delivery state. Record an empty or
whitespace-only Solver stop response as a named completion-contract refusal.
The existing policy then retains an earlier eligible Solver draft or abstains;
the strict policy still raises. For an empty non-stop response, retain its raw
hash and an explicit absence state so the existing wire-level disposition runs.

Canonical delivery now uses `native_seal_refusal_abstention_records` for seal
refusals, matching the runner's existing derivation. Other abstentions retain
their previous derivation. No scorer, answer authority, data permission,
action budget, retrieval policy or output reserve changes.

## Offline evidence

The new test exercises nine paths for each Earnings carrier, with two
independent source-bound windows per path:

- immediate ACCEPT;
- REVISE then ACCEPT;
- model-requested acquisition with a relevant return, then a Solver revision;
- model-requested acquisition with an empty return, then a Solver revision;
- revision-budget exhaustion and delivery of the latest eligible Solver;
- empty first Solver response and abstention;
- empty revised Solver response and retention of the earlier Solver;
- whitespace-only Solver response and abstention;
- empty length-terminated Solver response and finite-completion abstention.

Two additional cases assert that strict configurations still refuse the empty
Solver. The 20 tests cover 36 completed synthetic window trajectories plus
the two expected strict refusals. They verify per-window history isolation,
acquisition-to-Solver material flow, final answer authority, actual contact
counts, normaliser carrier identity and stitched output/trace verification.
The actual model request gate is substituted by a local recorder: this is
not tokenizer capacity evidence or a registered four-row GPU proof.

Dataset loading, prepared knowledge and speech/model bytes are synthetic.
The runtime adapter itself is real; its raw dataset loader is tested separately
and replaced by a synthetic split in this integration proof. E22 receives no
ConEC source or data allowance. There is no acoustic, scientific or transfer
effectiveness claim.

Validation:

- 359 execution, adapter, finite-completion and flight tests passed.
- 131 source-custody, system-feedback, reference-isolation and scope tests passed.
- All 18 changed executable source lines were covered by the focused proof.
  This is changed-line coverage, not whole-module or repository coverage.
- Engineering-base, native-framework-reuse and finite-completion checks passed.
- Changed-file Ruff and Git whitespace checks passed.

The first coverage command used file paths where the tool required module
names and collected no coverage. The corrected module-scoped measurement
produced the stated changed-line coverage. An attempted derived-media check
stopped at its invocation prerequisite; no real data was read. Its relevant
synthetic confinement tests are included in the 131-test group.

## Frozen experiment and next work

The active SLURP update1 worker remains
`/home/chao/saea-worktrees/codex-system-text-update1-flight-v1` at
`2f07dd3d6f52eee79d24243c40a0dff195260816`. None of its files, requests,
manifests, queue controls or policy versions was changed. This repair is
prospective engineering, not an authorization to retry or rewrite any result.
Any later campaign must bind its actual runtime revision and pass its own
admission; never insert a changed executor into an in-flight family.

Update1 still requires all five members to finalize and score before its exact
READ gate. The next learning proposal must receive only its admitted branch
feedback; the blind proposer stays isolated. No quality result was read here.

Cross-carrier task adapters, native window paths and common native-count
feedback plumbing exist. The new system-text search remains SLURP-registered;
its slot-specific editable bundle, source identities and metric rules must not
be relabeled as an admitted Audio2Tool or Earnings search. Those carriers still
need their own exact knowledge/data binding, measured capacity, same-chain A/A,
metric protocol and sequencing before GPU execution. Existing holds remain.
