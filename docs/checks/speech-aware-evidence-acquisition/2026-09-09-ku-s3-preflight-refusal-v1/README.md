# KU-S3 pre-generation refusal and recovery evidence

The original max256 campaign completed the 1,000-row matched control and its single full official score. Speech and twin each failed preflight before opening a generation attempt; neither generated a response. The queue retried each failed preflight once while draining scoring. The original command returned zero despite unfinished failed cells; this is an engineering defect, not successful campaign completion.

The saved full-roster fake-wire traces prove the named boundary mismatch. Across both 1,000-row arms, all differences were request IDs, worker slots and request-owned `rails-message/<request-id>/<index>` provenance addresses. The latter never enter the transport's model-visible messages. Source identities, hashes, ordered evidence, speech packets, predecessor, prompt and max256 ceiling were unchanged. Narrow canonicalization now validates ownership and replaces only that routing segment for comparison. All four saved preflight traces match their fitted arm under this normalization. Original traces and fit certificates remain untouched.

A nonblocking stack inspection separately located repeated TRAIN parsing in `run_speech_native_agent_loop -> SlurpAdapter.build_task_contract -> load_slurp_ontology`. The cache fix retains TRAIN-only source semantics, hashes source bytes on every lookup, binds the governed identity and loader implementation, and rechecks cold-load source stability. It returns the same immutable rendered contract.

The old resident session is no longer live. Its stop receipt records ALREADY_EXITED at 18:29:16 UTC; the available evidence does not identify the original cause of exit. The owner subsequently approved one additional full matched control so the recovered control, speech and twin can share a new resident process. Preserve the completed control as separate replication evidence. Do not read comparative treatment outcomes before the three recovery generations seal; do not reinterpret an old capacity receipt as a new fit.

These are engineering and custody findings, not a retrieval-effectiveness result. The broader Stage-2 experiment plan remains incomplete.
