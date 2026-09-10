# E21 offline direct registration readiness

This registration prepares the direct first stage of the prospectively fixed offline direct-then-KC-E1f pipeline. It preserves the full 44-call discovery roster, all 1,593 fixed 90-second windows, the direct-only shared EvidenceAgentController/OpenJiuwen path, the existing formal packets, decoder-only c36864/np4 geometry, and max_tokens 1024.

The composed configuration hash is `28ef61c5cc0baa88df184e3d8696b101dc99060f7a36565676ec32d5c8a70577`. The protocol hash is `dbce17e3d28e6b53f9df10d2d61e0deb9d297eca0b005ed5cddfde93d72e1da7`. Both fit and generation use session `serving-e21-offline-direct-repair-np4-v1`. The fit registers exactly 4,780 endpoint contacts. Generation targets 1,593 requests within a 1,750-call, 2.0 GPU-hour, 150,000-speech-second ceiling.

Both cells remain HELD. Root may make the fit cell ready only after the already-running full-roster model-free wire terminates successfully and publishes its immutable terminal evidence. Root may make generation ready only after the complete actual-request fit passes at this unchanged geometry, its result is hash-pinned, and a separate generation admission is recorded. This document does not assert either event occurred.

After those gates close, the shared fit command is:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-registration/src \
/home/chao/.venvs/speechrl/bin/python -m speech_aware_evidence_acquisition.core.flight.cli coordinate-fit \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-registration \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --runtime-root /home/chao \
  --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
  --experiment e21-offline-direct-kc-e1f-packets-np4-v1 \
  --cell e21-offline-direct-fit-v1 \
  --owner root \
  --expected-session-id serving-e21-offline-direct-repair-np4-v1 \
  --output /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-E21-OFFLINE-DIRECT-FIT-NP4-V1/request-fit.json \
  --contact-cap 4780
```

After fit and admission, root creates the standard lease token. The attach-only generation command is:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-registration/src \
/home/chao/.venvs/speechrl/bin/python -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-registration \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --runtime-root /home/chao \
  --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
  --experiment e21-offline-direct-kc-e1f-packets-np4-v1 \
  --cell e21-offline-direct-generation-v1 \
  --expected-session-id serving-e21-offline-direct-repair-np4-v1 \
  --lease-token-file /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/<root-issued-generation-lease-token>.json
```

When the parent seals and verifies, and before any quality or reference read, build its model-free predecessor through the existing shared entry point:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-registration/src \
/home/chao/.venvs/speechrl/bin/python \
  /home/chao/saea-worktrees/e21-offline-direct-registration/scripts/flights/bind_window_predecessor.py \
  --manifest /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1/attempt-e21-offline-direct-generation-v1/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1.run-manifest.json \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-registration \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --contract /home/chao/saea-worktrees/e21-offline-direct-registration/docs/readiness/2026-09-10-e21-offline-system-v1/direct-parent-contract-v1.json \
  --receipt /home/chao/saea-worktrees/e21-offline-direct-registration/docs/receipts/e21-predecessor-offline-direct-generation-np4-v1.json \
  --exposure-row SAEA-E21-MF-OFFLINE-DIRECT-PREDECESSOR-BINDING-V1
```

The contract fixes the 44 sample IDs and all 1,593 exact window indices and bounds from the authoritative prepared inventory. The builder must reproduce the sealed stitched outputs, costs, saturation count, and source identities before emitting the DATA-confined snapshot and content-free repository receipt. The frozen repair template remains byte-identical at SHA-256 `497131a4e6defc06d1cc638281dfb0691f9390c50ca4079e6fae491d7a8382e3`; its successor may fill only the new predecessor receipt path and measured SHA-256. The analysis plan remains byte-identical at SHA-256 `8b92393cb37632b7fc53fbb35686d0aef63f845b199bd5de39127e5702ccd5f5`.

Root pre-contact correction: set the existing shared window_preparation_workers to8 (the draft omitted it and inherited serial preparation) and prompt_fit_multiple to2.0. No runtime code change or new test framework is required. The running model-free proof remains frozen on its original source; its single-worker materialization preserves the same roster order. The actual upcoming full fit checks the new composed request identity before generation.
