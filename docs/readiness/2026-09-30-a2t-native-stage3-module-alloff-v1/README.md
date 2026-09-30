# Consumption-module all-off arm on audio2tool (carrier admission gate, HELD)

Registered before contact 2026-09-30 at study commit `60eb5feaa` (branch `fable/carrierhooks`) by
`scripts/flights/module/register_carrier_module_alloff_cells.py --carrier a2t`; owner decision 196, direction
205; design `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` sections 2b.3 and 3.2. **HELD**: decision 187 keeps the GPU on SLURP until the SLURP lock. Nothing
here authorises a flight, a flip or an admission entry.

**What it is.** The evidence-consumption module `saea-evidence-consumption-module-v1`, profile `audio2tool`, with
every component off. Audio2Tool has no locked system (base lock v3 section 4; the harness receipt names no Audio2Tool default plan), so the module's all-off arm is the DIRECT baseline of the shared controller -- a2t-native-system-direct-v1's policy blocks (phase-direct-only-v1 and its one phase_material.direct entry), byte-identical to the sealed direct a2t-native-role-direct-union4000-v1 and to both A2T-AA passes.

**Why.** Design 2b.3 item 3: a carrier admits the module only after its module-bare arm is flown as an A/A on the
carrier's own roster; its half-widths are that carrier's module null. Own null: h_A2T 1.625 pp official tool accuracy, 1.375 pp official exact match, parameter-F1 margin 2.23 (owner decision 167, docs/results/2026-09-27-a2t-aa-paired-400-read.md), measured on THESE request bytes: the all-off arm is request-identical to A2T-AA pass A and pass B, so its module null is that null by construction, and the carrier admission gate (design 2b.3) is met by the byte proof without a new flight.

**The byte proof** (`python -B scripts/analysis/module_equivalence_proof.py --at a2t0`): ok = True.

| cell | experiment / fragment | composed identical | policy leaves differing from own | policy leaves vs direct parent | bookkeeping vs direct parent | ok |
| --- | --- | --- | --- | --- | --- | --- |
| direct-layer | `a2t-native-system-direct-v1` | -- | [] | -- | -- | True |
| arm | `a2t-native-stage3-module-alloff-v1` | True | [] | [] | ['live_phase_fit.attempt_id', 'live_phase_fit.run_id', 'what_this_is'] | True |
| smoke | `a2t-native-stage3-module-alloff-smoke-4-v1` | True | [] | [] | ['live_phase_fit.attempt_id', 'live_phase_fit.run_id', 'what_this_is'] | True |

**Cells.** arm `a2t-native-stage3-module-alloff-v1` (`SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-V1`, 400 rows, composed `b78a4171904e6f6a...`);
smoke `a2t-native-stage3-module-alloff-smoke-4-v1` (`SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1`, 4 rows). Read row `SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-FORM-READ-V1` (descriptive form read).
Carrier hooks with no analogue here (`None`, so the module refuses those components): current_lock, decision_supply_path, default_deliver_normaliser, deliver_stages, delivered_path_admissions, flown_branch_programs, lock_versions, perception_branch_frame.

**Measurement.** `form-proof`, `claims_benefit: false`, expected effect 0.0 (instrument rule 5). Scorers: a2t-toolcall-official (paper-facing, arXiv:2604.22821 Table 3 calibration) beside a2t-toolcall-v2 / a2t-toolcall / cost.

**If the owner reopens this carrier.** (1) Root countersigns the DRAFT rows and mints `coordination/a2t-native-stage3-module-alloff-v1/root-admission-v1.json` with
`scripts/flights/module/module_alloff_mint_receipt.py --carrier a2t`. (2) `scripts/flights/module/module_alloff_a2t0_flip.sh`
re-pins the smoke and the arm. (3) `scripts/flights/module/batch_chain_module_alloff_a2t0.sh` queues them on
`serving-a2t-native-role-base-np3-max2048-v3`. (4) `scripts/flights/module/module_alloff_a2t0_read.sh` names the read.

**Not authorised.** No flight, no component-on cell on this carrier, no re-flight of any sealed cell, no test-split contact.

## Coordinator ruling (Fable 5.1, 2026-09-30)

The all-off byte proof `scripts/analysis/module_equivalence_proof.py --at a2t0` (merge `906dd8fe`; `ok`) is accepted
as the Audio2Tool module admission form proof: with every component off, the module-composed arm is byte-identical
to the carrier's own direct baseline. The cells stay **HELD** and **unflown** under owner decision 187 (SLURP-only
GPU) until the owner rules decision 209; option C would open the carrier flights after the SLURP close. No
countersignature, mint, flip or re-pin follows from this ruling.
