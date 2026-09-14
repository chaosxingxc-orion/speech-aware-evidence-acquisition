# Status 090: Service restored and sole native TRAIN A recovery generating

Snapshot: 2026-09-14T05:55:36.358181+00:00. Keep the owner goal active.
The completed exploratory direct-versus-native DEV comparison and its verdict
remain preserved. This status records a distinct TRAIN source flight.

## Interruption and restoration

The initial TRAIN A anchor at commit51b492a0 aborted after the serving log
recorded a CUDA illegal memory access in ggml_cuda_kernel_launch, with
ggml_cuda_op_div on the stack. The campaign then recorded remote connection
closure. Its durable exposure is 5 generation requests and 12.5793125 speech
seconds: 1 returned response, 4 unanswered requests across 4 launched samples.
Five successful real-request fits used 20 endpoints. There is no terminal
sample, complete manifest or score. Do not read partial quality or replay the
old attempt. The later owner-reported reboot is not the sole observed cause.

Accounting: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-v1/
interruption-accounting-v1.json.
SHA256: 1d49e5f7f24c5c4ce93c99ac9474a0599008b0b540d326fa0d0d224aea6a39fb.

Root recorded the old service stopped through the shared stale-stop command
after observing no old process, closed port8080 and zero GPU memory. Root
archived the old flight metadata under an acquired free kernel guard, preserving
its bytes. The attempt was already ABORTED and was not rewritten.

The owner-authorized new service is
serving-slurp-native-train-a-recovery-np4-v1, PID767 on boot
66947d87-43d2-4860-9766-11060b2e6bb6. It uses the identical model fragment,
decoder hash, binary and prepared-packet root, no mmproj, total98304 context,
four24576-token slots and max512. The10-second monitor is active.
Fresh-process health does not establish the CUDA root cause or prove a fix.

## Current recovery

Run: SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1.
Attempt: attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1.
Campaign PID2124. Tool session3387. Service wrapper session32418; monitor58863.
Frozen runtime: /home/chao/saea-worktrees/slurp-train-anchor-cuda-recovery-v1,
commit826a77c7bd9030ccbc25f2b74cd6fa4ed69db561, clean at observation.

At the snapshot the attempt is OPENED with 39 charged
requests, not completed samples. GPU has reached98% in consecutive samples
and four slots are busy; the latest pinned sample is
91.0% with
22976.0 MiB.
Progress receipt: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
runtime-progress-v1.json, SHA256 4322f0a406fcd74a5b6ad81a25f07ca9a728f4131391c095395ef376a3b42600.
No task-quality result was read.

All1080 ordered samples, role prompts, native graph, candidate bounds, stores,
sampling and speech packets are unchanged. The new preparation output equals
the original byte-structure exactly and warms with no producer invocation.
New run/attempt/fit/service identities, root admission, exposure rows and
clean-source protocol were committed before contact. See
docs/readiness/2026-09-14-slurp-native-dual-store-train-fold-a-anchor-recovery-v1/.
This is the sole recovery. Any second failure closes this flight. Do not
automatically restart or spend unused ceilings on another attempt.

## Parallel analysis preparation

The shared offline native TRAIN candidate-stage sidecar is integrated in the
review checkout, not the frozen runtime. It reuses source, candidate, reference
and reward-link verification, exports coverage and covered-only conditional
correctness without gold strings, and leaves final reward vectors unchanged.
Root fixed a stale-cache risk by binding the full derived diagnostic document.
The integrated65-test selection passed in8.76seconds; real source verification
remains pending because the full TRAIN trajectory is still running.
Test log SHA256: d9b2a1d8a862d3d2016272bcb9b9bb50e6a98aead8b870eaf7311fd5fd4cec14.

## Next actions

Monitor this exact process/attempt and healthy resident; retain original
source and interruption evidence. On success, seal all1080 outputs and run
one complete official TRAIN score with per-sample counts, then verify and
release its actual sources. Prepare reward links and stage diagnostics using
shared entries, without rescoring. Keep Fold B untouched.

Follow OWNER-CANDIDATE-COVERAGE-026 and the candidate-coverage/information-gain
plan: optimize C0/C1 coverage separately from covered-set joint resolution,
then admit task-useful evidence acquisition according to TRAIN findings.
No enhanced tool, candidate refresh, memory pack, proposal run, Fold B
evaluation or new DEV comparison is authorized by this status.
