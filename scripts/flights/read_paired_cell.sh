#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The standard paired read of one sealed Stage-3 cell (owner decision 163), from its readiness package.
#
#   bash scripts/flights/read_paired_cell.sh docs/readiness/<package> [--passes vs-aa] [--output-base DIR]
#
# Reads the package's analysis recipe (arms.arm, arms.in_chain_replicate, arms.comparator, resampling,
# output.analysis_root) and runs scripts/analysis/stage3_paired_read.py --package on it: pass vs-aa (left =
# the in-chain A/A, the GATING contrast) and pass vs-comparator (left = the recipe's comparator, CONTEXT
# only), each with the per-scenario tables (both weightings), the delivery / conversion counts and the
# frontier row, under $SPEECHRL_DATA_DIR/<output.analysis_root>/<pass>/. It REFUSES before any score is
# opened unless the recipe's READ run id has a ROOT COUNTERSIGNED exposure row, and it never overwrites a
# pass directory that already holds files. MODEL-FREE: zero model / tokenizer / encoder / scorer / server
# contacts. The driver writes DESCRIPTIVE numbers; the verdict is the coordinator's and its disposition is
# taken with the owner in conversation (decision 139).
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
PKG=${1:?usage: read_paired_cell.sh docs/readiness/<package> [--passes vs-aa,vs-comparator] [--output-base DIR]}
shift
case "$PKG" in /*) ;; *) PKG=$MAIN/$PKG ;; esac
[ -d "$PKG" ] || { echo "REFUSED: no package directory $PKG"; exit 3; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
"$PY" -B "$MAIN/scripts/analysis/stage3_paired_read.py" --package "$PKG" \
  --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" "$@"
rc=$?
[ $rc -eq 0 ] || echo "READ REFUSED OR FAILED (exit $rc)"
exit $rc
