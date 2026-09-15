# Earnings21 direct static-fit registration

Status: root-admitted and held pending root's final clean source freeze, the
exact resident service and the exclusive lease. This registration authorizes
only the direct static execution-unit fit. It does not authorize generation,
native fit, ASR, encoding or scoring.

The successor experiment fragment
configs/experiment/e21-native-window-direct-full44-fit-v1.json retains the fit
and future direct-generation cells together. It differs from the held
preparation fragment only in the successor identity, purpose and fit readiness.
The future generation cell remains held. Model, dataset, baseline, task,
decoding, roster, packets, implementation, margin and arm budget are unchanged.

Root admission is
DATA/coordination/e21-native-window-registration-v1/admission-v1.json, SHA-256
de78bb55f4fcb46e0b04432da997dc2ff3c8e5a002d358646f7cdcd0542272e8.
The stable-source review SHA-256 is
bbffc0281efcc3ed3d830a9815393e6cafcd2bdfc6113f92576c84cbcae7d616.

The composed configuration SHA-256 is
d4594775716f9ef45c266e82d7bff584de44f039beb6dc4e4112bdcef773b69d.
The shared runtime protocol SHA-256 is
23ce891d1b9335a4045950e214712a28a072782ee20b83c4b9a7ba7e36d32000.
The protocol document SHA-256 is
ebafb75dc81df62e9cfcc72f14781b103e10b961ce56557c04c6be929790a7f9.
The direct fit plan SHA-256 is
f16e4da9b25bcd43743f5e1adfcfb5380581a766f9c5062fc21252ce0e6a8b16.

The fit uses the existing static execution-unit-aware path over all 1,593
canonical requests. The preparation authorizer replaces the experiment's 1,593
generation-call declaration with the registered 4,780 endpoint cap for this
distinct fit run. The direct fit and future direct generation share the four
GPU-hour and 141,346-speech-second ceilings. The 4/3 fit margin, max1024 output,
four 24,576-token slots and source-bound packet inventory remain unchanged.

Root may use this deferred shared command only after reviewing and freezing the
clean source, starting and verifying
serving-e21-native-window-context-tools-np4-max1024-v1 and its shared monitor,
and acquiring the standard GenerationLease for this exact fit run and attempt.
Root must mint the designated lease-token file from that real GenerationLease
immediately before dispatch and never record or expose its token contents. Pass
that file to the attach-only worker:

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/home/chao/saea-worktrees/e21-native-window-fit-registration-v1/src \
    /home/chao/.venvs/speechrl/bin/python -B -m \
      speech_aware_evidence_acquisition.core.flight.cli prompt-fit \
      --repo-root /home/chao/saea-worktrees/e21-native-window-fit-registration-v1 \
      --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
      --runtime-root /home/chao \
      --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
      --experiment e21-native-window-direct-full44-fit-v1 \
      --cell e21-native-window-direct-full44-fit-v1 \
      --expected-session-id serving-e21-native-window-context-tools-np4-max1024-v1 \
      --lease-token-file /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-native-window-registration-v1/root-fit-lease-token-v1.json \
      --output /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/prepared/SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1/attempt-e21-native-window-direct-full44-fit-v1/request-fit.json \
      --contact-cap 4780

The resident-service coordinate-fit route is not selected because it requires
its own exact monitor-owner receipt. The attach-only prompt-fit path reuses
root's verified shared service, monitor and exclusive lease and performs the
same registered static fit. The command is a handoff recipe, not launch
authority. Stop and preserve the contact record on any refusal or failure. Do
not retry or alter geometry, output, source, fit margin or roster. After a successful fit, root preserves
this source, plan, exposure row and receipt before separately registering any
generation successor.
