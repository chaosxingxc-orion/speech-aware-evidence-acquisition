#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Usage: plan_gates_mint.sh <default-plan-lock|default-plan-lock-replicate> [mint]
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
PY=/home/chao/.venvs/speechrl/bin/python
DATA=$SAEA_DATA_ROOT
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN:$MAIN/src SPEECHRL_DATA_DIR=$DATA
NAME=$1; MODE=$2
cd $MAIN || exit 1
rc=0
for c in finite_completion_policy_check results_ledger_check harness_admission_check engineering_base_check tool_catalog_check; do out=$($PY -B scripts/checks/$c.py 2>&1); r=$?; echo "$c: exit $r :: $(echo "$out" | grep -v '^ok' | tail -1 | cut -c1-140)"; [ $r -ne 0 ] && rc=1; done
$PY -B -m pytest -q -p no:cacheprovider tests/unit/test_default_plan_lock_cells.py tests/unit/test_config_table_module_switches.py 2>&1 | tail -1
echo "== compose + load the new cells through the loader"
$PY - "$NAME" <<'PY'
import json, io, sys
from pathlib import Path
name = sys.argv[1]
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.core.config import compose
for p in (f"configs/experiment/slurp-native-{name}-v1.json", f"configs/experiment/slurp-native-{name}-smoke-4-v1.json"):
    e = json.load(io.open(p, encoding="utf-8")); c = e["cells"][0]
    composed = compose(Path("."), c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], p.split("/")[-1][:-5])
    d = composed.values; cfg = load_native_episode_config(d, default_phase_program(d["policy"]))
    print(p.split("/")[-1], "loads | phase_tools:", "phase_tools" in d, "| normaliser:", d["native_episode"].get("deliver_normaliser"), "| review_loop:", d["native_episode"].get("review_loop"), "| slot store:", d["knowledge_stores"]["slot-contracts"]["release"]["relpath"].split("/")[-2])
PY
[ $? -ne 0 ] && rc=1
if [ "$MODE" = "mint" ]; then
echo "== mint the decision receipt from B1-notool's"
$PY - "$DATA" "$NAME" <<'PY'
import json, io, sys, os, hashlib
from datetime import datetime, timezone
DATA, name = sys.argv[1], sys.argv[2]
tag = name.upper()
src = f"{DATA}/coordination/slurp-b1-notool-v1/root-admission-v1.json"
d = json.load(io.open(src, encoding="utf-8"))
s = json.dumps(d)
for a, b in [
    ("slurp-b1-notool-admission-v1", f"slurp-{name}-admission-v1"),
    ("SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-SMOKE-4-FIT-V1", f"SAEA-SLURP-NATIVE-{tag}-SMOKE-4-FIT-V1"),
    ("SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-SMOKE-4-V1", f"SAEA-SLURP-NATIVE-{tag}-SMOKE-4-V1"),
    ("SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-FIT-V1", f"SAEA-SLURP-NATIVE-{tag}-FIT-V1"),
    ("SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1", f"SAEA-SLURP-NATIVE-{tag}-V1"),
    ("slurp-native-exemplars-k20-notool-smoke-4-v1", f"slurp-native-{name}-smoke-4-v1"),
    ("slurp-native-exemplars-k20-notool-v1", f"slurp-native-{name}-v1"),
    ("slurp-native-anchor-exemplars-k20-notool-smoke-4-v1", f"slurp-native-{name}-smoke-4-baseline-v1"),
    ("slurp-native-anchor-exemplars-k20-notool-v1", f"slurp-native-{name}-baseline-v1"),
    ("docs/readiness/2026-09-20-slurp-b1-notool-v1", f"docs/readiness/2026-09-22-slurp-{name}-v1"),
    ("coordination/slurp-b1-notool-v1", f"coordination/slurp-{name}-v1"),
]:
    s = s.replace(a, b)
n = json.loads(s)
rep = name.endswith("replicate")
n["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
n["decision"] = ("Admit cell PLAN: the four-row smoke and the 1,080-row TRAIN Fold A arm of the SLURP default plan flown as one arm -- the sealed tool-free B1 fragment plus the plan's decided keys (slot-contracts v2, the delivery normaliser node, the review-loop marker) -- the decision-30 v2.0 lock evidence (decision 57 option b); read against the sealed B1-notool arm at B1r's own-null margins, with the lock comparison beside B5e + node (63.78 / 81.85); locked only once cell PLANr replicates it."
                 if not rep else
                 "Admit cell PLANr: the four-row smoke and the 1,080-row TRAIN Fold A request-identical replicate of cell PLAN under its own run id -- the plan's own null (decision 38) and the decision-30 lock replication; read against the sealed PLAN arm.")
n["authorization_basis"] = "Owner decisions 30 (lock trigger (b) fired 2026-09-20), 38 (own-null margins), 57 (option b: the plan flown is the plan locked), 58 (script-derived registrations), 75 (frontier row), 77 (flown only through the scheduled-task queue), 78 (the seal path: plan arm, replicate, B9a, DEV-2000; no G2; np4 stays), 25, 28."
root = "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/"
def rehash(x):
    if isinstance(x, dict):
        if "path" in x and isinstance(x["path"], str) and os.path.exists(root + x["path"]):
            x["sha256"] = hashlib.sha256(io.open(root + x["path"], "rb").read()).hexdigest()
        for v in x.values(): rehash(v)
    elif isinstance(x, list):
        for v in x: rehash(v)
rehash(n)
if "budget" in n and isinstance(n["budget"], dict):
    for arm in ("arm", "smoke"):
        if arm in n["budget"] and isinstance(n["budget"][arm], dict):
            n["budget"][arm]["native_task_contract_calls_cap"] = 0
            if arm == "arm": n["budget"][arm]["expected_contacts"] = 4320; n["budget"][arm]["expected_gpu_hours"] = 1.7
n["claim_boundary"] = "The plan arm on a discovery roster against the sealed B1-notool arm at B1r's own-null margins, with the lock comparison reported and never gated; no DEV1000, Fold B, test-split or paper-scale claim; development numbers (decision 28)."
os.makedirs(f"{DATA}/coordination/slurp-{name}-v1", exist_ok=True)
out = f"{DATA}/coordination/slurp-{name}-v1/root-admission-v1.json"
io.open(out, "w", encoding="utf-8").write(json.dumps(n, indent=2) + "\n")
print("minted", out, "| decision_id", n.get("decision_id"), "| eligible", n.get("eligible_run_ids"))
PY
fi
exit $rc
