# Status 034: SLURP control sealed; speech arm dispatched on the same service

Date: 2026-09-11T12:32:46.035331+00:00. OWNER-GPU-RESUME-013 remains current. This boundary records
progress, not a completed scientific comparison.

## GPU execution and custody

The control completed successfully: 2,000 generation calls, 1,000 terminal
outputs and 6,002 actual-fit endpoints. Common bundle verification passed.
Both complete phase fits passed; their minimum margins were 13,716 tokens
(direct) and 6,091 tokens (slots). Fit-inclusive utilization cost was
0.21377297687994107 GPU hours against the shared 0.5 per-arm cap; audio cost
was 5,769.58737500002 seconds against 6,000.

Control manifest SHA-256:
55b063174c635a921844f8b0acc3fc1a12bf7a5c6748b4e6fd75776b9bd55797.
Root seal-check DATA receipt:
coordination/slurp-program-matched-control-seal-check-v1.json,
SHA-256 2ac58644d29809c8983cd017ac8c94090e5b583b4f582d3fbc37ee6e86dce776.
Independent immutable monitor/cost closure is running in parallel.
The seal-check's null use_phase count is not phase proof; retain that receipt
and verify the actual phase metadata in a separate successor.

Control worker session 7178 exited zero. Root released only control lease
session 20612, which exited zero. The model remains in the same process.
Root acquired speech lease PID 37699 / session 20954, then dispatched speech
worker PID 38011 / session 24915. Preserve the lease until complete seal or
explicit abort reconciliation.

Resident: serving-slurp-live-program-matched-np4-v1, server PID 35780,
root wrapper PID 35765 / session 49170, ten-second monitor PID 35824 /
session 62129. Geometry is c65536 / np4 / 16384 per slot, decoder-only
with no mmproj. Actual experiment requests use the registered max256.
Source remains the unchanged frozen checkout
/home/chao/saea-worktrees/slurp-program-matched-generation at
21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff.

Speech dispatch receipt:
DATA coordination/slurp-program-matched-speech-dispatch-v1.json,
SHA-256 198745230b1b9985b3c017a6e8be35e3ddc092642d3c19fcffb18946b97ecde1.

## Handoff and utilization

The 60-second handoff target was missed. The interval from the control terminal
contact boundary at 12:20:32 UTC to speech worker process start at 12:27:32 UTC
was approximately 420 seconds. The root first verified the complete seal and
budget, then acquired the speech lease at 12:22:16 UTC. The remaining roughly
316 seconds before worker start were coordinator delay and are not model work.

After dispatch, the speech worker read and validated existing source-bound
feature packets from the WSL mounted data drive, then began the registered
actual fit. This CPU/data phase briefly leaves the GPU idle. Do not label it
effective generation or claim continuous 100 percent utilization. During
control generation, sampled GPU utilization was typically 84 to 95 percent
with all four slots used. Keep the frozen scheduling/configuration unchanged;
do not invent extra contacts to occupy the device.

At 12:32:59 UTC, the speech direct fit had passed all 1,000 requests and
3,001 registered endpoints with a 13,716-token minimum margin. The attempt
had charged 324 generation calls; the 12:32:54 monitor sample showed
four busy slots, zero idle slots and 87 percent GPU utilization.
These are dated partial operational counts, not a quality result or final seal.

## E21 CPU scoring

The complete direct score succeeded once, in 1929.26 seconds. Its score SHA-256
is 68d2792a22f0901aa7fd8261210d6dbfee5971aae6e5678aa85ded3a93e53682;
the complete-score receipt SHA-256 is
2a8aa24693d3fdfcf7c0aec31a2b7a8d93fa55e5905d9e336e0da8937f337d1d.
Do not rerun it.

The repair is now the sole full scorer: runner PID 37643, child PID 37651,
session 78549, managed by aligned_scoring_views. Both jobs use frozen
64440737 and explicit data/lock context. The existing whole-call alignments
explain the long CPU score tail; preserve their implementation and complete
roster. No SLURP full scorer may overlap this job.

## Next actions

1. Keep speech running through both real phase fits and both independently
   generated stages; track counts and budgets without reading quality.
2. After its seal, verify completeness, costs and common service identity,
   release only its lease, and record the closed pair's read release.
3. Build both predeclared joined deliveries from immutable raw parents. Score
   each complete roster exactly once when the E21 scorer is free, then run
   the unchanged paired analysis.
4. Review the E21 saved-score contrasts and protection guards, settle the
   existing attempts and record the scientific verdict.
5. Preserve held S4 exemplars, historical failures and the unproven live E21
   review/selection/new-observation behavior. No adaptive repeat is authorized.

Keep owner-approved limits: 4,000 planned / 4,200 maximum generations,
12,004 actual-fit endpoints, 1.0 utilization GPU hour for the pair and
0.5 per arm including fits. No new code, model, encoding or method was added.
