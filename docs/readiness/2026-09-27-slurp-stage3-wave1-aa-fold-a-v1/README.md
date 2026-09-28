# The knowledge wave's shared in-chain A/A (owner decision 164)

Registered before contact 2026-09-27 at study commit `df8ccf9ceb40b8f63cf2d927e9ba0ca93bc86186`; the cell is **held**.
Nothing here authorises a flight, a flip or an admission entry.

**What it is.** `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`: the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (intent 85.8333 /
SLU 65.1575, decision 161) re-flown byte for byte under its own run, attempt and FIT ids. Decision 164
reads the knowledge wave's arms "against ONE shared in-chain A/A of the AGREE arm's own bytes (row 160's
precedent)"; this is that cell. Derived by `scripts/flights/wave/derive_slurp_wave_aa_cell.py` (decision 58): the only differences from the AGREE
fragments are per-flight bookkeeping and the dropped `prepared_phase_supply` pin (item E16: the flip mints this
cell's own, which must carry the AGREE output digest `eab5c61e...`).

**Byte identity** (`scripts/flights/wave/wave_shared_aa_proof.py`, the decision-160 proof pointed at the pair (wave A/A, AGREE arm), model-free):
**IDENTICAL** at study commit `df8ccf9c` -- composed-config classes {"bookkeeping": 30, "supply-pin": 2}; prepared supply output digests A/A `eab5c61e` and AGREE `eab5c61e` (equal to the registered digest and to the AGREE arm's committed artifact: True); request bytes over the first 120 rows, 663 contacts: payload and POST body identical under one run id True, POST body identical under own run ids True. Receipt: [`shared-aa-proof-v1.json`](shared-aa-proof-v1.json).

**Who reads at it.**

| arm | run id | package | READ row |
| --- | --- | --- | --- |
| W1 | `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1` | `2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1` | `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1` |
| W3 | `SAEA-SLURP-STAGE3-W3-FOLD-A-V1` | `2026-09-27-slurp-stage3-w3-contrast-fold-a-v1` | `SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1` |
| W4 | `SAEA-SLURP-STAGE3-W4-FOLD-A-V1` | `2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1` | `SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1` |

**Where it flies.** Step 1 of `scripts/flights/wave/batch_chain_wave.sh`: the W1 four-row smoke, then the wave
campaign plan `configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json` = [this A/A, the W1 arm]; W3 (step 2) and W4 (step 3) follow in the same chain on
the same resident session `serving-slurp-native-candidate-five-train-a-np4-v1` -- the COMP-1 + G5 shape of decision 160. No smoke of its own (the AGREE and
COMP-1 A/As carried none).

**Fit.** perception ALLOW rendered 19,449 physical margin 4,584; reviewer ALLOW rendered 19,313 physical margin 4,720; planner ALLOW rendered 19,252 physical margin 4,781; solver COMPACT_REQUIRED rendered 21,278 physical margin 2,755 (readiness held, blockers None).

**`stage3_measurement`.** `cross-flight-with-in-chain-replicate`, `expected_effect_pp` 0.0, `claims_benefit` false,
`replicate_run_id` `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (the sealed request-identical source of its bytes). It is the instrument.
Its own READ `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1` reports the cross-flight offset (A/A minus AGREE) as context only.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-wave1-aa-fold-a-v1-preregistration.md` | the preregistration, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the read rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the A/A's plans |
| `analysis-recipe-v1.json` | the offset read, READ run id `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1` |
| `shared-aa-proof-v1.json` | the byte-identity proof against the AGREE arm |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/wave/wave_mint_receipt.py` |

**Mint, flip, queue.** Root countersigns the A/A's two DRAFT flight rows (`SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`, `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1`; the READ
row `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1` may stay DRAFT until the seal) together with the W1, W3 and W4 rows, mints `coordination/slurp-stage3-wave1-aa-fold-a-v1/root-admission-v1.json` (id
`slurp-stage3-wave1-aa-fold-a-admission-v1`, two eligible run ids) with `scripts/flights/wave/wave_mint_receipt.py` and the three arm receipts
with their own mint scripts, flips everything with `scripts/flights/wave/wave_flip.sh` (converged at ONE HEAD, which
becomes the flight commit), and queues `scripts/flights/wave/batch_chain_wave.sh`. `--allow-output-change` is never
passed.
