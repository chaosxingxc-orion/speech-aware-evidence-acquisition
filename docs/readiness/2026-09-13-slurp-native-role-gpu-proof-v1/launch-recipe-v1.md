# Root launch recipe

Run these public shared entries only after root has reviewed and registered the exposure rows. The two plans bind the shared runtime execution-plan protocol SHA-256 `c2c26d0e73e26c9144ab745e045732d9220843099a59e543c874d31bb6c4fbdc`. Do not run a standalone coordinate-fit command: the native gate fits each realized request inside generation.

Set `REPO` to the clean checkout containing the registered commit and `DATA` to the configured speech data root. The umbrella lock is `/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json`.

```bash
cd "$REPO"
SPEECHRL_DATA_DIR="$DATA" bash scripts/serving_session.sh start \
  q4km-mmproj-free-slurp-native-role-gpu-proof-np8-max256-v1 \
  --session-id serving-slurp-native-role-gpu-proof-np8-v1 \
  --host 127.0.0.1 --port 8080 --runtime-root /home/chao
```

In a separate root-owned terminal, issue the attach-only worker lease. Keep that terminal open until explicit release.

```bash
cd "$REPO"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
  --experiment slurp-native-role-gpu-proof-v1 --cell slurp-native-role-gpu-proof-v1 \
  --owner root-slurp-native-role-gpu-proof-v1 \
  --expected-session-id serving-slurp-native-role-gpu-proof-np8-v1 \
  --token-output coordination/slurp-native-role-gpu-proof-v1.worker-lease.json
```

After the lease-ready event, launch the worker from the same registered checkout. This invokes `FlightRuntime.run_phases`, whose native gate performs each dynamic fit before dispatch.

```bash
cd "$REPO"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
  --experiment slurp-native-role-gpu-proof-v1 --cell slurp-native-role-gpu-proof-v1 \
  --expected-session-id serving-slurp-native-role-gpu-proof-np8-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-role-gpu-proof-v1.worker-lease.json"
```

Before launch, root records parser-readable 16-column rows in `docs/exposure-ledger.md` for these two identities. Do not copy a reduced table into the ledger: the shared exposure parser requires its full header and row shape.

`SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-FIT-V1` binds `dynamic-fit-plan-v1.json` and at most 176 tokenizer endpoints inside generation, one before each realized request. It authorizes neither a standalone fit run nor generation, scoring, or a new roster.

`SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1` binds `generation-plan-v1.json` and at most 44 frozen-core contacts on the fixed four-row TRAIN roster. Its only local tool class is the Reviewer native task-contract action; accepted output is Solver-only.

The serving process and its session receipt are new after the WSL restart. The pinned runtime build and GGUF receipt are reused unchanged; do not regenerate E0 solely for the boot change.
