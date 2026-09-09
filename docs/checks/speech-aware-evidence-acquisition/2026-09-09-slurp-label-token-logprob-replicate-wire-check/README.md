# LP-2 confirmation cell wire check — `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-REPLICATE-V1`

**Zero contacts, zero servers, zero sockets.** Only two things are faked, and they are the two
`FlightRuntime.wire_check` fakes: the gate and the transport. Everything else is the production
request path — the real `core.config.compose`, the real fragments, the real adapter, the real
roster loader, the real payload binding, the real packet reads. The speech-feature packets *are*
opened and hash-verified, so this runs on the machine that holds `SPEECHRL_DATA_DIR`; no MP3 is
decoded and no audio is resampled, so the pinned absence of `ffmpeg` is preserved.

Runner: `scripts/slurp_label_token_logprob_wire_check.py`. Machine-readable half:
`wire-check.json`. The cell, its rule and its claim surface live in
`docs/readiness/2026-09-09-slurp-label-token-logprob-judge-lp2-v1-preregistration.md`.

## What it has to prove

The confirmation cell is a **fresh replicate**, not a new arm. Its whole purpose is to give the
LP-2 label-token judge rows its threshold was *not* fitted to, and that purpose evaporates if the
replicate quietly changed anything: a different request would answer a different question, and the
frozen threshold would be read against a distribution it was never meant for. So "nothing
functional moved" is checked mechanically here rather than asserted in the fragment.

| stage | result |
|---|---|
| `request` | **PASS** |
| `payload_binding` | **PASS** |
| `media_identity` | **PASS** |
| **overall** | **PASS** |

## `request` — the composed configs and the bound payloads

Both FULL cells composed with the real `core.config.compose`.

| | value |
|---|---|
| shared baseline / dataset / model fragment | `slurp-direct-closed-list` / `slurp-speech-native-dev1000` / `q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64-logprobs5` |
| shared arm | `speech-feature-query` |
| composed keys that moved | `budget_basis`, `cells`, `execution_plan`, `experiment_id`, `preregistration`, `profile_basis`, `purpose`, `wire_check_script` |
| carried by the predecessor alone | `declared_protocol_change`, `one_key_basis`, `read_script` |
| carried by the replicate alone | `design_read`, `frozen_judge`, `one_factor_basis`, `smoke` |
| **keys outside the experiment fragments that differ** | **none** |
| `decoding_params` identical | **yes** — `{id_slot: per-sample, logprobs: true, max_tokens: 64, seed: 20260803, temperature: 0, top_logprobs: 5}` |

**The crisp form of the claim.** Strip every key either experiment fragment declares and hash what
is left: the model, dataset and baseline halves of both composed configs come to the *same*
sha256, `014d052acd8430f4b30b532c9e5c6d25a2b4541ff311609facc1f38f68055a5b`. Nothing that reaches a
request moved.

`config_hash` does move, `15670eaa…711e587` → `6ecd015d…88c739b`, and it must: two runs cannot
share an experiment identity, and `experiment_id`, `purpose`, `execution_plan`, `cells` and the
budget basis all ride the composed hash like every other declared key. `protocol_hash` against a
fixed all-zero split identity moves with it, `bceed4f0…` → `722bb57e…`.

**The bound payloads.** `FlightRuntime.wire_check(seal_and_score=False)` on both smoke cells — the
predecessor's four rows and the replicate's eight — paired **by sample id**, never by dispatch
position. On all four rows the two arms share:

* `payload_fields_moved`: **empty**;
* `decoding_params_moved`: **empty**;
* `protocol_payload_sha256` (the canonical boundary payload with the two run-local values
  stripped): **identical between the arms**, row by row;
* `task_instruction_sha256` `4073f79e…0d37db` on both — the predecessor flight's own rendered
  instruction, unchanged;
* `model_contacts` 0 in both receipts, and `payload_keys_equal_arm_visible_fields` true in both.

Two payload values are exempt and are named rather than tolerated silently: `request_id`, the
flight's dispatch-order counter, and `decoding_params.id_slot`, the `per-sample` sentinel resolved
to whichever server slot the executor allocated in that run. Both differ between any two runs of
one config, so a difference in either is not a protocol difference.

## `payload_binding` — the mandatory stage between request and seal

`rails.core_client.payload_binding_stage` on the replicate's own real roster rows, through the real
carrier root `.../speechrl-data/datasets/slurp` and this fragment's declared derived media roots
(there are none).

| cell | rows in the fragment | rows checked | bound | failures |
|---|---:|---:|---|---:|
| the eight-row smoke | 8 | **8 (every row)** | yes | 0 |
| the 1,000-row cell | 1,000 | 2 (first and last) | yes | 0 |

Zero model contacts and zero sockets in both.

## `media_identity` — the replicate reads the predecessor's own bytes

A replicate that read different packets off a different featcache would be a different observation
wearing the same config, so the packet identity is checked rather than assumed.

| | value |
|---|---|
| packets verified | 4 (predecessor smoke), 8 (replicate smoke) |
| rows the two share | 4 |
| identical packet sha256 on every shared row | **yes** |
| declared packet root, both arms | `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` |
| declared `LLAMA_SPEECH_DECODER_SHA256`, both arms | `0751c279…8066d` |

## Files

| file | what it holds |
|---|---|
| `wire-check.json` | all three stages: the composed diff and both functional hashes, the per-row bound payloads, both binding stages, the packet identity table |
| `MANIFEST.sha256` | this directory's byte manifest |

## Reproducing

```bash
source ~/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$REPO/src
export CUDA_VISIBLE_DEVICES=
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
cd $REPO && python scripts/slurp_label_token_logprob_wire_check.py --write
```

The receipt carries no timestamp, so two consecutive writes reproduce the same `MANIFEST.sha256`.
