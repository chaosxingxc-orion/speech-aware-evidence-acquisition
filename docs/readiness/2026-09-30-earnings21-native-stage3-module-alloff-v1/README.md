# Consumption-module all-off arm on earnings (carrier admission gate, HELD)

Registered before contact 2026-09-30 at study commit `60eb5feaa` (branch `fable/carrierhooks`) by
`scripts/flights/module/register_carrier_module_alloff_cells.py --carrier e21`; owner decision 196, direction
205; design `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` sections 2b.3 and 3.2. **HELD**: decision 187 keeps the GPU on SLURP until the SLURP lock. Nothing
here authorises a flight, a flip or an admission entry.

**What it is.** The evidence-consumption module `saea-evidence-consumption-module-v1`, profile `earnings`, with
every component off. Earnings has no locked system: the six-node form flew once (item E35, STRUCTURAL PASS) and is NOT admitted (base lock v3 section 4; E39 / E41 are four-row form proofs). The E35 read names the DIRECT arm as the comparator, so the module's all-off arm is the direct baseline on the full discovery roster -- e21-native-window-direct-full44-v1, referenced byte for byte (it carries no fit identity).

**Why.** Design 2b.3 item 3: a carrier admits the module only after its module-bare arm is flown as an A/A on the
carrier's own roster; its half-widths are that carrier's module null. Own null: E21's measured own null (WER 0.058, PERSON 0.250, ORG 0.356, numeric 0.157; docs/results/2026-09-27-verdict-reclassification.md) was measured on the pre-FlightRuntime buf90 direct form (SAEA-E21-FULL44-NULL-REPLICATE-V1), NOT on these native-window bytes; the module null on this form is unmeasured until an in-chain A/A of this arm seals (design 2b.3).

**The byte proof** (`python -B scripts/analysis/module_equivalence_proof.py --at e210`): ok = True.

| cell | experiment / fragment | composed identical | policy leaves differing from own | policy leaves vs direct parent | bookkeeping vs direct parent | ok |
| --- | --- | --- | --- | --- | --- | --- |
| direct-layer | `e21-native-window-direct-full44-v1` | -- | [] | -- | -- | True |
| arm | `earnings21-native-stage3-module-alloff-v1` | True | [] | [] | [] | True |
| smoke | `earnings21-native-stage3-module-alloff-smoke-4-v1` | True | [] | [] | [] | True |

**Cells.** arm `earnings21-native-stage3-module-alloff-v1` (`SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-V1`, 1593 rows, composed `3b5c8ed17fe0a6fc...`);
smoke `earnings21-native-stage3-module-alloff-smoke-4-v1` (`SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1`, 4 rows). Read row `SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-FORM-READ-V1` (descriptive form read).
Carrier hooks with no analogue here (`None`, so the module refuses those components): current_lock, decision_candidates, decision_supply_path, deliver_stages, delivered_path_admissions, flown_branch_programs, lock_versions, max_decision_candidates, perception_branch_frame.

**Measurement.** `form-proof`, `claims_benefit: false`, expected effect 0.0 (instrument rule 5). Scorers: asr-wer-whisper (Whisper-normalised WER) beside conec-entity-wer-official, numeric-value-accuracy-v1, semantic-high-impact-error-rate-v1 and cost.

**If the owner reopens this carrier.** (1) Root countersigns the DRAFT rows and mints `coordination/earnings21-native-stage3-module-alloff-v1/root-admission-v1.json` with
`scripts/flights/module/module_alloff_mint_receipt.py --carrier e21`. (2) `scripts/flights/module/module_alloff_e210_flip.sh`
re-pins the smoke and the arm. (3) `scripts/flights/module/batch_chain_module_alloff_e210.sh` queues them on
`serving-e21-native-window-flightruntime-np4-max1024-v1`. (4) `scripts/flights/module/module_alloff_e210_read.sh` names the read.

**Not authorised.** No flight, no component-on cell on this carrier, no re-flight of any sealed cell, no test-split contact.

## Coordinator ruling (Fable 5.1, 2026-09-30)

The all-off byte proof `scripts/analysis/module_equivalence_proof.py --at e210` (merge `906dd8fe`; `ok`) is accepted
as the Earnings-21 module admission form proof: with every component off, the module-composed arm is byte-identical
to the carrier's own direct baseline. The cells stay **HELD** and **unflown** under owner decision 187 (SLURP-only
GPU) until the owner rules decision 209; option C would open the carrier flights after the SLURP close. The E21
native-window own null must be measured by an in-chain A/A of this all-off arm before any E21 component claims
benefit. Earnings-22 has no own null and no baseline fragment; the thin Earnings-22 runtime adapter carries no cell.
No countersignature, mint, flip or re-pin follows from this ruling.
