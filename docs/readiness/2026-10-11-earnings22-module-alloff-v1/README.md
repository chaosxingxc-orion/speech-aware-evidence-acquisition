# Consumption-module all-off arm on earnings22 (carrier admission gate, HELD)

Registered before contact 2026-10-11 at study commit `01e6aa750` (branch `sonnet/e22-register`) by
`scripts/flights/module/register_carrier_module_alloff_cells.py --carrier e22`; owner decision 196, direction
205; design `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` sections 2b.3 and 3.2. **HELD**: decision 187 keeps the GPU on SLURP until the SLURP lock. Nothing
here authorises a flight, a flip or an admission entry.

**What it is.** The evidence-consumption module `saea-evidence-consumption-module-v1`, profile `earnings22`, with
every component off. Earnings-22 has no locked system and no direct parent cell: the shared direct layer e22-native-window-direct-base-v1 (the phase-direct-only-v1 program and its one phase_material.direct entry, the generic transcription instruction bytes shared with E21) is the whole comparator, so the module's all-off arm is that base fragment plus the E21-shaped native-window geometry and pins on the Earnings-22 dev split. No knowledge supply, no ConEC layer, no entity scorer, no analytical tool.

**Why.** Design 2b.3 item 3: a carrier admits the module only after its module-bare arm is flown as an A/A on the
carrier's own roster; its half-widths are that carrier's module null. Own null: Earnings-22 has NO measured own null on this form (no cell has ever flown on the native-window dev form); the module null is unmeasured until an in-chain A/A of this arm seals (design 2b.3). The all-off arm is therefore a form proof only, and no benefit may be claimed on this carrier until that A/A exists.

**The byte proof** (`python -B scripts/analysis/module_equivalence_proof.py --at e220`): ok = True.

| cell | experiment / fragment | composed identical | policy leaves differing from own | policy leaves vs direct parent | bookkeeping vs direct parent | ok |
| --- | --- | --- | --- | --- | --- | --- |
| direct-layer | `e22-native-window-direct-base-v1` | -- | [] | -- | -- | True |
| arm | `earnings22-native-stage3-module-alloff-v1` | True | [] | [] | [] | True |
| smoke | `earnings22-native-stage3-module-alloff-smoke-4-v1` | True | [] | [] | [] | True |

**Cells.** arm `earnings22-native-stage3-module-alloff-v1` (`SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1`, 451 rows, composed `f35237082d1ace6f...`);
smoke `earnings22-native-stage3-module-alloff-smoke-4-v1` (`SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1`, 4 rows). Read row `SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-FORM-READ-V1` (descriptive form read).
Carrier hooks with no analogue here (`None`, so the module refuses those components): current_lock, decision_candidates, decision_supply_path, deliver_stages, delivered_path_admissions, flown_branch_programs, lock_deliver_normalisers, lock_versions, max_decision_candidates, perception_branch_frame, perception_template_variant_frame, template_variant_frame.

**Measurement.** `form-proof`, `claims_benefit: false`, expected effect 0.0 (instrument rule 5). Scorers: asr-wer-whisper only (corpus-level Whisper English-normalizer WER, the paper-facing metric; no ConEC, entity or numeric layer exists for Earnings-22). Scorer variant: the PLAIN window-form scorer, NOT the ESB short-form tail-2 s variant of docs/readiness/2026-09-05-scoring-alignment-conclusions.md (15.937 sealed vs 9.2377 under the 2.0 s digital-silence tail, deviation D-TS2-3): this cell appends no tail silence, reads whole 90 s windows of whole dev calls rather than ESB test utterances, and so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band is claimed.

**If the owner reopens this carrier.** (1) Root countersigns the DRAFT rows and mints `coordination/earnings22-native-stage3-module-alloff-v1/root-admission-v1.json` with
`scripts/flights/module/module_alloff_mint_receipt.py --carrier e22`. (2) `scripts/flights/module/module_alloff_e220_flip.sh`
re-pins the smoke and the arm. (3) `scripts/flights/module/batch_chain_module_alloff_e220.sh` queues them on
`serving-e22-native-window-flightruntime-np4-max1024-v1`. (4) `scripts/flights/module/module_alloff_e220_read.sh` names the read.

**Not authorised.** No flight, no component-on cell on this carrier, no re-flight of any sealed cell, no test-split contact.
