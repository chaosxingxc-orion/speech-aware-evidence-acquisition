#!/usr/bin/env bash
# Model-free feasibility arithmetic. Run A's own embedding server log reported a
# per-request token count for each of its 60 audio contacts, quantized as
# 2 + 13*k with k in {2,3,4,5,6,7} and multiplicities {10,24,15,7,3,1}. That is
# enough to bracket the encoder's chunk length c from the frozen 60's own
# durations (ceil(seconds / c) == k), and hence to predict the worst-case token
# count for Run B's longest clip against the server's forced 512-token pooled
# budget -- BEFORE 552 registered contacts are spent.
#
# Reads durations and the operational server log only. No vector, no result.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"
export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km
cd "$REPO"
exec > >(tee "$SDIR/token-fit.log") 2>&1
python - <<'PY'
import math
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    load_pslu_sample_manifest,
    select_pslu_samples,
)

lock = load_lock(umbrella_lock_path())
root = data_root()

manifest = load_pslu_sample_manifest(REPO / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
slurp = SlurpAdapter(lock, root, repo_root=REPO)
run_a = sorted(float(s.audio_seconds) for s in select_pslu_samples(slurp.load_split("devel"), manifest))

# Observed by the Run A server itself: k = (n_tokens - 2) / 13.
observed = {2: 10, 3: 24, 4: 15, 5: 7, 6: 3, 7: 1}
cum = []
running = 0
for k in sorted(observed):
    running += observed[k]
    cum.append((k, running))
print("Run A durations (n=60): min %.3f mean %.3f max %.3f" % (run_a[0], sum(run_a)/len(run_a), run_a[-1]))
print("observed k multiplicities (k = (n_tokens-2)/13):", observed)
print()
print("boundary brackets -- the m-th smallest duration must satisfy ceil(s/c) = k:")
lo, hi = 0.0, 1e9
for k, m in cum:
    if m >= len(run_a):
        s_m, s_next = run_a[m - 1], None
    else:
        s_m, s_next = run_a[m - 1], run_a[m]
    # s_m <= k*c  ->  c >= s_m / k
    lo = max(lo, s_m / k)
    if s_next is not None:
        # s_next > k*c  ->  c < s_next / k
        hi = min(hi, s_next / k)
    print(f"  k={k}: {m}-th smallest = {s_m:.3f}s -> c >= {s_m/k:.4f}"
          + (f"; next = {s_next:.3f}s -> c < {s_next/k:.4f}" if s_next is not None else ""))
print()
print(f"CHUNK LENGTH BRACKET: {lo:.4f} <= c < {hi:.4f}")
if lo >= hi:
    print("  (inconsistent -- the simple ceil model does not fit; treat the worst case as unbounded)")

a2t = Audio2ToolAdapter(lock, root, repo_root=REPO)
run_b = sorted(float(s.audio_seconds) for s in a2t.load_split("discovery"))
print()
print("Run B durations (n=%d): min %.3f mean %.3f max %.3f total %.2f"
      % (len(run_b), run_b[0], sum(run_b)/len(run_b), run_b[-1], sum(run_b)))
for thresh in (10, 20, 25, 30, 33, 35):
    print(f"  clips longer than {thresh}s: {sum(1 for s in run_b if s > thresh)}")

print()
print("PREDICTED TOKENS for Run B's longest clip, over the bracket:")
worst = run_b[-1]
for c in (lo, (lo + hi) / 2, hi - 1e-6):
    toks = 2 + 13 * math.ceil(worst / c)
    print(f"  c={c:.4f} -> ceil({worst:.2f}/c)={math.ceil(worst/c)} -> {toks} tokens"
          + ("  ** EXCEEDS 512 **" if toks > 512 else "  (fits 512)"))
print()
print("MAX SAFE CLIP LENGTH at the worst-case (smallest) c:")
kmax = (512 - 2) // 13
print(f"  512-token budget admits k <= {kmax} chunks -> at c={lo:.4f}s, clips up to {kmax*lo:.2f}s")
over = [s for s in run_b if 2 + 13 * math.ceil(s / lo) > 512]
print(f"  Run B clips that would exceed 512 at the worst-case c: {len(over)}")
if over:
    print(f"    longest {len(over)}: {[round(s,2) for s in over[-10:]]}")
PY
