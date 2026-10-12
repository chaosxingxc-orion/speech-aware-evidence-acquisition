#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# P-SV-1 SEAL-ONLY completion (owner decision 197): flip the seal-only cell to ready on master, model-free,
# converged at ONE HEAD, which becomes the flight commit of batch_chain_psv1_sealonly.sh.
#
# Root (act delegated by owner decision 197) runs this ONLY after, in order:
#   1. countersigning the seal-only clauses on the arm's generation and FIT rows and the row
#      SAEA-SLURP-STAGE3-PSV1-FOLD-B-SEALONLY-REPLAY-PROOF-V1;
#   2. minting $DATA/coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json with
#      scripts/flights/psv/psv1_sealonly_mint_receipt.py (decision id slurp-stage3-psv1-fold-b-sealonly-admission-v1).
# --allow-output-change is never passed. The rails implementation hashes changed with the I7v fix (they are part of
# every prepared artifact's identity), so the seal-only cell re-pins its inherited supply, whose output must stay
# 81d6a712..., and verifies or rebuilds its branch-seed pin with an unchanged output.
# CLI HAZARD: this runs core.flight.cli check; run it only while a flying campaign's arm is alive with a growing call
# counter, never in the gap between two chain steps of the batch driver.
#
# Loop form (a later flip may rewrite the shared exposure ledger after an earlier cycle reported "satisfied"): the cycle
# is re-run until a whole pass commits nothing, bound 4. Only then is HEAD recorded. Untracked files count as dirt.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
RRD=docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1
# Environment for scripts/flights/batch/repin_cell_generic.sh (inherited through repin_loop_generic.sh on every pass).
export RD=$RRD
export CELL=slurp-native-stage3-psv1-fold-b-v1-resume
export EXP=slurp-native-stage3-psv1-fold-b-v1-resume
export PKG=slurp-stage3-psv1-fold-b-v1
export PREREG=$RRD-preregistration.md
export DEC_PATH=coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json
export DEC_ID=slurp-stage3-psv1-fold-b-sealonly-admission-v1
export TAG=psv1-sealonly ARM=1
export MSG=/home/chao/psv1-sealonly-commit.txt
unset ALLOW_OUTPUT_CHANGE
PY=/home/chao/.venvs/speechrl/bin/python
cd "$MAIN" || exit 1

# Preconditions: the predecessor trace untouched and its attempt ABORTED, the seal-only attempt unopened, the replay
# proof registered clean, the receipt minted, both arm rows unconsumed and their seal-only clauses countersigned.
$PY -B - "$MAIN" "$DATA" <<'PY' || exit 6
import hashlib, json, sys
from pathlib import Path
main, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1"
PRED = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1"
PIN = "0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a"
SO = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-psv1-fold-b-fit-v1-seal-only"
problems = []
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
cell = load(main / "configs/experiment/slurp-native-stage3-psv1-fold-b-v1-resume.json")["cells"][0]
if cell["attempt_id"] != SO:
    problems.append(f"the resume cell declares attempt {cell['attempt_id']!r}, not the seal-only attempt")
if cell.get("resume_from") != {"attempt_id": PRED, "trace_sha256": PIN}:
    problems.append("the resume cell's resume_from is not the registered predecessor")
trace = data / f"runs/{RUN}/{PRED}/{RUN}.trace.jsonl"
if not trace.is_file() or sha(trace) != PIN:
    problems.append(f"the predecessor trace is missing or no longer hashes to {PIN[:8]}...")
if load(data / f"attempts/{RUN}/{PRED}.json").get("state") != "ABORTED":
    problems.append("the predecessor attempt is not ABORTED")
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1/{FSO}"):
    if (data / path).exists():
        problems.append(f"{path} already exists: the seal-only attempt or its FIT identity is not fresh")
proof = load(main / "docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/generation-plan-registered-v1.json").get("resume_replay_proof") or {}
if (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice")) != (1080, 0, 0):
    problems.append(f"the registered resume_replay_proof is not 1,080 / 0 / 0: {proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')}")
receipt_path = data / "coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json"
if not receipt_path.is_file():
    problems.append("the seal-only decision receipt root-admission-sealonly-v1.json is not minted")
else:
    receipt = load(receipt_path)
    if receipt.get("status") != "decided" or receipt.get("decision_id") != "slurp-stage3-psv1-fold-b-sealonly-admission-v1":
        problems.append("the seal-only receipt is not a decided slurp-stage3-psv1-fold-b-sealonly-admission-v1")
    if RUN not in receipt.get("eligible_run_ids", []) or SO not in receipt.get("eligible_attempt_ids", []):
        problems.append("the seal-only receipt does not list the arm run id and the seal-only attempt as eligible")
ledger = (main / "docs/exposure-ledger.md").read_text(encoding="utf-8")
for run in (RUN, "SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1"):
    rows = [ln for ln in ledger.split("\n") if ln.startswith("|") and f"| {run} |" in ln]
    if len(rows) != 1 or rows[0].split("|")[9].strip().lower() != "no":
        problems.append(f"{run}: the completion needs exactly one row reading consumed = no")
    elif "SEAL-ONLY COMPLETION REGISTERED" in rows[0] and "countersignature pending" in rows[0].split("SEAL-ONLY COMPLETION REGISTERED", 1)[1][:200]:
        problems.append(f"{run}: the seal-only clause is still a DRAFT (root countersignature pending)")
for problem in problems:
    print("refusing to flip the P-SV-1 seal-only completion:", problem)
sys.exit(1 if problems else 0)
PY

printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' "research: flip the P-SV-1 SEAL-ONLY completion to ready (owner decision 197: the same run id SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1 under attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only, resume_from the aborted arm attempt (trace 0c1edb20..., 1,080 rows); zero new model contacts; replay proof 1,080 checked / 0 failing / 0 sealed twice; P-SV-1's one recovery; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-psv1-fold-b-sealonly-admission-v1)" > /home/chao/psv1-sealonly-commit.txt

CYCLES=(
  "$SP/repin_cell_generic.sh $RRD slurp-native-stage3-psv1-fold-b-v1-resume generation /home/chao/psv1-sealonly-commit.txt"
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
echo "$CONVERGED" > /home/chao/psv1seal-flight-commit.txt
echo "flight commit $CONVERGED (the P-SV-1 seal-only cell ready at it)"
