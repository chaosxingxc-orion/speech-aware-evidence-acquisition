#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the SLURP test-sample SUCCESSOR-2 composed cell (slurp-milestone-successor2-composed-v1; owner decisions 233, 241, 250 A,
# 251 A) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole pass commits nothing, and only
# then is HEAD recorded as the flight commit (/home/chao/ms2-flight-commit.txt). NO SMOKE cell exists and none is flipped: the
# allowance lists a test-sample smoke as not authorised, and a smoke under the read id would consume its one attempt. Root runs this
# ONLY after:
#   1. the R6-P1 flight has SEALED (one experiment in flight) and the serving session is free;
#   2. countersigning the three DRAFT ledger rows (run, FIT, READ) -- the countersignature of the first consumed row names the
#      conversational report of the R5 read (NEUTRAL) to the owner (allowance first_contact_gate: date and arm);
#   3. minting coordination/slurp-milestone-successor2-composed-v1/root-admission-v1.json with
#      scripts/flights/nx/milestone_successor2_mint_receipt.py (the two eligible run ids);
#   4. master carries the CURRENT_LOCK v2.2 change (decision 249) and the cell passes core.flight.cli check; no concurrent merge
#      (a flip loop commits a half-resolved merge).
# The flip refuses on any refusal of milestone_successor2_preflip_check.py (allowance pin / status / ids, a registered smoke, a
# pending pin, an existing attempt). After the flip, refresh the registered plan pins (the writer copies the minted supply pin into
# the plans) and flip again. --allow-output-change must never be passed.
#   bash scripts/flights/nx/milestone_successor2_flip.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
NX=$MAIN/scripts/flights/nx
PY=/home/chao/.venvs/speechrl/bin/python
SLUG=milestone-successor2-composed
LABEL=SUCCESSOR2-COMPOSED
RD=docs/readiness/2026-10-10-slurp-$SLUG-v1
CELL=slurp-$SLUG-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/nx/milestone_successor2_mint_receipt.py)"; exit 6
fi
$PY -B "$NX/milestone_successor2_preflip_check.py" --repo-root "$MAIN" --data-root "$DATA" || { echo "$LABEL flip REFUSED by the preflip gate"; exit 6; }
printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
  "research: flip $LABEL to ready (test-sample successor 2, owner decisions 233/241/250 A/251 A: the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1, one attempt, no smoke; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
  > /home/chao/ms2-arm-commit.txt
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  bash "$SP/repin_loop_generic.sh" "$NX/milestone_successor2_repin_cell.sh" "$RD" "$CELL" generation /home/chao/ms2-arm-commit.txt || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/ms2-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL ready at it)"
