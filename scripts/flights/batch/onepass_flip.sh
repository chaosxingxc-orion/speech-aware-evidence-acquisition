#!/bin/bash
# One-pass package flip (owner decision 270 A): ONE call of scripts/flights/repin_package_one_pass.py re-pins every cell of a package,
# refreshes the registered-plan pins, writes the shared documents and the ledger rows once, commits ONCE and runs core.flight.cli check
# once per cell on the committed tree. Model-free. Replaces repin_loop_generic.sh x cells x passes + refresh_registered_plan_pins.py +
# the second loop of the iterative mode (which stays available as FLIP_MODE=iterate, the default).
#
# Usage: onepass_flip.sh --readiness-dir <RD> --prereg <file> --package <coordination dir name> --decision-path <relpath> --decision-id <id> \
#                        --commit-msg <file> [--ready-receipt <cell>]... [--flight-commit-file <path>]... <cell> [<cell> ...]
#   Each <cell> is both the experiment id and the cell id (every flip package registers one experiment fragment per cell).
# Env: SAEA_MAIN (repo root; refused under /mnt unless SAEA_ALLOW_9P_FLIP=1), SAEA_FLIP_DATA (data root), SAEA_FLIP_LOCK (lock path),
#      SAEA_ONEPASS_NO_CHECK=1 (stage only, tests), SAEA_ONEPASS_OUT (directory for the summary/err files, default /home/chao).
# Exit: 64 repo root on 9p; 2 usage; 4 the tool refused (the JSON error is printed); 5 a post-commit gate failed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
[ -n "${SAEA_FLIP_DATA:-}" ] && export SAEA_DATA_ROOT=$SAEA_FLIP_DATA  # test override, as before
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
DATA=${SAEA_DATA_ROOT:-$SAEA_DATA_ROOT_DEFAULT}  # resolved and guarded by saea_data_root_init before the first cd
LOCK=${SAEA_FLIP_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
PY=${SAEA_PY:-/home/chao/.venvs/speechrl/bin/python}
OUTDIR=${SAEA_ONEPASS_OUT:-/home/chao}
RD=; PREREG=; PKG=; DEC_PATH=; DEC_ID=; MSG=; RECEIPTS=(); FCF=(); CELLS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --readiness-dir) RD=$2; shift 2 ;;
    --prereg) PREREG=$2; shift 2 ;;
    --package) PKG=$2; shift 2 ;;
    --decision-path) DEC_PATH=$2; shift 2 ;;
    --decision-id) DEC_ID=$2; shift 2 ;;
    --commit-msg) MSG=$2; shift 2 ;;
    --ready-receipt) RECEIPTS+=("$2"); shift 2 ;;
    --flight-commit-file) FCF+=("$2"); shift 2 ;;
    -*) echo "usage: onepass_flip.sh: unknown option $1" >&2; exit 2 ;;
    *) CELLS+=("$1"); shift ;;
  esac
done
[ -n "$RD" ] && [ -n "$PREREG" ] && [ -n "$PKG" ] && [ -n "$DEC_PATH" ] && [ -n "$DEC_ID" ] && [ -f "$MSG" ] && [ ${#CELLS[@]} -gt 0 ] \
  || { echo "usage: onepass_flip.sh --readiness-dir RD --prereg F --package P --decision-path R --decision-id I --commit-msg FILE [--ready-receipt C]... [--flight-commit-file F]... CELL..." >&2; exit 2; }
# Owner 2026-10-12: hot paths never run on /mnt/* (9p). Refuse (64) unless SAEA_ALLOW_9P_FLIP=1.
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_in_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
cd "$MAIN" || exit 1
# 2026-09-29: D3 freeze refuses a __pycache__ entry beside the frozen scoring sources.
if [ -d "$MAIN/src" ]; then find "$MAIN/src" -type d -name __pycache__ -prune -exec rm -rf {} +; fi
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
ARGS=(--repo-root "$MAIN" --data-root "$DATA" --runtime-root "${SAEA_RUNTIME_ROOT:-/home/chao}" --lock-path "$LOCK"
      --readiness-dir "$RD" --preregistration "$PREREG" --package-name "$PKG"
      --decision "$DEC_PATH" --decision-id "$DEC_ID" --set-ready --commit-message-file "$MSG")
for c in "${CELLS[@]}"; do ARGS+=(--experiment "$c" --cell "$c"); done
for c in "${RECEIPTS[@]}"; do ARGS+=(--ready-receipt "$c"); done
for f in "${FCF[@]}"; do ARGS+=(--flight-commit-file "$f"); done
[ "$SAEA_ONEPASS_NO_CHECK" = 1 ] && ARGS+=(--no-check)
echo "== one-pass flip HEAD $(git rev-parse --short HEAD); tracked dirt: $(git status --short | grep -vc '^??'); cells: ${CELLS[*]}"
T0=$(date +%s)
$PY -B scripts/flights/repin_package_one_pass.py "${ARGS[@]}" > "$OUTDIR/$PKG-onepass.out" 2> "$OUTDIR/$PKG-onepass.err"
RC=$?
if [ $RC -ne 0 ]; then
  echo "REFUSAL (exit $RC):"
  $PY -c "import json,io,sys; t=io.open(sys.argv[1]).read(); print(json.loads(t)['error'][:800] if t.lstrip().startswith('{') else t[-800:])" "$OUTDIR/$PKG-onepass.err"
  if grep -q "old hash residue remains" "$OUTDIR/$PKG-onepass.err"; then
    echo "REMEDY: a package file still quotes a superseded hash. Do NOT edit the number inside a record of something that happened:"
    echo "        re-run that record's own producer at the flipped bytes (a dry run is model-free), then repair only THIS cell's own ledger rows (item E26)."
  fi
  exit 4
fi
$PY -c "
import json, sys
s = json.load(open(sys.argv[1]))
print('one-pass: commit', (s['commit'] or 'none')[:12], '| fragment rounds', s['fragment_rounds'], '| cells', len(s['cells']), '| checks', len(s['checks']))
print('timings (s):', s['timings_seconds'])
" "$OUTDIR/$PKG-onepass.out"
echo "tracked dirt after commit: $(git status --short | grep -vc '^??')"
echo "one-pass seconds: $(( $(date +%s) - T0 ))"
for c in "${RECEIPTS[@]}"; do
  CK=$DATA/coordination/$PKG/check-$c-ready-v1.json
  if [ -f "$CK" ] && [ -f "$MAIN/scripts/flights/batch/b1_check_summary.py" ]; then
    $PY -B "$MAIN/scripts/flights/batch/b1_check_summary.py" "$CK" "$MAIN/$RD/protocol-registered-v1.json" || { echo "check summary FAILED for $c"; exit 5; }
  fi
done
if [ ${#RECEIPTS[@]} -gt 0 ] && [ -f scripts/checks/results_ledger_check.py ]; then $PY scripts/checks/results_ledger_check.py 2>&1 | tail -1; fi
exit 0
