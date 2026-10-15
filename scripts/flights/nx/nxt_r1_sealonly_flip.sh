#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# NX-T R1 SEAL-ONLY completion of the stopped column flight (owner decision 320 A, proposed): flip the seal-only cell to ready on master, model-free, in LOOP FORM --
# converged at ONE HEAD, which becomes the flight commit of batch_chain_nxt_r1_sealonly.sh. Run it through the ext4 package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/nxt_r1_sealonly_flip.sh" \
#     --package docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1 \
#     --cells slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1-sealonly --pins-commit-msg /home/chao/nxt1seal-pins-commit.txt
#
# Root runs this ONLY after, in order:
#   1. countersigning the seal-only clauses on the arm's generation and FIT rows and the row SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SEALONLY-REPLAY-PROOF-V1
#      (countersign-row-texts-v1.json in the package);
#   2. minting $DATA/coordination/slurp-nxt-r1-thinking-policy-fold-b-v1/root-admission-sealonly-v1.json with scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py
#      (decision id slurp-nxt-r1-thinking-policy-fold-b-sealonly-admission-v1).
# ROSTER NARROWING: the seal-only cell's roster is the stopped attempt's COMPLETE rows (a strict subset of Fold B), so the cell's own first-phase supply, rebuilt model-free
# under the same run id, legitimately differs from the 1,080-row parent's: ALLOW_OUTPUT_CHANGE=1 is the roster-narrowing precedent (scripts/flights/batch/roll1_repin_arm.sh).
# The seal-only path never reads the supply. This is the ONLY flip of the NX-T family that passes it.
# CLI HAZARD: this runs core.flight.cli check at the end (repin_cell_generic.sh, ARM=1); run it only while NO flight is alive and, per the coordinator, with batch-STOP
# parked (the batch chain refuses while it exists).
#
# Loop form (a later flip may rewrite the shared exposure ledger after an earlier cycle reported "satisfied"): the cycle is re-run until a whole pass commits nothing,
# bound 4. Only then is HEAD recorded. Untracked files count as dirt.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/nx
PY=${SAEA_PY:-/home/chao/.venvs/speechrl/bin/python}
cd "$MAIN" || exit 1
# The identities come from the family (never a literal here).
eval "$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MAIN/src" $PY -B -c "
import sys; sys.path.insert(0, '$DIRD'); import nxt_r1_family as f
s = f.sealonly_spec()
print('RRD=%s CELL=%s PKGN=%s PREREG=%s DEC_PATH=%s DEC_ID=%s FLIGHT_FILE=%s' % (s['package'], s['cell'], f.PKG_NAME, s['preregistration'], s['decision_relpath'], s['decision_id'], f.SEALONLY_FLIGHT_COMMIT_FILE))
")" || { echo "cannot read the seal-only identities from the family"; exit 66; }
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
# Environment for scripts/flights/batch/repin_cell_generic.sh (inherited through repin_loop_generic.sh on every pass).
export RD=$RRD CELL EXP=$CELL PKG=$PKGN PREREG DEC_PATH DEC_ID
export TAG=nxt1seal ARM=1
export MSG=/home/chao/nxt1seal-commit.txt
export ALLOW_OUTPUT_CHANGE=1

# Preconditions: the predecessor trace untouched and its attempt ABORTED, the seal-only attempt and its FIT identity unopened, the roster document matching the cell, the
# replay proof registered clean, the receipt minted, both arm rows unconsumed and their seal-only clauses countersigned.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MAIN/src" $PY -B - "$MAIN" "$DATA" "$DIRD" <<'PY' || exit 6
import hashlib, json, sys
from pathlib import Path
main, data, dird = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, dird)
import nxt_r1_family as fam
S = fam.sealonly_spec()
RUN, FIT_RUN, PRED, SO, FSO = S["run"], S["fit_run"], S["predecessor_attempt"], S["attempt"], S["fit_attempt"]
problems = []
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
exp = load(main / f"configs/experiment/{S['experiment']}.json")
cell = exp["cells"][0]
resume = cell.get("resume_from") or {}
if cell["attempt_id"] != SO:
    problems.append(f"the seal-only cell declares attempt {cell['attempt_id']!r}, not the seal-only attempt")
if set(resume) != {"attempt_id", "trace_sha256"} or resume.get("attempt_id") != PRED:
    problems.append("the seal-only cell's resume_from is not a mode-A pin of the stopped attempt")
if "seal-only" not in cell["allowed_execution_stages"] or "campaign" in cell["allowed_execution_stages"] or "worker" in cell["allowed_execution_stages"]:
    problems.append("the seal-only cell's allowed stages are not check / prepare-supply / seal-only")
rows = load(main / S["complete_rows"])
ids = [i["sample_id"] for i in rows["items"]]
if exp["populations"][0]["ids"] != ids or exp["population"]["count"] != len(ids) or exp["population"]["split_identity_hash"] != rows["split_identity_hash"]:
    problems.append("the experiment's population is not the complete-rows document's roster")
trace = data / f"runs/{RUN}/{PRED}/{RUN}.trace.jsonl"
if not trace.is_file() or sha(trace) != resume.get("trace_sha256"):
    problems.append("the stopped attempt's trace is missing or no longer hashes to the registered resume_from")
attempt_file = data / f"attempts/{RUN}/{PRED}.json"
if load(attempt_file).get("state") != "ABORTED":
    problems.append("the stopped attempt is not ABORTED")
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/{FIT_RUN}/{FSO}"):
    if (data / path).exists():
        problems.append(f"{path} already exists: the seal-only attempt or its FIT identity is not fresh")
plan = load(main / S["package"] / "generation-plan-registered-v1.json")
proof = plan.get("resume_replay_proof") or {}
n = len(ids)
if (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice"), proof.get("union_complete_rows")) != (n, 0, 0, n):
    problems.append(f"the registered resume_replay_proof is not {n} / 0 / 0: {proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')}")
receipt_path = data / S["decision_relpath"]
if not receipt_path.is_file():
    problems.append("the seal-only decision receipt root-admission-sealonly-v1.json is not minted")
else:
    receipt = load(receipt_path)
    if receipt.get("status") != "decided" or receipt.get("decision_id") != S["decision_id"]:
        problems.append("the seal-only receipt is not a decided " + S["decision_id"])
    if RUN not in receipt.get("eligible_run_ids", []) or SO not in receipt.get("eligible_attempt_ids", []):
        problems.append("the seal-only receipt does not list the arm run id and the seal-only attempt as eligible")
ledger = (main / "docs/exposure-ledger.md").read_text(encoding="utf-8")
for run in (RUN, FIT_RUN, S["proof_run"]):
    found = [ln for ln in ledger.split("\n") if ln.startswith("|") and f"| {run} |" in ln]
    if run == S["proof_run"]:
        if len(found) != 1 or "countersignature pending" in found[0]:
            problems.append(f"{run}: the replay-proof row is missing or still a DRAFT")
        continue
    if len(found) != 1 or found[0].split("|")[9].strip().lower() != "no":
        problems.append(f"{run}: the completion needs exactly one row reading consumed = no")
    elif "SEAL-ONLY COMPLETION REGISTERED" not in found[0]:
        problems.append(f"{run}: the seal-only clause is not on the row")
    elif "countersignature pending" in found[0].split("SEAL-ONLY COMPLETION REGISTERED", 1)[1][:200]:
        problems.append(f"{run}: the seal-only clause is still a DRAFT (root countersignature pending)")
for problem in problems:
    print("refusing to flip the NX-T R1 seal-only completion:", problem)
sys.exit(1 if problems else 0)
PY

printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' "research: flip the NX-T R1 SEAL-ONLY completion to ready (owner decision 320 A as proposed: the same run id SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1 under the seal-only attempt, resume_from the stopped rec1 column attempt by trace sha256, the roster fixed to its complete rows; zero new model contacts; narrowed supply re-pinned with --allow-output-change; decision receipt slurp-nxt-r1-thinking-policy-fold-b-sealonly-admission-v1)" > "$MSG"

CYCLES=(
  "$SP/repin_cell_generic.sh $RRD $CELL generation $MSG"
)
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash $SP/repin_loop_generic.sh $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
[ -z "$(git status --short)" ] || { echo "tree not clean after convergence (untracked files count): $(git status --short | head -3)"; exit 5; }
echo "$CONVERGED" > "$FLIGHT_FILE"
echo "flight commit $CONVERGED (the NX-T R1 seal-only cell ready at it)"
