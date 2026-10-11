# Consumption-module all-off arm on earnings22 (carrier admission gate, HELD)

Registered before contact 2026-10-11 at study commit `13a0b367c` (branch `sonnet/e22-register`) by
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

## Earnings-22 specifics (read before reopening this carrier)

**Model-free work done.** The 10-call dev window inventory (451 fixed 90-second windows, 40,055.9 decoded seconds) and
the four-row subset batch (call 4453225, windows w0001-w0004) were built CPU-only on 2026-10-11 through the shared
`prepare-window-inventory` path, with the Earnings-21 protocol, into the data root (write-once). Counts, hashes and the
exact command are in `window-inventory-receipt-v1.json` (this directory); nothing else about the audio is recorded.
Both cells pin them; `FlightRuntime` verifies the pins down to slice bytes (4 and 451 execution units load).

**Where the first contact-requiring step sits.** `core.flight.cli check` and a Python-API wire check reach the
execution-unit roster (verified), then refuse at `core.driver.run.load_window_packet_binding`: the Earnings-22 window feature
packets (`analysis/SAEA-E22-DEV-WINDOW-GPU-ENCODING-V1/window-feature-packets.json`, and the four-row twin) do not exist.
Producing them is an encoder forward pass (root lease, GPU, registration, owner authorization); both baselines carry an
all-zero PENDING sha256 for that pin, so the composed hashes change when the real pin lands. Behind that step the runtime requires a validated non-empty knowledge snapshot for every phase-program contact, and
Earnings-22 has no governed knowledge, so both baselines pin an INERT placeholder snapshot (one facet, one value, bound to no
dataset sample; `scripts/build_e22_inert_knowledge_snapshot.py`, asset `knowledge/e22/inert/all-off-placeholder-v1/snapshot.json`
under the data root, sha256 `19c61475ef1d6a641cd5ec182479285b6bb6af2928cc17115bb01b3ef8633a31`), the same way the Earnings-21 and Audio2Tool cells pin theirs. The direct
phase declares `knowledge: "none"`, so the placeholder is bound invisibly and supplies nothing.

**Shared-code change this registration needed.** The four-row smoke is a one-call subset of the dev split, which the
Earnings runtime adapter admitted only for Earnings-21 discovery. Commit `8383e68f1` takes the parent split and carrier
from `DEFAULT_SPLIT` / `CARRIER_LOCK_KEY` (Earnings-21 messages and behaviour byte-identical) and drops the Earnings-22
refusal; the smoke dataset fragment therefore carries the adapter's own `e21_runtime_subset` key. Drop that commit and
the smoke cell becomes unrunnable (the arm is unaffected).

**Scorer variant (declared in each baseline's `what_this_is`).** `asr-wer-whisper` only, corpus-level WER under the Whisper
English normalizer, on the PLAIN window form. It is NOT the ESB short-form tail-2 s variant (15.937 sealed, NOT ALIGNED, vs
9.2377 ALIGNED with 2.0 s of digital silence appended, deviation D-TS2-3): this cell appends no silence and reads whole dev
calls in 90 s windows, not ESB test utterances, so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band
is claimed. An ESB-comparable Earnings-22 number needs the existing short-form tail-2 s dataset fragments, a different form.

**Other facts.** `earnings22-dev-subset10` has no `split_id`, which the flight runtime requires, so the arm uses the new
`earnings22-native-window-dev10-v1`. The serving session name is NEW (its feature root differs from the resident E21
session); its launch entry is a root item. The inventory plan label `split_role: discovery` (copied from the E21 inventory
fragment) is a label only; the cells declare `dev`. No in-chain A/A exists, so no benefit may be claimed on this carrier.
