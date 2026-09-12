# SLURP cached-observation answering registration skeleton

This directory is a non-runnable preparation aid. It does not register an execution plan, add an exposure row, mark a cell ready, start a service, acquire a lease or authorize a model contact.

The four plan templates in registration-skeleton.json preserve the frozen pair budgets. Each generation plan carries 3,150 calls, 10,500 speech seconds and 2.0 GPU hours for a 3,000-contact target. Each fit plan carries exactly 9,003 endpoint contacts and the same 10,500-second and 2.0-hour per-arm coverage because FlightRuntime derives live fit by replacing only run ID, attempt ID and planned calls on the generation plan. Per-arm fit and generation speech/GPU coverage is shared rather than additive. The pair totals remain 6,300 generation calls, 18,006 fit contacts, 21,000 speech seconds and 4.0 GPU hours.

Both arms use policy phase-task-tools-solve-revise-v1, DEV-1000, max_tokens 256, the same packet and knowledge bindings, and one root-owned decoder-only service: serving-slurp-speech-observation-np4-v1, no mmproj, context 65,536, four slots and 16,384 tokens per slot.

## Finalization sequence

1. Bind the sealed recovery catalog SHA-256 43925fb7e66c378037eaf676ae8e25860bf835ed53d34bac696ee718b54f9073 at the already-frozen recovery relpath and verify the catalog ID, producer identities, finalized attempt, 1,000-row source roster and artifact hashes through the shared loader.
2. Before recall, freeze every identity-bearing field: all four fragment identities; the catalog pin and OBS action; stages; all run, attempt, fit, cell, experiment and service IDs; budgets; max_tokens; plan, solve and revise material; supply, knowledge, packet, prompt and task fields; preservation flags and source receipts. Only prepared_phase_supply, prepared_phase_recall, prepared_request_fit, prompt_fit_receipt, prompt_fit_receipt_sha256 and per-cell readiness are excluded from recall artifact identity and may remain absent.
3. Materialize the treatment fragments and prepare its distinct solve recall with the commands in the treatment README. Bind only the returned prepared_phase_recall.solve pin. Verify 1,000 rows and exact selected IDs and order without changing any identity-bearing field.
4. Add final readiness requirements. Control binds the retained recall and paired root decision. Treatment binds the recovery catalog, its distinct recall, the same paired decision, and depends on the control generation run reaching sealed.
5. Create the two-cell campaign plan in this order: control, treatment. The treatment dependency is required_state sealed. The shared queue may compute control scoring while treatment runs, but paired semantic output remains closed until both arms seal or root records a terminal hold.
6. On the final clean pair source, compose both arms and compute each protocol hash. Fit and generation for one arm use the same composed-config and protocol hashes.
7. Write immutable generation and fit plan documents from the skeleton, then append all four exposure rows to the canonical ledger with consumed=no and plan artifact pins. Recompute the final clean source commit after all committed registration bytes are present.
8. Root starts one attested resident process and launches the shared campaign. Live fit runs automatically at each actual phase barrier under the arm generation lease; there is no separate fit launcher.

## Model-free final identity derivation

Run only after final treatment materialization, recall binding and readiness binding. This command reads configuration files and prints hashes; it contacts no service.

~~~bash
PAIR_REPO=/home/chao/saea-worktrees/slurp-speech-observation-pair-v1
PYTHON=/home/chao/.venvs/speechrl/bin/python
export PAIR_REPO PYTHON
export PYTHONPATH="$PAIR_REPO/src"
export PYTHONDONTWRITEBYTECODE=1

"$PYTHON" - <<'PY'
from pathlib import Path
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

repo = Path("/home/chao/saea-worktrees/slurp-speech-observation-pair-v1")
split_hash = "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
cells = (
    ("control", "slurp-speech-observation-control-v1", "slurp-speech-observation-control-v1"),
    ("treatment", "slurp-speech-observation-whisper-v1", "slurp-speech-observation-whisper-v1"),
)
for label, baseline, experiment in cells:
    composed = compose(
        repo,
        "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64",
        "slurp-speech-native-dev1000",
        baseline,
        experiment,
    )
    print(label, composed.config_hash, protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
PY
~~~

Copy each printed composed hash and protocol hash into both plan documents for that arm. Validate every nested execution_plan through contracts.ExecutionPlan.validate before registration. Do not substitute placeholders or a pre-readiness hash.

## Root-only service and campaign commands

Use the final clean pair source and no editable install. The serving wrapper must remain in a root-owned live shell. Starting the service is permitted only after root completes scientific admission, the four immutable plans and exposure rows, readiness bindings, and the active A2T lease or service handoff.

~~~bash
PAIR_REPO=/home/chao/saea-worktrees/slurp-speech-observation-pair-v1
SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
DATASET_LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHON=/home/chao/.venvs/speechrl/bin/python
export PAIR_REPO SPEECHRL_DATA_DIR DATASET_LOCK PYTHON
export PYTHONPATH="$PAIR_REPO/src"
export PYTHONDONTWRITEBYTECODE=1

bash "$PAIR_REPO/scripts/serving_session.sh" start q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64 --session-id serving-slurp-speech-observation-np4-v1 --runtime-root /home/chao --host 127.0.0.1 --port 8080
~~~

After the resident session record matches the complete required identity, root launches the two-cell campaign from a separate shell. Replace ROOT_OWNER with the identity used in the registered custody record.

~~~bash
"$PYTHON" "$PAIR_REPO/scripts/flights/run_campaign.py" campaign --repo-root "$PAIR_REPO" --data-root "$SPEECHRL_DATA_DIR" --runtime-root /home/chao --lock-path "$DATASET_LOCK" --campaign-plan "$PAIR_REPO/configs/campaign/slurp-speech-observation-pair-v1.json" --owner ROOT_OWNER --expected-session-id serving-slurp-speech-observation-np4-v1
~~~

The campaign worker attaches to the resident. It cannot start, stop or replace the process. Root records and pins serving/serving-slurp-speech-observation-np4-v1/session.json after startup.

## Remaining bindings

The recovery catalog is pinned at SHA-256 43925fb7e66c378037eaf676ae8e25860bf835ed53d34bac696ee718b54f9073. The skeleton intentionally leaves unresolved the treatment recall SHA-256; paired decision path, hash and decision ID; final readiness objects; two final composed hashes and two protocol hashes; final clean pair source commit; four final plan paths and hashes; resident session receipt hash; campaign-plan commit; and root owner identity.

Do not inspect paired semantic results until both complete manifests seal or root records a terminal hold. No private launcher or second answering model is part of this plan.
