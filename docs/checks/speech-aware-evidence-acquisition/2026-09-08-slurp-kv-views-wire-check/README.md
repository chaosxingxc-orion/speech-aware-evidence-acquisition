# KV knowledge views — request-half wire check, all seven arms (2026-09-08)

Row `SAEA-SLURP-MF-KV-VIEWS-PREP-V1`, profile `model-free-check`. Fragment
`configs/experiment/slurp-kv-views-wire-check-4-v1.json` (wire-check only; it carries a never-fly
note and has no exposure row of its own). Preregistration
`docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md`.

**PASS on all seven arms.** 4 DEV-1000 rows each, on a clean committed tree, against
`core.flight.runtime.WireCheckGate` and `WireCheckTransport` — **zero sockets, zero model
contacts, zero GPU**. Everything between the two fakes is real: `core.config.compose`, the
label-free roster with every media file re-hashed, the knowledge-snapshot load and content-hash
verification, the sealed-manifest predecessor binding, the phase program, the KV state fill mining
TRAIN, `rails.runner`'s containment fold on every contact instruction, the request build, the
transport seam, the bundle seal and `core.scoring_batch` over the complete manifest.

## The seven arms

| cell | view / twin | contacts | model contacts | seal + score | config hash | protocol hash |
|---|---|---|---|---|---|---|
| `kv0-examples-free` | `examples-free` | 4 / 4 | **0** | **OK** | `781fae97…` | `e0fa24a0…` |
| `kv1-descriptions` | `descriptions` | 4 / 4 | **0** | **OK** | `0a9e3555…` | `bb897bd2…` |
| `kv1-descriptions-twin` | `descriptions`, twin | 4 / 4 | **0** | **OK** | `59d37955…` | `b25e5ba5…` |
| `kv2-cards` | `cards` | 4 / 4 | **0** | **OK** | `4f2714e6…` | `a591adb5…` |
| `kv2-cards-twin` | `cards`, twin | 4 / 4 | **0** | **OK** | `5b47a0df…` | `652668dd…` |
| `kv3-fewshot` | `fewshot`, k = 3, seed 20260903 | 4 / 4 | **0** | **OK** | `323200a2…` | `a452dfbd…` |
| `kv3-fewshot-twin` | `fewshot`, twin | 4 / 4 | **0** | **OK** | `343241ee…` | `aa663d3d…` |

## What the check proves

| assertion | result |
|---|---|
| model contacts | **0** on every arm; the `cost` block's 4 calls and 15.011 audio seconds are the FAKE transport's, metered because the meter does not know the transport is fake |
| dispatch | `phase-program`, `program_id` **`phase-slots-given-intent-v1`** — KC-S1b's own program, no new policy id — one phase `slots`, rows 4, contacts 4, `contacts_per_sample` 1 |
| `supplied_phases` / `seeded_supply_phases` | **empty** on every arm; `phase_supply` is `null`. A KV view is deterministic and declares no retrieval |
| typed knowledge blocks on the request | **0** on every row — correct, and the point: a KV view is instruction-side, not traced supply. This is where KU-S3 (KV-4) reads non-zero |
| resolved system message | sha256 **`4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db`** on **all seven** arms — byte-identical to KC-S1b's own, and to the sealed closed-list baseline's instruction plus its 1,836-character suffix |
| the arm's static DIRECTIVE | sha256 **`221ed0d343b0a543eda98008312938da25bde204a131efe8427ea8e3934a5e1f`**, 841 characters, on **all seven** arms — this is containment fold C1 stated as an identity: every KV arm ships the same control bytes and the view lives only in the per-sample block |
| containment at contact time | `rails.runner._assert_agent_control_excludes_knowledge_payloads` raised on **none of the 28 contacts**, against the bound snapshot's 11,863 protected payloads |
| distinct request bodies | 4 of 4 per arm, each with its own speech packet re-verified |
| payload keys equal the arm's visible fields | true, 18 keys, on every arm |
| config and protocol hashes | **distinct per arm** — `fill_params` rides the config hash, so the view and the twin flag are part of what each cell IS |
| seal and score | **OK** on every arm: a sealed run manifest with 4 canonical output rows, and all four declared scorers (`slurp-slu-official`, `slurp-slu-f1-normalized-v1`, `slurp-slu`, `cost`) running to completion over the complete manifest through `core.scoring_batch` |

**No score here is a measurement.** The transport answers every row with its canned string; the
scorers ran to prove they run, and nothing they produced enters a verdict, a comparator or an
admission.

## One operational number for the flight

The KV state fill mines TRAIN once per run, inside `_resolved_state_fills`, before the first
contact. Measured as the difference in dispatch wall time between the arm that skips it and the
arms that do not: **6.2 s (KV-0, no TRAIN mining) against 8.8–11.0 s** for the six views that
build cards, descriptions or exemplars — so the mining costs roughly **3–5 seconds**, once, for a
whole flight. That is the whole pre-flight cost of a KV view, and it is the operational contrast
with KV-4: KU-S3's retrieval seed costs 0.68–0.71 h of single-threaded CPU per arm.

## A defect this check found and the fix that was applied

The first pass ran the seven arms writing their receipts **into the repository**, and six of the
seven came back `SCORING_FAILED`: `core.scorers._assert_scoring_entry_gate` calls
`require_clean_study_repo`, which refuses an **untracked** file as readily as a modified one, so
each arm's own freshly written receipt dirtied the tree for the next arm. The fix is not a code
change: receipts are written outside the repository during the run and copied in afterwards. The
first arm passed and the rest failed, which is exactly the signature of this defect and is recorded
here so the next agent recognises it in one line rather than in an hour.

## Files

`kv0-examples-free.json` … `kv3-fewshot-twin.json` — one `saea-slurp-closed-list-wire-check-v1`
receipt per arm, as written by `scripts/flights/run_slurp_closed_list_cell.py --wire-check`.
`MANIFEST.sha256` — sha256 over every other file here.
