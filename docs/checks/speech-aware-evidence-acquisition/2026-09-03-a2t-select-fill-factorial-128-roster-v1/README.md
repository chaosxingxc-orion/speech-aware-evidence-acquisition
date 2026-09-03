# Audio2Tool SELECT/FILL Factorial 128 Roster V1

This directory freezes the fresh 128-row, 16-per-tier discovery roster for the prospectively
named `Y00`, `Y01`, `Y10`, and `Y11` SELECT/FILL factorial. The same rows also bind the external
`DIRECT_M0` and `JOINT_ONE_CALL` references. The roster is drawn only from the frozen 400-row
evaluation proposal and does not register or consume a test or confirmatory split.

`build_roster.py` performs an identity-only projection over the mixed carrier manifests. It emits
no task text or annotation field and never invokes a gold loader. It excludes all 608 sample
identities already registered by the strict Audio2Tool receipt loader, every prior-roster query
block and normalized-token class, and every construction query block and normalized-token class.
It then enforces global sample, query-block, and normalized-token-class uniqueness within the new
roster.

The frozen receipt has SHA-256
`6b07abc516f3fa43ad62e25eb642a4cbdf6ea0ebfac031852ed613c2b2d46a23` and split identity
`44d6176042ad1760bb1c7f27d5df40f2beb9f6e690c1b63e6b61800211140d0d`. Before internal
equivalence deduplication, 186 candidates remained eligible: 23 in tier 1, 24 in tiers 2 through
7, and 19 in tier 8. The selected media total 719.309 seconds.

Roster construction made zero model, embedding, tokenizer, scorer, network, and audio-decoder
contacts. The builder verifies the frozen partition, prior-roster bytes, carrier lock, every WAV
hash and header duration, and refuses to overwrite an existing receipt.
