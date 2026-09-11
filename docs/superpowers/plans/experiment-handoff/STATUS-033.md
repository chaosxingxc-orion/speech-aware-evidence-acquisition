# Status 033: owner resumed GPU work; SLURP control generating at full slot occupancy

Date: 2026-09-11 UTC. This turn made progress: owner resumed GPU experiments,
root switched serving geometry and started the already-approved SLURP control
after its complete first-phase actual request fit passed.

## Current owner authority

OWNER-GPU-RESUME-013 supersedes the temporary OWNER012 scheduling pause. The owner
explicitly resumed GPU work after network reconnection and requests high
utilization. The existing OWNER011 one-pair method, analysis and budgets remain
unchanged:4000 planned/4200 maximum generations,12004 actual-fit endpoints and
1.0 utilization GPU-hour family,0.5 per arm including fits. No extra repeat is
authorized if this comparison fails.

Owner-resume DATA receipt: coordination/owner-gpu-resume-013-v1.json,
SHA-2562191c76a2eca92fd954ce781ea6c375e872750eeb1fbe53d04ce84e8b801792e.

## Service switch and live custody

E21 generation had already completed with its lease released and its costs
sealed. Root stopped only the old resident through scripts/serving_session.sh.
The shared stop completed without force at2026-09-11T11:57:42Z; old coordinator
tool session95670 exited zero. Do not treat the network/host time gap during the
owner-directed pause as experimental generation time.

Root started serving-slurp-live-program-matched-np4-v1 at11:58:20Z from the clean
frozen source /home/chao/saea-worktrees/slurp-program-matched-generation,
commit21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff. The decoder is no-mmproj,
c65536/np4/16384per slot, with the inherited qualified weights/build/cache.
The model fragment's historical max64 name/default remains; actual experiment
requests retain the preregistered max256 override.

- Root serving wrapper PID35765, tool session49170; actual server PID35780.
- Root10-second monitor PID35824, tool session62129.
- Root control lease PID35877, tool session20612.
- Attach-only control worker PID35924, tool session7178.
- Control token file: DATA coordination/slurp-program-matched-control-v1.token.json.
- Service receipt SHA-256c429c5876dc0d078b4794314d775ee03263446b6021eb126fa6c7a49e7814d56.

Revalidate these live handles before acting. Never infer termination from an
observation timeout. Root retains the lease through seal or explicit abort
reconciliation; the worker never owns service stop or replacement.

## Actual fit and generation evidence

The complete direct-stage fit covered1000 requests and3001 registered endpoints,
with zero generation in that fit. Every request fits and the minimum margin is
13716tokens. Receipt:
DATA prepared/SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-FIT-V1/attempt-live-program-matched-control-fit-v1/direct.request-fit.json,
SHA-256c8baaca85a71fba92f1902f71d4049fbb116259afacd8f56e126efebe6841eb0.

Initial fit time included reading source-bound prepared feature packets over the
WSL mounted data drive; no missing feature was encoded. At12:03:44Z the monitor
showed4busy/0idle slots,86%GPU utilization and21272MiB device memory. The durable
generation attempt had charged81requests at the subsequent12:03:47Z observation.
These are partial operational counts, not quality results or a complete seal.

The slots-stage fit must still run with this arm's own newly generated first
stage. Do not substitute the synthetic predecessor, skip the fit, change the
output cap, or borrow the other arm's first-stage responses.

## Parallel CPU work

E21 direct score remains the sole complete scorer under aligned_scoring_views:
parent PID33717, child PID33724, tool session57224. Root revalidated both live
after reconnection; the agent confirmed active CPU progress and no restart.
Repair scoring remains sequentially next, followed by the frozen saved analysis.
Use frozen64440737 and the preregistered release from STATUS-032. Keep one full
official scorer and the global CPU/memory allowance.

## Exact next steps

1. Monitor the current control worker and both live phase-fit receipts. Read only
   operational costs/counts until both comparison arms seal or a formal hold.
2. After complete control seal and custody verification, release lease20612,
   keep the same resident service, then use the prepared speech lease and worker
   commands from coordination/slurp-program-matched-frozen-handoff-v1.json.
3. The speech arm independently generates its own first stage and slots stage,
   with its own actual fits. Use all four slots within the frozen geometry.
4. After both raw parents seal, build the registered joined derivatives, score
   each complete roster once, execute the unchanged paired analysis, and close
   costs/attempts. Do not automatically score raw parents.
5. Root reviews E21 scores/guards and finalizes its existing comparison in
   parallel. Preserve every earlier failed/held scientific result and the
   explicit unproven live E21 review/selection/new-observation gap.

The runtime implementation and frozen experiment source were not changed.
