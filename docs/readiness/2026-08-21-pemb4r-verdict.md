# P-EMB-4R verdict — REGISTER-RESCUE(a-glap) + KNN-BEATS-LABEL-MATCH

Date: 2026-08-21. Profile: `bounded-discovery-probe`. This is the registered
one-shot, model-free read of the seven P-EMB-4R embedding arms. C-DECODE was
canceled by the pre-read owner amendment and made zero generation contacts.

## Mechanical result

The flight-written retrieval plan was independently re-derived from all 4,033
landed, hash-verified vector files with zero mismatches.

| Arm | K=5 vote accuracy | Recall@5 | Registered interpretation |
|---|---:|---:|---|
| A-LCO3 | 9/60 = 0.1500 | 0.3000 | No register rescue; pooling-override scoped |
| A-LCO7 | 7/60 = 0.1167 | 0.2000 | No register rescue; pooling-override scoped |
| A-GLAP | **19/60 = 0.3167** | **0.5667** | **REGISTER-RESCUE** |
| T-LCO3 | 33/60 = 0.5500 | 0.7833 | Text-mediated diagnostic |
| T-LCO7 | 34/60 = 0.5667 | 0.8667 | Text-mediated diagnostic |
| T-GLAP | 13/60 = 0.2167 | 0.5167 | Text-side control |
| T-QW | **52/60 = 0.8667** | **0.9333** | **KNN-BEATS-LABEL-MATCH** |

`AUDIO-CONTENT-ABSENT` did not fire because A-GLAP exceeded its 0.15 ceiling.
`AUDIO-ROUTES` did not fire because no speech arm reached 0.65. The canceled
C-DECODE arm has no end-to-end comparison and contributes no verdict.

## Scientific interpretation

Register alignment matters, but independent speech embeddings remain
insufficient as the primary method. GLAP rises from the prior 0.1333
audio-to-label control to 0.3167 on utterance-to-utterance keys and reaches the
gold label somewhere in its top five for 34/60 samples. This is a real weak
signal and invalidates a blanket claim that all audio embeddings contain no
routing content. It is still substantially below direct speech classification
(cited FS-NONE 49/60 = 0.8167) and does not satisfy the study's effective-method
criterion.

The T-QW result shows that maintainable utterance-text keys are a strong key
representation when the query is already text-mediated. It does not answer the
speech-native question and cannot be promoted as the successor query path.

Accordingly, P-EMB-4R closes the independent pooled embedding/cosine/kNN branch
as the main solution, while preserving the successor hypothesis: precomputed
speech features must be carried into the frozen Omni decoder and jointly
matched against text keys under decoder conditioning, without any parameter
update and without substituting a transcript-only query.

## Citation boundary

This result is discovery-tier, n=60, same-distribution, and single-run per arm.
It supports neither final superiority nor generalization. It does not test the
mmproj-free packet transport or the planned speech-feature-query × text-key
decoder matcher.

Evidence archive:
`docs/checks/speech-aware-evidence-acquisition/2026-08-21-pemb4r-read/`.

## Addendum (2026-09-08): binding-config sha256 re-pinned, this flight's evidence unchanged

Umbrella commit `faebc8f` (owner Decision 11-D: commit the pending umbrella lock changes and
re-pin the study's P-EMB hashes, chosen over reverting the lock) resolved the umbrella lock's
`lco-embedding-omni-3b-gguf` entry from an unresolved local candidate (`LOCAL_CANDIDATE`,
`UNRESOLVED_LOCAL_SOURCE`) to a real Hugging Face source (`marksverdhei/LCO-Embedding-Omni-3B-GGUF`
@ `af8a36fbb6e7629c9dbcb218478c6b1477b36e09`, lifecycle `AUXILIARY`, 3 verified files with per-file
sha256; `lco-embedding-omni-7b-gguf`/`glap`/`qwen3-embedding-0.6b-gguf` unchanged). `rails.probes.
pemb4r_flight.BINDING_CONFIG_SHA256` was re-pinned to the digest this resolved entry now produces;
the prior digest is preserved as `BINDING_CONFIG_SHA256_AT_FLIGHT` and still matches this flight's
own sealed `flight-receipt.json`/`flight-state.json`/`config-values.json` `binding_config_sha256`
field verbatim (test `test_binding_config_sha256_at_flight_matches_the_sealed_pemb4r_receipt`) —
**this flight was not re-run and its evidence above is unchanged.** The lock's pre-`faebc8f` entry
carried no per-file sha256 for this model (only an aggregate size/file count, which moved by 1,462
bytes as the file count dropped 5 → 3), so the lock's own metadata alone cannot prove the model
bytes are identical across the two lock versions; corroborating, not certifying, this flight's own
`model_file_measurements` independently hashed `LCO-Embedding-Omni-3B-Q8_0.gguf` and its mmproj
file at flight time, before the lock carried any per-file hash, and both measured values equal the
two GGUF hashes the resolved entry now pins (its third file, `README.md`, was never independently
hashed here). Any future reuse of this embedder must re-verify against the resolved lock entry
rather than lean on this note.
