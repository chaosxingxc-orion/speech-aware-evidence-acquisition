# G5 fixed16 external recovery seal

This check seals the already completed 2026-09-02 G5 fixed16 flight without
contacting a model or any network, retriever, tokenizer, or scorer.

The original pre-contact `ExecutionPlan` bound split hash
`8c0136a901693548a737bf4bf3fa83206d9bae190283123d6412be6a78b069fe`.
The generic `audio2tool/<sample_id>` recomputation for the same sixteen
identifiers is `62d2372ecc5a...`.  It therefore also changes the protocol
hash.  The durable attempt is ABORTED after the original seal failure.

`core.bundle.verify_bundle` cannot be achieved honestly for this candidate:
doing so would require retrospectively changing the plan's split hash and
protocol hash, the candidate manifest's identity fields, and the durable
terminal attempt state.  This check does none of those things.  It writes one
new, write-once `g5-recovery-seal.json` beside the flight, which hashes every
pre-existing flight artifact and records the exact formal-verification limit.
The candidate remains unscored and is not a qualified paper candidate.

Run only in the WSL environment that can address the durable flight:

```bash
~/.venvs/speechrl/bin/python \
  docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-g5-fixed16-recovery-seal-v1/seal_g5_recovery.py \
  --mission-dir /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1/flight-20260902T210832Z \
  --attempts-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/attempts
```

The command refuses an existing recovery seal instead of overwriting it.
