# Joint role imports: source engineering contract

This optional owner227 path implements the held decision in
`docs/readiness/2026-10-09-slurp-local-to-joint-n100-v1/root-decision-v1.json`, raw
SHA256 `68f4ab8ce4d71e8731f743e357738786fc78fb086022a135245cbcf413dd3d51`.
It grants no policy activation, contacts, registration, READ, adoption or merge.
The actual contract is the original fixed development N100. Synthetic N5 cases
exercise configuration arithmetic only and cannot substitute for that raw pin.

## Exact imports and original custody

Use `import_exact_role_texts` in the existing `rails.system_text_policy` module.
Read the selected member's mask from the pinned decision's `ordered_members`:
controls retain the exact original seed bundle; each candidate copies only its
declared Solver and/or Reviewer text. This is the joint role import declaration,
not another proposal round or a new optimizer protocol. A minimal pure call is:

```python
member = next(row for row in decision["ordered_members"] if row["id"] == member_id)
bundle = (import_exact_role_texts(seed, donors, roles=member["imports"],
          decision=decision, selection_sources=basis["root_selection_sources"])
          if member["imports"] else seed)
compiled = compile_system_text_policy(source_baseline, bundle,
    repo_root=repo_root, output_root=new_staging_root, data_root=data_root)
```

The compiler and `SystemSearchArchive` remain the canonical materializer and
archive. Both actual donor ancestries remain direct parents for every candidate,
including a single-role import. Every nonimported seed field remains exact,
including `context_layout`, `node_context`, optimizer experience, construction,
knowledge and supply. Original donors must retain their full-seed parent and
must change no other role. The cumulative union rejects conflicting kind/hash
identities and retains all root-visible selection exposure. Controls stay
byte-identical to the seed; the family basis records their selection context.
Print only source kind/hash/count summaries, never the full example lists.

A repository-relative raw-pinned `joint_role_basis` document has exactly:

```json
{
  "schema": "saea-joint-role-import-n100-basis-v1",
  "root_decision": {"relpath": "<original root decision>", "sha256": "<original raw hash>"},
  "source_population": {"relpath": "<original N100 population>", "sha256": "<original raw hash>"},
  "source_preparation_receipt": {"relpath": "<original final full-seed receipt>", "sha256": "<original raw hash>"},
  "donor_preparation_receipts": {
    "solver": {"relpath": "<original Solver receipt>", "sha256": "<original raw hash>"},
    "reviewer": {"relpath": "<original Reviewer receipt>", "sha256": "<original raw hash>"}
  },
  "root_selection_sources": [
    {"kind": "selection", "sha256": "<root decision raw hash>", "sample_ids": ["<complete original cohort, in order>"]},
    {"kind": "selection", "sha256": "<each original full-family root evidence raw hash>", "sample_ids": ["<complete original cohort, in order>"]}
  ]
}
```

The implementation anchors the original pins, complete cohort, five ordered
members, three import candidates, two controls, sampling and geometry to the
existing decision/population. Root evidence is checked as raw bytes without
parsing quality. Original canonical policy archives recursively verify every
ancestor. Original full400 supply and its selected N100 output remain raw-pinned
and equal; fresh preparation reuses the exact output through the existing
model-free preparation path. No original receipt or supply is rewritten.

## Separate preparation and stage admission

Use the existing preparation CLI with a root-authored unsigned input whose
schema is `saea-joint-role-import-preparation-input-v1`. Its existing fields are
`source_preparation_commit`, `package_relpath`, `experiment_population`,
`population_cohort`, `runtime_root`, `datasets_lock_path`, `member_specs`, plus
the raw-pinned `joint_role_basis`. Omit `local_node_basis` and `target_role`.
Each configured member spec contains exactly `identity`, `policy_binding`, and
`companions`; reuse the local path's complete `capacity`, `graph`, `natural`
companion shape. Give every member/stage a fresh experiment/cell/run/attempt
identity and every natural companion a separate fresh actual-request FIT pair.
Original seed/donor spend and all generation/proof identities are excluded.

```text
PYTHONDONTWRITEBYTECODE=1 /home/chao/.venvs/speechrl/bin/python -B \
  scripts/preparation/prepare_manual_audio_recovery.py \
  --input <new root-owned input.json> --input-sha256 <raw SHA256> \
  --repo-root <reviewed checkout> --data-root <DATA>
```

Root alone may use this CLI after exact source approval. It remains held,
model-free and network-refusing and writes only new prospective artifacts. It
produces the complete generation identity map and separate capacity/natural
proof identity maps. Proof maps use schema
`saea-joint-role-import-proof-identity-map-v1` with exact fields `stage`,
`experiment_population`, `joint_role_basis`, `generation_identity_map`,
`proof_roster`, `members`. The proof roster is the independently raw-pinned
original graph4 dataset (`fe35d4a89f4ddac7c4a3f4b32da1ed244f9c1f1d422d56098d6118085190d80d`),
not an arbitrary subset of N100. Every ordered member, including control/A/A,
must retain its same policy, import mask and N100 parent binding.
Those preparation maps bind held compositions. Moving readiness to ready changes
composed hashes. Preserve the original held maps/receipts; project the complete
final-ready family, author a fresh raw-pinned stage map with its final hashes,
and bind the root decision/disposition to that map before countersigning plans.
An old held map copied into registration is refused. Do not create a circular
hash by putting plan hashes inside the final-ready configuration.

Each stage needs its own existing countersigned plans and DATA campaign decision.
There is no `JOINT` analysis selector. The current
`scripts/analysis/author_manual_architecture_package.py` authorer and
`analysis.system_architecture_read` qualifier use `manual-architecture-n20-v1`
plus the exact optional basis. Capacity uses
`rails.experiment_population.require_architecture_capacity_registration`;
natural uses `rails.architecture_natural_registration.require_architecture_natural_registration`
with its original `natural-four-row-v1` plan role. The existing capacity family
qualifier and original structural custody validator remain authoritative.
Historical DATA/temporary launch and authoring convenience wrappers that require
`target_role`, `local_node_basis`, or `local-solver-panel-v1`/`local-reviewer-panel-v1`
do not accept joint inputs and must not be invoked with them. This slice adds no
joint dispatch wrapper. Root must use the canonical generic registration/qualifier
interfaces with a separately reviewed exact stage launch packet; source approval
alone is not that packet or dispatch authority.
In particular, the preserved DATA
`coordination/local-reviewer-n100-k4-update2-capacity-v1/n100_capacity_helpers_v1.py`
`register()` emits no `joint_role_basis`/`joint_proof_identity_map`; the old local
bridge additionally requires `target_role`. They are not turnkey joint stage
registration paths. A separate narrowly reviewed metadata adapter or explicit
canonical root plan authoring must close that seam before any actual joint
capacity admission. Preserve those historical bytes and reuse their canonical
qualifier; do not relax the new gate to make their old plans pass.
Plans preserve `joint_role_basis`; capacity/natural plans also pin
`joint_proof_identity_map`. The separately decided full stage eligibility must
match all configured identities. Its `adaptive_joint_roster_reuse` contains
exactly schema `saea-owner227-adaptive-joint-roster-reuse-v1`, `root_decision`,
`joint_role_basis`, `stage`, scope `adaptive-development-discovery-only`, false
`claims_benefit`, `independent_validation`, `runtime_adoption`, `learner_export`,
complete ordered `members`, and the exact `cumulative_sources` union. Each row
binds `member_id`, `cell_id`, `run_id`, `attempt_id`, `config_hash`, `tuning_roster`,
`read_roster`, and complete actual `intersection_sample_ids`. Preserve overlaps
for structural stages as well. Existing owner/exposure/runtime gates still run.

Only after full canonical stage validation does the flight gate retain an
authenticated overlap as an explicit advisory. Missing or invalid declarations
remain blocking. Held-out, confirmatory, benefit and learner-export refusals,
and every legacy branch, remain unchanged. N100 admission independently joins
the completed natural qualification to its original separate complete proof map
and the exact N100 parent identity map. No historical-source compatibility alias
is accepted for this path.

## Serial root checklist and analysis boundary

1. Verify exact reviewed source, root decision and all original pins; materialize
   only the declared role imports through the existing compiler/archive.
2. Author the complete population and basis with original roster/ancestry; prepare
   only fresh held generation/capacity/graph/natural configurations.
3. Root separately registers, admits and completes the whole capacity family and
   fresh complete natural family with original custody, then performs structural
   qualification and countersigned READ through existing helpers.
4. Final N100 authoring propagates `joint_role_basis` through intent, registered
   plans, wrapper and recipe; it retains the generic manual selector and all
   capacity/natural, exact source, reserve, guard and root ledger predicates.
5. Final N100 intent/worker freeze waits for separately reviewed paired definitions
   and analyzer. This slice implements no contrasts, new CI or selection rule.

Prepared supply binds exactly runtime.py plus kb_policy, knowledge_provider,
knowledge_stores and phase_supply. `_require_prepared_implementation` verifies
those bytes. Existing final authoring additionally freezes reader/analyzer
identity; `resolve_analysis` is source-identity-only. Therefore independently
frozen structural preparation may coexist with CPU-only analysis engineering,
but later reuse must retain every bound config/policy/implementation byte.
There is no post-freeze dependency replacement. K-only learner export stays
unchanged; stage metrics, score authority, executor and bootstrap are untouched.
