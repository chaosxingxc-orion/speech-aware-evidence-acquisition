# STATUS-167: exact source rendering repair accepted on CPU

The previous turn completed the v3 file handoff (f26f46d0). This turn made concrete
engineering progress: source commit 23b4ec0eade972f98d961442dd7856c9fa87ec2c reproduces and
fixes the candidate-view proof's plain-versus-prefixed source representation mismatch.
It is integrated by fast-forward into canonical master. No failed source was edited.

Root reproduced the failure through the actual composed config, released 54-card source
and shared task-contract-only renderer. The narrow fix preserves exact body/URI/ID binding,
preserves plain or named representation, and records source_representation.
Root ran 46 distinct focused tests; the delegated adjacent set passed 89 tests.
Coverage of both slot-view modules is 87.08%. Engineering/Ruff/diff checks pass.
The real-source synthetic-scope check passes 108 views with unchanged canonical sources.
No model, tokenizer, speech tool or official scorer was contacted.

Read [the additive repair handoff](../../../handoff/2026-09-16-fable51/RENDERING-REPAIR-UPDATE-v1.md)
and [the concrete proposal](../../../readiness/2026-09-16-candidate-slot-rendering-fresh-proof-proposal-v1.md).
The owner was asked to admit at most one new four-row engineering proof, because the
previous proof explicitly stops after its first failure and permits no retry under that
identity. No response/admission is recorded in this status.

Current failed attempt remains ABORTED; typed-context remains closed after its second
failure; held direct quality remains unread; Fable takeover is not acknowledged.
No full scientific comparison or new GPU experiment is launched by this update.
\nFresh held configs and model-free prepared supply are complete. Cache revalidation\nreturned warm with unchanged output hash. Live admission still awaits the owner response.\n