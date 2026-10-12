#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# VARIANT 1 of the COMP-1 recovery: flip the RESUME-RECOVERY cell and G5's smoke and arm to ready on master,
# model-free, converged at ONE HEAD, which becomes the flight commit of batch_chain_comp1_resume.sh.
#
# Root runs this ONLY after, in order:
#   1. the OWNER has ruled for the resume (owner decision 22's letter -- code and request bytes unchanged -- is
#      broken by the harness fixes; the byte-identity proof is the case for admitting it anyway);
#   2. the branch carrying the fix (fable/comp1rec, a451f942) and this registration (fable/comp1res) is merged;
#   3. root has countersigned the resume's DRAFT clauses on the arm's generation and FIT rows and the proof row
#      SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME-BYTE-IDENTITY-PROOF-V1, and marked the -REC section superseded unflown;
#   4. root has minted $DATA/coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v1.json (decision id
#      slurp-stage3-comp1-fold-a-resume-admission-v1, status decided, eligible_run_ids naming
#      SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 and SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1).
# --allow-output-change is never passed. The G5 cells are the ones batch_chain_comp1_g5.sh would have flown; they
# never started (no runs/ or attempts/ directory under their run ids), so they are re-converged here unchanged.
#
# Sequence (the comp1_g5_flip.sh shape): the resume cycle, then G5's smoke and arm cycles, then a CONVERGENCE pass
# re-running all three until one whole pass commits nothing (a later flip rewrites the shared exposure ledger after
# an earlier cell reported "satisfied"). Only then is HEAD recorded. Untracked files count as dirt.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/comp1
G5=$MAIN/scripts/flights/g5
RRD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1
G5RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
PY=/home/chao/.venvs/speechrl/bin/python
cd "$MAIN" || exit 1

# Preconditions: the proof receipt passes and names the declared trace, the predecessor trace is untouched, the
# arm's rows are unconsumed, the receipt is minted, the A/A is FINALIZED, G5 never started.
$PY -B - "$MAIN" "$DATA" <<'PY' || exit 6
import hashlib, json, sys
from pathlib import Path
main, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
TRACE = "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"
problems = []
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
try:
    proof = load(data / "coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json")
    if proof.get("verdict") != "PASS" or proof.get("trace", {}).get("sha256") != TRACE:
        problems.append(f"the byte-identity proof is {proof.get('verdict')!r} over {proof.get('trace', {}).get('sha256')!r}")
except FileNotFoundError:
    problems.append("the byte-identity proof receipt is missing: run scripts/flights/comp1/comp1_resume_byte_identity_proof.py")
trace = data / f"runs/{RUN}/attempt-slurp-native-stage3-comp1-fold-a-generation-v1/{RUN}.trace.jsonl"
digest = hashlib.sha256()
with trace.open("rb") as handle:
    for block in iter(lambda: handle.read(1 << 20), b""):
        digest.update(block)
if digest.hexdigest() != TRACE:
    problems.append(f"the predecessor trace hashes to {digest.hexdigest()}, not the declared {TRACE}")
receipt_path = data / "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json"
if not receipt_path.is_file():
    problems.append("the resume decision receipt root-admission-resume-v3.json (attempt 3) is not minted")
else:
    receipt = load(receipt_path)
    if RUN not in receipt.get("eligible_run_ids", []):
        problems.append("the resume receipt does not list the arm run id as eligible")
aa = load(data / "attempts/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1.json")
if aa.get("state") != "FINALIZED":
    problems.append(f"the shared A/A attempt is {aa.get('state')!r}, not FINALIZED")
for g5 in ("SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"):
    if (data / "runs" / g5).exists() or (data / "attempts" / g5).exists():
        problems.append(f"{g5} has a run or attempt directory: G5 is no longer unstarted -- stop and re-plan")
ledger = (main / "docs/exposure-ledger.md").read_text(encoding="utf-8")
for run in (RUN, "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1"):
    rows = [ln for ln in ledger.split("\n") if ln.startswith("|") and f"| {run} |" in ln]
    if len(rows) != 1 or rows[0].split("|")[9].strip().lower() != "no":
        problems.append(f"{run}: the resume needs exactly one row reading consumed = no")
for problem in problems:
    print("refusing to flip the COMP-1 resume:", problem)
sys.exit(1 if problems else 0)
PY

cat > /home/chao/comp1-resume-commit.txt <<M
research: flip the COMP-1 RESUME-RECOVERY to ready (owner decision 22, harness item E10: the same run id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 under attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3 (resume attempt 3 with a fresh FIT attempt id attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3; attempt 2 aborted 00:20:43Z on a FIT-identity collision caused by a coordinator-side registration error -- attempt 1's FIT attempt id was reused; the fix is proven by the four-row dry run SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1 flown as the step's smoke, owner decision 181), resume_from the aborted attempt's trace 029a2dbb..., 471 rows kept under I7r custody and 609 flown; admitted on the model-free byte-identity proof coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json; COMP-1's ONE recovery re-registration; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-fold-a-resume-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
cat > /home/chao/comp1-resume3-smoke-commit.txt <<M
research: flip the four-row DRY RUN of COMP-1 resume attempt 3 to ready (owner decision 181: fix, prove on a 4-row dry run, then resume; SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1 under attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3-smoke with FIT attempt attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3-smoke; the parent COMP-1 smoke's bytes; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-fold-a-resume-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
for K in smoke arm; do
cat > /home/chao/g5-$K-commit.txt <<M
research: re-converge G5 ($K) at the COMP-1 resume flight commit (G5 never started in the aborted chain; its registration, receipt and replicate SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 are unchanged; owner decisions 127, 135, 138, 153 and 160; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-g5-fold-a-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
done

CYCLES=(
  "$CP/comp1_repin_resume3_smoke.sh $RRD slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1 smoke-generation /home/chao/comp1-resume3-smoke-commit.txt"
  "$CP/comp1_repin_resume.sh $RRD slurp-native-stage3-comp1-fold-a-v1-resume generation /home/chao/comp1-resume-commit.txt"
  "$G5/g5_repin_smoke.sh $G5RD slurp-native-stage3-g5-fold-a-smoke-4-v1 smoke-generation /home/chao/g5-smoke-commit.txt"
  "$G5/g5_repin_arm.sh $G5RD slurp-native-stage3-g5-fold-a-v1 generation /home/chao/g5-arm-commit.txt"
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
echo "$CONVERGED" > /home/chao/comp1res-flight-commit.txt
echo "flight commit $CONVERGED (the COMP-1 resume cell and G5 smoke / arm all ready at it)"
