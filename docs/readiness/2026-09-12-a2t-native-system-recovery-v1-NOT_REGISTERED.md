# Audio2Tool native system power recovery candidate

Status: **NOT_REGISTERED**. This is a configuration-only candidate from frozen
source commit `cbc53ac0c36bed94fdb50c3b069a74569d935720`. It does not authorize model,
tokenizer, service, GPU, scoring, or generation contact. No execution plan or
exposure registration is included. Root must complete manual admission before
using any live command below.

## Candidate boundary

Campaign `SAEA-A2T-NATIVE-SYSTEM-RECOVERY-V1` is the same-roster, full three-arm
recovery. The generation run IDs are:

- `SAEA-A2T-NATIVE-SYSTEM-RECOVERY-DIRECT-V1`, target/cap 4,000/4,200;
- `SAEA-A2T-NATIVE-SYSTEM-RECOVERY-STAGE-CONTROL-V1`, target/cap 8,000/8,400;
- `SAEA-A2T-NATIVE-SYSTEM-RECOVERY-KNOWLEDGE-V1`, target/cap 8,000/8,400.

All cells remain `held`. They use resident session
`serving-a2t-native-system-recovery-np3-v1`. The model and dataset fragments
remain `q4km-mmproj-free-a2t-native-system-np3-v1` and
`audio2tool-org1-union-4000`: decoder-only, no mmproj, c98304/np3, 32,768 tokens
per slot, max1024, the 4/3 fit multiplier, the existing exposed 4,000-row split,
and a whole-roster phase barrier. Task programs, prompts, knowledge values,
ranking/fusion settings, packet identity, and vector identity are unchanged.

The only baseline differences are fresh live-fit run/attempt IDs for every arm
and removal of the old knowledge `prepared_phase_recall` pin. The only
experiment differences are fresh cell/run/attempt/experiment IDs, the new
resident session ID, an explicit `prompt-fit` preparation stage, and held
`NOT_REGISTERED` readiness. Fresh per-arm budgets, population, split identity, source
receipts, and task-facing values are unchanged.

## Receipt reuse and required rebinding

Reuse these source artifacts and receipts byte for byte:

- packet promotion `prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json`,
  SHA-256 `720d81f63a1923f19893c0ee171e1ab7b47f9a946c1e62a06bdddd839243de8a`;
- query-encoding closure `coordination/a2t-query-encoding-root-closure-v1.json`,
  SHA-256 `8127de087876b43a22ba26f0564a61b8e00619148a5c664e19d09556c46da91d`;
- native-key closure `coordination/a2t-native-key-root-closure-v1.json`, SHA-256
  `95b74158f1c5356288e5a42c6a0012e7a38957a3618a2d3e7ef7af792a4e42cd`;
- sealed key facets SHA-256
  `567642452ec2b0ae2a3d23036ba296c79542f7fed1d5bd949da3aba1435a52dd`,
  segmented speech queries SHA-256
  `c7680bc52afeb4096649376c611dafe392935533044ad5d7de3ea4aa3ac1be4f`,
  and native knowledge snapshot semantic SHA-256
  `ccf5d93f14afa2393fc3e988a1e00c877c73e48b13b9ca0c6bde2f390093d276`;
- the existing model fragment and its pinned runtime/model/build receipts.

Do not reuse the old campaign recall, any old actual-request fit receipt, the
old resident session receipt, wire verdict, scientific eligibility receipt,
execution plan, or exposure registration. Those are operationally bound to the
old composed configuration, old process/session, or old run IDs.

Prepare a fresh model-free knowledge recall at
`prepared/SAEA-A2T-NATIVE-SYSTEM-RECOVERY-KNOWLEDGE-CAMPAIGN-PREPARE-V1/recall.json`.
Then add its relative path and file SHA-256 under
`prepared_phase_recall.solve` in
`configs/baseline/a2t-native-system-recovery-knowledge-v1.json`. Preparation
input hashing deliberately excludes only this receipt pin and readiness, so
the newly created receipt remains valid after the pin and final readiness
requirements are added. Recompose after that edit. All three full actual-request
fit receipts must then be produced under the fresh fit run IDs and the final
registered configuration; the 12,001/24,002/24,002 fit contact caps remain.

## Root-only commands after review

Use the literal checkout source and no editable install:

```bash
RECOVERY_REPO=/home/chao/saea-worktrees/a2t-native-power-recovery-v1
SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
DATASET_LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHON=/home/chao/.venvs/speechrl/bin/python
export RECOVERY_REPO SPEECHRL_DATA_DIR DATASET_LOCK PYTHON
export PYTHONPATH="$RECOVERY_REPO/src"
export PYTHONDONTWRITEBYTECODE=1
```

The pre-registration, model-free recall command is:

```bash
mkdir -p "$SPEECHRL_DATA_DIR/prepared/SAEA-A2T-NATIVE-SYSTEM-RECOVERY-KNOWLEDGE-CAMPAIGN-PREPARE-V1"
"$PYTHON" "$RECOVERY_REPO/scripts/flights/run_campaign.py" prepare-phase-recall \
  --repo-root "$RECOVERY_REPO" --data-root "$SPEECHRL_DATA_DIR" \
  --runtime-root /home/chao --lock-path "$DATASET_LOCK" \
  --experiment a2t-native-system-recovery-knowledge-v1 \
  --cell a2t-native-system-recovery-knowledge-v1 --phase solve --workers 20 \
  --output "$SPEECHRL_DATA_DIR/prepared/SAEA-A2T-NATIVE-SYSTEM-RECOVERY-KNOWLEDGE-CAMPAIGN-PREPARE-V1/recall.json"
```

After recall rebinding, final composition, root eligibility, execution plans,
and exposure rows are committed, root may start the one resident wrapper and
launch the shared campaign. The fresh actual-request fit occurs ON that service
at each full-roster live phase barrier, including phase two only after fresh
phase-one state exists; it cannot be completed before service startup:

```bash
bash "$RECOVERY_REPO/scripts/serving_session.sh" start \
  q4km-mmproj-free-a2t-native-system-np3-v1 \
  --session-id serving-a2t-native-system-recovery-np3-v1 \
  --runtime-root /home/chao --host 127.0.0.1 --port 8090

"$PYTHON" "$RECOVERY_REPO/scripts/flights/run_campaign.py" campaign \
  --repo-root "$RECOVERY_REPO" --data-root "$SPEECHRL_DATA_DIR" \
  --runtime-root /home/chao --lock-path "$DATASET_LOCK" \
  --campaign-plan "$RECOVERY_REPO/configs/campaign/a2t-native-system-recovery-v1.json" \
  --owner ROOT_OWNER --expected-session-id serving-a2t-native-system-recovery-np3-v1
```

Keep the serving wrapper in a root-owned live shell. Replace `ROOT_OWNER` only
with the identity used in the manually registered recovery. The current held
configuration refuses campaign execution.

## Root cumulative accounting update

The fresh per-arm targets/caps are unchanged. The family budget now carries prior consumed usage plus the fresh full-pass allowance; the exact pinned basis is DATA/coordination/a2t-native-system-recovery-cumulative-budget-v1.json. It records 15,864 prior generation contacts, 48,004 prior fit contacts, and 92,897.6323333201 prior charged speech seconds. The GPU budget conservatively carries the entire original allocation-to-stop wall interval in addition to the new 10-hour allowance, while reporting the sampled utilization integral separately. This candidate remains NOT_REGISTERED until root finishes admission.


## Root admission successor

This candidate snapshot was superseded by root registration on 2026-09-12. The six execution plans are in docs/readiness/2026-09-12-a2t-native-system-recovery-v1/. DATA coordination/a2t-native-system-recovery-registration-summary-v1.json (SHA-256 7eef2e239f56a675e693fdd862aae4561cd45b8adabb79165baca17b15bc9f59) pins the successor wire and eligibility receipts and final composed identities. All three cells are now ready for the sole manually reviewed recovery; complete actual-request fitting remains mandatory at each live phase barrier. This update grants no effectiveness conclusion and does not rewrite the original terminated campaign.
