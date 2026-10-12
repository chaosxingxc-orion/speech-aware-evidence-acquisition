#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# COMP-1 SEAL-ONLY completion (owner decision 189 option A): flip the seal-only cell and G5's smoke and arm to ready
# on master, model-free, converged at ONE HEAD, which becomes the flight commit of batch_chain_comp1_sealonly.sh.
#
# Root runs this ONLY after, in order:
#   1. the OWNER has ruled decision 189 for option A (seal-only completion of attempt 3 under the merged replay fix);
#   2. fable/comp1seal (fable/sealonly + this registration) is merged to master;
#   3. root has countersigned the DRAFT seal-only clauses on the arm's generation and FIT rows and the DRAFT row
#      SAEA-SLURP-STAGE3-COMP1-FOLD-A-SEALONLY-REPLAY-PROOF-V1;
#   4. root has minted $DATA/coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json with
#      scripts/flights/comp1/comp1_sealonly_mint_receipt.py (decision id slurp-stage3-comp1-fold-a-sealonly-admission-v1).
# --allow-output-change is never passed. runtime.py changed on fable/sealonly (its whole-file hash is part of every
# prepared artifact's identity), so the seal-only cell AND both G5 cells re-pin their prepared supplies here; each must
# reproduce its registered output digest.
#
# Loop form (memory: a later flip rewrites the shared exposure ledger after an earlier cell reported "satisfied"): the
# three cycles are re-run as one pass until a whole pass commits nothing, bound 4. Only then is HEAD recorded. Untracked
# files count as dirt.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/comp1
G5=$MAIN/scripts/flights/g5
RRD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1
G5RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
PY=/home/chao/.venvs/speechrl/bin/python
cd "$MAIN" || exit 1

# Preconditions: both predecessor traces untouched, the seal-only attempt unopened, the replay proof registered clean,
# the receipt minted, the A/A FINALIZED, G5 unstarted, both arm rows unconsumed.
$PY -B - "$MAIN" "$DATA" <<'PY' || exit 6
import hashlib, json, sys
from pathlib import Path
main, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
SO = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-seal-only"
PRED = {
    "attempt-slurp-native-stage3-comp1-fold-a-generation-v1": "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997",
    "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3": "87be5cefcaa395ad58a010b6d79986c5c79981c8cebe0279029bd22f7343df26",
}
problems = []
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
cell = load(main / "configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json")["cells"][0]
if cell["attempt_id"] != SO:
    problems.append(f"the resume cell declares attempt {cell['attempt_id']!r}, not the seal-only attempt")
if cell.get("resume_from") != [{"attempt_id": a, "trace_sha256": t} for a, t in PRED.items()]:
    problems.append("the resume cell's resume_from is not the registered two-predecessor list")
for attempt, pin in PRED.items():
    trace = data / f"runs/{RUN}/{attempt}/{RUN}.trace.jsonl"
    if not trace.is_file() or sha(trace) != pin:
        problems.append(f"{attempt}: the trace is missing or no longer hashes to {pin[:8]}...")
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1/{FSO}"):
    if (data / path).exists():
        problems.append(f"{path} already exists: the seal-only attempt or its FIT identity is not fresh")
proof = load(main / "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/generation-plan-registered-v1.json").get("resume_replay_proof") or {}
if (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice")) != (1080, 0, 0):
    problems.append(f"the registered resume_replay_proof is not 1,080 / 0 / 0: {proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')}")
receipt_path = data / "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json"
if not receipt_path.is_file():
    problems.append("the seal-only decision receipt root-admission-sealonly-v1.json is not minted")
else:
    receipt = load(receipt_path)
    if receipt.get("status") != "decided" or receipt.get("decision_id") != "slurp-stage3-comp1-fold-a-sealonly-admission-v1":
        problems.append("the seal-only receipt is not a decided slurp-stage3-comp1-fold-a-sealonly-admission-v1")
    if RUN not in receipt.get("eligible_run_ids", []) or SO not in receipt.get("eligible_attempt_ids", []):
        problems.append("the seal-only receipt does not list the arm run id and the seal-only attempt as eligible")
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
        problems.append(f"{run}: the completion needs exactly one row reading consumed = no")
    elif "SEAL-ONLY COMPLETION REGISTERED" in rows[0] and "countersignature pending" in rows[0].split("SEAL-ONLY COMPLETION REGISTERED", 1)[1][:200]:
        problems.append(f"{run}: the seal-only clause is still a DRAFT (root countersignature pending)")
for problem in problems:
    print("refusing to flip the COMP-1 seal-only completion:", problem)
sys.exit(1 if problems else 0)
PY

cat > /home/chao/comp1-sealonly-commit.txt <<M
research: flip the COMP-1 SEAL-ONLY completion to ready (owner decision 189 option A: the same run id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 under attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only, resume_from the original aborted attempt (trace 029a2dbb..., 471 rows) and resume attempt 3 (trace 87be5cef..., 609 rows); zero new model contacts; replay proof 1,080 checked / 0 failing / 0 sealed twice; the one recovery of row 175; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-fold-a-sealonly-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
for K in smoke arm; do
cat > /home/chao/g5-$K-commit.txt <<M
research: re-converge G5 ($K) at the COMP-1 seal-only flight commit (G5 never started; runtime.py changed on fable/sealonly, so its prepared supply re-pins with an unchanged output; its registration, receipt and replicate SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 are unchanged; owner decisions 127, 135, 138, 153 and 160; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-g5-fold-a-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
done

CYCLES=(
  "$CP/comp1_repin_sealonly.sh $RRD slurp-native-stage3-comp1-fold-a-v1-resume generation /home/chao/comp1-sealonly-commit.txt"
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
[ -z "$(git status --short)" ] || { echo "tree not clean after convergence (untracked files count): $(git status --short | head -3)"; exit 5; }
echo "$CONVERGED" > /home/chao/comp1seal-flight-commit.txt
echo "flight commit $CONVERGED (the COMP-1 seal-only cell and G5 smoke / arm all ready at it)"
