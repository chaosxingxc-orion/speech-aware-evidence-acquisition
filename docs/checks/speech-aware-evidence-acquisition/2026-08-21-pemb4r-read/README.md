# P-EMB-4R registered one-shot model-free read — archive (2026-08-21)

This directory is the single sanctioned read of the seven completed P-EMB-4R
embedding arms (`SAEA-PROBE-pemb4r-4100`). The 2026-08-21 pre-read owner
amendment canceled C-DECODE after the flight receipt had proved zero generation
contacts and authorized closure from the landed vectors only.

## Inputs and integrity

| Item | Bound input |
|---|---|
| Query set | Frozen SLURP devel-60, split identity `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| Key bank | 900 SLURP train utterances, 50 per scenario, bank manifest `5f48895107d715a7eae2954fe56f833455d33df3d6527e3643a0b0c924f5b112` |
| Retrieval plan | `7150c6b3410de4cc883da7f5ef0798dd80e4beaf253037594e99ff8cf5cea768` |
| Vector assets | Four existing bank manifests and seven existing query manifests; 4,033 files were hash-verified on load |
| Retrieval re-derivation | `True`, zero mismatches |
| Repeat noise | Re-derived from the landed LCO-3B, LCO-7B and Qwen repeat-vector pairs |
| Read implementation | `analysis/pemb4r_read.py`, SHA-256 `29d8d96d438dbe4f3be4cbb886238f2a6c6e6952338cee3604341c0b3f79981a` |
| Study base commit | `07d0cf06851998ecb607734ca41a04a292fba563` |
| Model/GPU contact | None; file and scoring reads only |

The read reused the existing flight loaders for every manifest and the existing
`pemb4r_flight.build_arm_retrieval` implementation for independent
re-derivation. No embedding was regenerated, no cache was modified, and no
llama.cpp process was started.

## Outcome

Overall registered result: **`REGISTER-RESCUE(a-glap) +
KNN-BEATS-LABEL-MATCH`**. C-DECODE status is explicitly
**`CANCELED-BY-OWNER-2026-08-21`**.

| Arm | Query/model | Vote accuracy K=5 | Recall@1/3/5 | Interpretation |
|---|---|---:|---:|---|
| A-LCO3 | speech / LCO-3B | 9/60 = 0.1500 | 0.1833 / 0.3000 / 0.3000 | No rescue; pooling-override scoped |
| A-LCO7 | speech / LCO-7B | 7/60 = 0.1167 | 0.1167 / 0.1500 / 0.2000 | No rescue; pooling-override scoped |
| A-GLAP | speech / GLAP | **19/60 = 0.3167** | 0.3167 / 0.5167 / 0.5667 | Registered register-rescue threshold met, but far below direct speech classification |
| T-LCO3 | T0 text / LCO-3B | 33/60 = 0.5500 | 0.5167 / 0.7000 / 0.7833 | Text-mediated diagnostic |
| T-LCO7 | T0 text / LCO-7B | 34/60 = 0.5667 | 0.6333 / 0.7333 / 0.8667 | Text-mediated diagnostic |
| T-GLAP | T0 text / GLAP | 13/60 = 0.2167 | 0.2500 / 0.4333 / 0.5167 | Text-side control |
| T-QW | T0 text / Qwen embedding | **52/60 = 0.8667** | 0.8500 / 0.9167 / 0.9333 | KNN beats the cited 0.7500 label-match result; text-mediated only |

The GLAP speech arm removes the former blanket statement that every flown
audio-side construction is at or below 0.15. It does not establish an effective
speech-native method: 0.3167 remains 30 correct samples below the consumed
FS-NONE direct-speech baseline (49/60), and this probe never tested joint
decoder-conditioned speech-feature and text-key matching.

## Scope lock

This archive closes only the independently pooled embedding/cosine/kNN family
represented by the seven flown arms. It must not be cited as a failure of:

- speech features used directly inside the frozen Omni decoder;
- joint speech-query and text-key matching in one decoder context;
- speech-conditioned multi-step matching or verification; or
- any method that preserves the original speech packet at every decision step.

The strong T-QW result is a text-mediated diagnostic and is not a permitted
fallback for the speech-native successor study.

## Contents

- `verdict.json` — machine-readable `saea-pemb4r-read-v1` report.
- `report.txt` — rendered registered metrics and verdicts.
- `README.md` — this archive receipt.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.
