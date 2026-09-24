# Cell ROLL-AA: the Stage-3 within-flight A/A null: launch runbook

Preregistration: [`../2026-09-24-slurp-stage3-roll-aa-v1-preregistration.md`](../2026-09-24-slurp-stage3-roll-aa-v1-preregistration.md).
Board route: **F2** of `docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md section 7.3`.
Substrate: cell ROLL-1 (`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`
section S3-2) and the E2b greedy-repeat twin form of
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4.
Stage-3 algorithm (owner decision 101): **`shared-rollout`**, operator `rollout`.

## 0. In one paragraph

The locked v2.0 plan's Solver answers the **identical prompt twice** for each of 200 R01C
construction rows, **inside one flight**, **greedy**. The two samples of a Solver visit are two
contacts of the *same* request object: same messages, same speech packet, same supplied knowledge,
same response format. `reproduction.ojw.native_request.compose_solver_sample_decoding_params`
overrides exactly two fields per sample -- `temperature` (0.0 for both) and `seed`
(`fragment_seed + seed_offset + sample_index`, so 2080141211 and 2080141212) -- and at temperature 0
llama.cpp decodes greedily and never consults the seed. Whatever per-row difference the offline
read then measures is the **measurement floor itself**: llama.cpp batch-composition
nondeterminism and nothing else. Its CI95 half-width becomes **`h_within`**, the margin every
ROLL-2 variant comparison at n = 200 is read against.

## 1. What is registered here

| artefact | path |
| --- | --- |
| roster (200 rows) | `docs/receipts/rosters/slurp-stage3-roll-aa-r01c-200-v1.json` |
| smoke roster (4 rows) | `docs/receipts/rosters/slurp-stage3-roll-aa-r01c-smoke-4-v1.json` |
| phase program (ceiling 13) | `configs/policy/phase-native-candidates-review-revise-samples2-v1.json` |
| baselines | `configs/baseline/slurp-native-stage3-roll-aa-baseline-v1.json`, `-smoke-4-baseline-v1.json` |
| experiments | `configs/experiment/slurp-native-stage3-roll-aa-v1.json`, `-smoke-4-v1.json` |
| campaign plan | `configs/campaign/slurp-native-stage3-roll-aa-v1.json` |
| this package | `docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1/` + the preregistration |
| exposure-ledger rows | four flight rows + one read row, `consumed = no`, drafted and awaiting root countersignature |
| derivation tool | `scripts/flights/batch/rollaa_prepare_steps.py` (`rosters` / `policy` / `fragments` / `facts` / `verify`) |
| runbooks | `rollaa_repin_{smoke,arm}.sh`, `rollaa_flip_all.sh`, `batch_chain_rollaa.sh`, `rollaa_read.sh`, `rollaa_dry_run.py` |
| byte proof | `tests/unit/test_stage3_roll_aa_baseline_cell.py` |

**Readiness is HELD on both cells.** Nothing here authorises a flight, a readiness flip, a
contact, a queue entry or an admission entry. The registration itself was written model-free: zero
model, tokenizer, encoder, scorer, GPU and network contacts, and no audio sample was decoded.

## 2. The one factor

Against cell ROLL-1 (`configs/baseline/slurp-native-stage3-rollout-baseline-v1.json`):

```
native_episode.roles.solver.samples                     5   -> 2
native_episode.roles.solver.decoding_overrides.temp   0.7   -> 0.0
native_episode.roles.solver.twin                    (absent) -> "greedy-repeat"
native_episode.roles.solver.commit.min_support          3   -> 2
policy  phase-native-candidates-review-revise-samples5-v1 (19) -> ...-samples2-v1 (13)
```

`seed_offset` stays 0. Everything else -- `knowledge_stores`, `phase_material`, the task
instruction template, the geometry, `scorers`, `evidence_source`, the arm and the filled S3-1
preparation pins -- is ROLL-1's own bytes; `tests/unit/test_stage3_roll_aa_baseline_cell.py` is the
proof.

`twin: "greedy-repeat"` is not decoration. `rails.native_episode_config` admits
`decoding_overrides.temperature == 0` **only** under that marker, and its own comment states this
cell's thesis: *"its N pinned seeds are recorded custody, never a source of diversity at
temperature 0."*

The new phase program exists because `rails.native_episode_config.load_native_episode_config`
asserts `program.max_contacts` equals the bounded graph ceiling, which at samples 2 is
`1 + (1 + 1) * (1 * 2 + 3 + 1) = 13`, not 19. Two program ids must never resolve to the same
object when their ceilings differ.

## 3. Registered identities and budgets

| run id | plan | rows | calls | speech s | GPU h |
| --- | --- | ---: | ---: | ---: | ---: |
| `SAEA-SLURP-STAGE3-ROLL-AA-V1` | `generation-plan-registered-v1.json` | 200 | 2,600 | 10,235 | 2.0 |
| `SAEA-SLURP-STAGE3-ROLL-AA-FIT-V1` | `fit-plan-registered-v1.json` | 200 | 10,400 | 10,235 | 2.0 |
| `SAEA-SLURP-STAGE3-ROLL-AA-SMOKE-4-V1` | `smoke-generation-plan-registered-v1.json` | 4 | 52 | 222 | 1.0 |
| `SAEA-SLURP-STAGE3-ROLL-AA-SMOKE-4-FIT-V1` | `smoke-fit-plan-registered-v1.json` | 4 | 208 | 222 | 1.0 |

Attempts: `attempt-slurp-native-stage3-roll-aa-v1-generation` / `-fit` and
`attempt-slurp-native-stage3-roll-aa-smoke-4-v1-generation` / `-fit`.
2,600 = 200 x 13; 10,400 = 2,600 x 4; 10,235 = `ceil(787.2898125 x 13)`; 222 = `ceil(17.0349375 x 13)`.
**Expected** spend is about 5.2 contacts per row -- about 1,040 contacts and about 0.4 GPU hours --
so the registered ceiling is about 2.5x the expectation. A ceiling is a bound, never a target, and
budgets are run-cumulative across every attempt of a run id.

Composed and protocol hashes **as registered** (every one of them moves at the flip;
`scripts/flights/batch/repin_loop_generic.sh` rewrites each document that quotes them):

| cell | composed config | protocol |
| --- | --- | --- |
| `slurp-native-stage3-roll-aa-v1` | `e763460cc4f95bb7f0078c145019431e17775e08ef5333101ad4c1cb60acb266` | `72377e8c983390623a0993f48e355e253cdbd7cafe27f425d708c24b9bff4562` |
| `slurp-native-stage3-roll-aa-smoke-4-v1` | `bea38a568f6baa40f22338181ec9d282e4feb3ddb1da5ca3603014387f7e6a5c` | `da74d580a4cceadf39ce6ea10e438876cb9654421a528347223dd717b5ceae9b` |

## 4. Smoke, arm, read

**Smoke acceptance** (4 rows): 4 in / 4 out, exactly two samples in `solver_group` per row with
seeds 2080141211 and 2080141212 and temperature 0.0 on both, no tools array, every request fits,
no abort, at most 13 contacts per row.

**Read** (`SAEA-SLURP-STAGE3-ROLL-AA-READ-V1`, model-free, `scripts/flights/batch/rollaa_read.sh`):
`scripts/analysis/stage3_rollout_score.py` `render` + `score` + `pairs` on copies (sample count
auto-detected as 2, scorer `slurp-slu-official-projected-v3-train`), then the paired-delta stage of
`analysis-recipe-v1.json`: per-row `delta = sample1 - sample0` for official SLU-F1 and intent,
the pooled micro delta with CI95 by paired row bootstrap (10,000 draws, seed 20260915), the
byte-identical / intent-flip / entity-set-flip shares, and the per-stratum table -- reported beside
the cross-flight PLAN-vs-PLANr half-widths (Fold A h_SLU 1.2485 / h_intent 0.9943;
DEV-2000-ADDED h_SLU 1.2525 / h_intent 1.1520) as **context, never as a comparator**.

## 5. Mint, re-pin, flip, queue

1. Root mints `coordination/slurp-stage3-roll-aa-v1/root-admission-v1.json`, decision id
   `slurp-stage3-roll-aa-admission-v1`, with the **four** eligible run ids of section 3 and this
   family's budget caps (`scripts/flights/batch/mint_decision_receipt.py`). Without the correct
   `eligible_run_ids`, `core.flight.campaign.declared_readiness` refuses the smoke.
2. `bash scripts/flights/batch/rollaa_flip_all.sh` -- the smoke then the arm, each through
   `repin_loop_generic.sh`. The re-pin mints this cell's own prepared phase supply under its own
   run id (item E16), inserts the decision requirement, recomputes every hash and rewrites this
   package, the preregistration and the five ledger rows. **`--allow-output-change` must never be
   passed**: this cell carries no committed pin, so a CHANGED output on a later re-pin means the
   knowledge channel moved -- stop and report.
3. `bash scripts/flights/batch/batch_chain_rollaa.sh` -- one queue step, smoke then arm, on the
   SLURP geometry through the SAEA-Batch-Driver (decision 77). It reads the flight commit from
   `/home/chao/rollaa-flight-commit.txt`. The flight lock must be clear first.
4. `bash scripts/flights/batch/rollaa_read.sh` once the arm is sealed.

## 6. What this package does not authorise

No flight before the receipt is minted and both cells are flipped; no contact by this
registration; no readiness flip; no queue entry; no serving-session change; no re-flying,
re-scoring or re-reading of any sealed comparator; no Fold A, Fold B, DEV or test contact; and no
ROLL-2 variant registration -- `h_within` must exist before a variant comparison at n = 200 is
registered against it.
