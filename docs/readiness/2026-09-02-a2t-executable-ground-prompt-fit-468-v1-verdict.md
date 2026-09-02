# A2T executable-ground prompt-fit 468 v1 verdict

Date: 2026-09-02. Experiment: `SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-468-V1`.
Verdict: **PASS — THE COMPLETE 468-TOKEN PACKET ENVELOPE FITS WITH 17,678 TOKENS OF MARGIN**.

The source hashes, 104-row packet inventory, promotion binding, serving geometry, two message
identities, handbook metadata, and runtime identity all verified. Replacing only the speech reserve
from 455 to 468 increases each prompt by exactly 13 tokens:

- `ground-direct`: 12,557 text + 468 speech + 2 special = 13,027 prompt tokens; with 1,024
  completion tokens, 14,051 are required.
- `ground-agent-observed`: 12,572 text + 468 speech + 2 special + 1,024 bounded observation =
  14,066 prompt tokens; with 1,024 completion tokens, 15,090 are required.

The second envelope is worst and leaves `32,768 - 15,090 = 17,678` tokens. No handbook byte,
message, observation bound, completion allowance, slot geometry, model, or runtime changed.

Result SHA-256:
`277f5147b8ce1ac9acca538e4b8a83a2c5b282c62f278afd56e27c9fd61a2fd5`.
The run used zero model, tokenizer, audio-decode, network, retriever, embedding, scorer, paid-API, or
GPU contacts, with zero outbound attempts and an empty target list. Gold, labels, query text, task
responses, scores, rewards, protected unexposed data, and test annotations remained unopened.

Two pre-result invocations stopped because the runner tested the guard counter object itself for
truth; that object is always truthy even when `count=0`. Both stops wrote no result and recorded zero
outbound attempts. The runner was corrected prospectively to inspect `.count` and `.targets`; no
source, arithmetic, threshold, envelope, or pass condition changed.

Passing opens only separately preregistered ground-qualification implementation and zero-contact
preflight. Task model contact remains closed until those bindings land cleanly. Candidate pruning,
training-free control, approximately-1,000 scale, baseline change, test access, Stage-3, and paper-
scale work remain closed. Network-jitter and retry-stress testing remain out of scope.
