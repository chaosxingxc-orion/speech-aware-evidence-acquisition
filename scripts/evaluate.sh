#!/usr/bin/env bash
# Scoring entrypoint (R0; hardened R0 repair T6, invariant I7): model-free.
# --manifest is the AUTHORITATIVE, audit-grade path: verifies a run-manifest.json
# (core.bundle.verify_bundle) then scores it through its own configured scorers
# (core.scorers.score_bundle). --outputs scores a raw outputs JSONL directly
# against the frozen scoring stack with NO split/trace/hash verification --
# UNVERIFIED, never an audit record, ad-hoc/exploratory use only.
set -euo pipefail

usage() {
  cat <<'EOF'
usage:
  evaluate.sh --manifest <run-manifest.json>        AUTHORITATIVE (I7-verified)
  evaluate.sh --outputs <outputs.jsonl> [scorers]    UNVERIFIED, ad-hoc only
  evaluate.sh <outputs.jsonl> [scorers]              same as --outputs (legacy form)

For multiple independent authoritative manifests, use:
  evaluate_parallel.sh --jobs <jobs.jsonl> --output-dir <new-dir> [--workers N]

model-free scoring of the frozen scoring stack, never the model.

--manifest re-verifies the whole run bundle before scoring; this is the only
  path whose result may be cited as a formal record.
--outputs / the legacy positional form bypass split/trace/hash verification
  entirely and print a loud warning to stderr; their result is NOT an audit
  record. Default scorers: asr-wer.

Requires SPEECHRL_DATA_DIR for reference layers either way.
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

export PYTHONDONTWRITEBYTECODE=1
case "$1" in
  --manifest)
    python -m speech_aware_evidence_acquisition.core.driver score --manifest "$2"
    ;;
  --outputs)
    python -m speech_aware_evidence_acquisition.core.driver score --outputs "$2" --scorers "${3:-asr-wer}"
    ;;
  *)
    python -m speech_aware_evidence_acquisition.core.driver score --outputs "$1" --scorers "${2:-asr-wer}"
    ;;
esac
