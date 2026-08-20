#!/usr/bin/env bash
# The full suite at the flight commit. Model-free (every probe/client test
# drives a fake transport or MockEmbeddingClient -- zero sockets, zero GPU).
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
cd "$REPO"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git HEAD: $(git -C "$REPO" rev-parse HEAD)"
  echo "dirty entries: $(git -C "$REPO" status --porcelain | wc -l)"
  echo "PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE"
  python -m pytest -q -p no:cacheprovider
  echo "pytest exit: $?"
  echo "bytecode under the frozen scoring package after the suite (D3 gate): $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l)"
  echo "dirty entries after: $(git -C "$REPO" status --porcelain | wc -l)"
  echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$SCRATCH/preflight-pytest.log"
