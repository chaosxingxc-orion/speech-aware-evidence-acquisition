# E21 offline direct registration readiness

This registration prepares the direct first stage of the prospectively fixed offline direct-then-KC-E1f pipeline. It preserves the full 44-call discovery roster, all 1,593 fixed 90-second windows, the direct-only shared EvidenceAgentController/OpenJiuwen path, the existing formal packets, decoder-only c36864/np4 geometry, and max_tokens 1024.

The composed configuration hash is `4ef7e13d242bf2a87d1ab4b82fff4876560adf52ee67294235f2262597239b98`. The protocol hash is `d3eb7feff5ce46a0845c925734fb37bd2ca945f331936d5394843e03ff9678b4`. Both fit and generation use session `serving-e21-offline-direct-repair-np4-v1`. The fit registers exactly 4,780 endpoint contacts. Generation targets 1,593 requests within a 1,750-call, 2.0 GPU-hour, 150,000-speech-second ceiling.

The fit cell is READY after the terminal full-roster synthetic wire; generation remains HELD. The root admission below supersedes the earlier conditional wording. Root may make the fit cell ready only after the already-running full-roster model-free wire terminates successfully and publishes its immutable terminal evidence. Root may make generation ready only after the complete actual-request fit passes at this unchanged geometry, its result is hash-pinned, and a separate generation admission is recorded. This document does not assert either event occurred.

After those gates close, the shared fit command is:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-fit/src \
/home/chao/.venvs/speechrl/bin/python -m speech_aware_evidence_acquisition.core.flight.cli coordinate-fit \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-fit \
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
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-fit/src \
/home/chao/.venvs/speechrl/bin/python -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-fit \
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
PYTHONPATH=/home/chao/saea-worktrees/e21-offline-direct-fit/src \
/home/chao/.venvs/speechrl/bin/python \
  /home/chao/saea-worktrees/e21-offline-direct-fit/scripts/flights/bind_window_predecessor.py \
  --manifest /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1/attempt-e21-offline-direct-generation-v1/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1.run-manifest.json \
  --repo-root /home/chao/saea-worktrees/e21-offline-direct-fit \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --contract /home/chao/saea-worktrees/e21-offline-direct-fit/docs/readiness/2026-09-10-e21-offline-system-v1/direct-parent-contract-v1.json \
  --receipt /home/chao/saea-worktrees/e21-offline-direct-fit/docs/receipts/e21-predecessor-offline-direct-generation-np4-v1.json \
  --exposure-row SAEA-E21-MF-OFFLINE-DIRECT-PREDECESSOR-BINDING-V1
```

The contract fixes the 44 sample IDs and all 1,593 exact window indices and bounds from the authoritative prepared inventory. The builder must reproduce the sealed stitched outputs, costs, saturation count, and source identities before emitting the DATA-confined snapshot and content-free repository receipt. The frozen repair template remains byte-identical at SHA-256 `497131a4e6defc06d1cc638281dfb0691f9390c50ca4079e6fae491d7a8382e3`; its successor may fill only the new predecessor receipt path and measured SHA-256. The analysis plan remains byte-identical at SHA-256 `8b92393cb37632b7fc53fbb35686d0aef63f845b199bd5de39127e5702ccd5f5`.

Root pre-contact correction: set the existing shared window_preparation_workers to8 (the draft omitted it and inherited serial preparation) and prompt_fit_multiple to2.0. No runtime code change or new test framework is required. The running model-free proof remains frozen on its original source; its single-worker materialization preserves the same roster order. The actual upcoming full fit checks the new composed request identity before generation.

## Generation admission

Root admission on 2026-09-11 supersedes the earlier generation hold. Complete fit SHA-256 7ffb27a3ea6409bd85a451ec60140c1df842fb4d309b125a580c2d37c1f848d1 covers all 1593 requests, exactly 4780 endpoint contacts, no generation, and minimum margin 4704 tokens with 2x output reserve. Generation source: /home/chao/saea-worktrees/e21-offline-direct-generation. Generation config 070eebc006e5eeefe35261b4739756fc6ce90bb92d6efcd8b2bfa734f7c1fef1; protocol a292b3978250e797a18591b479506e876a95faa23329be3f5e1b9091543321c4. The completed fit retains its original plan, source and protocol; its inputs are unchanged by receipt/readiness binding.
