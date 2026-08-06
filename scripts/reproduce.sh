#!/usr/bin/env bash
# Model-free reproduction entrypoint (R0). This script never touches the model:
# a model-facing run additionally requires a validated ExecutionPlan file and a
# pre-registered exposure ledger row, driven explicitly from Python — never here.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: reproduce.sh [--help] [--full]

Runs the model-free verification chain: the E0 closure + runtime receipt gate
dry-run (authorizes nothing). Requires SPEECHRL_DATA_DIR and the pinned
runtime per docs/engineering.md.

GGUF identity (owner decision 2026-08-06, docs/owner-decisions-pending.md item
7): by default this gate open verifies the pinned GGUF set via the
CHEAP-IDENTITY FAST PATH (size + last-modified time + OS file id against a
cached record bound to the runtime receipt's own hash) -- it does NOT re-hash
the pinned model bytes this run, and falls back to a full re-hash automatically
if the cache is missing, stale, or the receipt changed. Pass --full to force
the authoritative full SHA-256 re-hash of every GGUF file instead. Every other
check (E0 closure, scoring freeze, exposure pre-registration, carrier scope,
llama.cpp build binary, runtime libraries) is unconditionally re-verified from
scratch every run either way — see docs/engineering.md and
FrozenCoreGate._validate_runtime for exactly what the fast path does and does
not defend against.

Env:
  LLAMA_RUNTIME_ROOT  Directory CONTAINING the pinned llama.cpp checkout
                       (runtime receipt paths, e.g. llama.cpp/build/bin/...,
                       are resolved relative to this directory, not to the
                       checkout itself). Default: $HOME.

Options:
  --full   Force the authoritative full SHA-256 re-hash of the pinned GGUF set
           (slow: tens of GB read from disk). Default: the fast path above.
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# Scan the full argument list (not just $1) for --full, so it composes with
# any future flag ordering; anything else is ignored rather than rejected,
# matching this script's existing leniency.
FULL_HASH_REQUESTED=0
for arg in "$@"; do
  if [[ "$arg" == "--full" ]]; then
    FULL_HASH_REQUESTED=1
  fi
done

if [[ "$FULL_HASH_REQUESTED" == "1" ]]; then
  echo "reproduce.sh: --full requested -- the runtime gate will do the authoritative full SHA-256 re-hash of every pinned GGUF file."
else
  echo "reproduce.sh: fast path (default) -- the runtime gate verifies the pinned GGUF set by size/mtime/OS-file-id and will NOT re-hash the model bytes this run unless the cache is missing or stale; pass --full for the authoritative re-hash."
fi

export PYTHONDONTWRITEBYTECODE=1
# SAEA_RUNTIME_FULL_HASH is exported only for this script's own subprocess
# tree (this one `python -m ...` invocation) -- it is never persisted into the
# caller's interactive shell, so it cannot leak into an unrelated, later real
# model-touch command run in the same terminal (contracts.RUNTIME_FULL_HASH_ENV
# doc comment).
if [[ "$FULL_HASH_REQUESTED" == "1" ]]; then
  export SAEA_RUNTIME_FULL_HASH=1
else
  export SAEA_RUNTIME_FULL_HASH=0
fi
python -m speech_aware_evidence_acquisition.e0.generate verify --runtime-root "${LLAMA_RUNTIME_ROOT:-$HOME}"
