# Owner progress and decision briefing

Snapshot: 2026-09-10 15:25 UTC. The first full E21 DR parent is generating on
the GPU. The second parent has completed CPU preparation and waits for the root
handoff. Canonical master contains the reviewed shared analysis through
bec60089. The active generation worktree remains frozen at8e675662.

## Owner decisions and execution priority

The owner accepted exclusive offline GPU feature encoding followed by encoder
unload. Keep mmproj off GPU during resident inference. Optimize task quality
and total cost for post-recording meeting minutes; online latency is not a goal.
Use whole-roster phase barriers where actual predecessor state requires them.

Complete useful preparation in parallel and close each prerequisite once.
Root owns scientific design, service custody, dispatch, review and decisions.
Helpers perform bounded preparation, implementation or source-reading tasks.
The current GPU experiment proceeds while the next materials and complete-score
handoff are prepared; broader engineering does not block it.

No new owner decision currently blocks the registered DR continuation. The
earlier GPU-budget amendment question was superseded by a verified accounting
correction: the inherited1.2 GPU-hour cap per parent is a utilization integral,
not elapsed wall time. Keep that cap and report both quantities separately.
See [the accounting correction](2026-09-10-e21-dr-gpu-budget-accounting-correction.md).

## Scientific state

- Fable numerical reproduction is complete:16,560 statistical fields agree
  exactly. This was a model-free audit of existing results. Existing independent
  inference repeats remain separate evidence.
- Original KC-S1b: official DEV1000 micro SLU-F1 changes from35.8020 to44.3503
  percent. Original NEW500 strict entity mean-row F1 gain is10.1067pp, a
  different metric and population. Extra slot contact alone did not establish
  improvement.
- KV: seven generated/scored runs recovered. Removing original examples in
  KV0 is harmful; KV1/KV3 are null-compatible; KV2 fails its inherited twin
  guard. Retain KC-S1b content as the owner selected.
- G1 KU-S3: control, speech retrieval and form twin each completed1000
  generations and official scoring in one decoder-only process, all with
  max256. The component is admitted. NEW500 row SLU-F1 gains are6.6374pp
  versus matched control and3.6544pp versus form twin. Joined predecessor
  intent is preserved. This is not an independent treatment repeat or a live
  system measurement.
- G2 N/twin: both completed1000 generations and official scoring. N fails
  non-inferiority versus its declared historical comparator: NEW500 intent
  changes by-2.20pp and micro SLU-F1 by-11.744pp. G3 encoding and G4 a/b/c
  remain held; do not encode the7049 missing SLURP exemplars. Preserve the
  documented control-turn difference and descriptive structural audits.
- Historical E21 constrained repair: PERSON WER changes from22.488858 to
  18.752143 percent; its inference repeat is18.854988. Corpus WER changes
  from8.199519 to8.154490 percent, small against own-null repeat variability.
  Preserve both the original rejection and owner-authorized v2 admission.
- Historical DR constrained replay reproduces all1593 windows and44 stitched
  calls. Current DR has two generation parents and four predeclared deterministic
  deliveries. Neither current parent has a complete official score yet.
- LOOP judge/twin generation has not begun. Each plan has600 selected re-listen
  requests, with all1593 fixed windows delivered. CPU inventory preparation
  is in progress; exact feature encoding and formal fits follow in a dedicated
  service window.
- Live SLURP and E21 system quality and full costs remain unmeasured.
  Upstream E21 ASR/entity gains do not establish meeting-minutes quality.
  No formal chain-of-thought effectiveness experiment is complete.

## E21 GPU execution and preparation

Full offline DR feature encoding is complete:1593 unique windows from44 calls,
141345.8526875 speech seconds, with1593 successful preprocessing contacts.
All features were verified and promoted into formal window packets without
re-encoding. Both draft-source groups share packet artifact SHA256
9aba4ff0d9a78dc66afcdf73f35bea0e7e6919e8448211f383f95219833a5115.

The root resident service is serving-e21-dr-packets-np6-v2 on build
cddb000cb45ab44d33c84483cf5e5962cbbaa5bf. It uses decoder-only inference with
--no-mmproj, total context36864 and6 slots. Preserve the registered OJW
prefetch1 behavior throughout the comparison; observed concurrent requests
are normally2. Do not change concurrency or geometry midflight.

Both exact1593-request fits passed at max1024 and the inherited2x margin:
minimum spare capacity274 tokens for unit drafts and572 for self drafts.
The current OJW bridge additionally sealed four actual full90-second-window
requests, with no retry, skip or saturation. This is engineering connectivity,
not full scientific protocol equivalence to historical raw-audio comparators.
The stopped strict-cache qualification remains stopped.

At15:24:54UTC, the unit attempt durably recorded1060 calls. Sampled utilization
integral was0.76630 GPU hours; the full-roster projection was1.15162 against
the original1.2 cap. This projection is provisional. The root watches actual
contact counters and the10-second monitor, without reading unsealed quality.
The self runtime completed CPU preflight/preprocessing in687.8 seconds with
zero model contacts and remains resident, waiting for its own root lease.

The authoritative external live record is
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-dr-gpu-live-handoff.json.
It identifies service/worker handles, frozen source, budget observations,
prepared runtime, and the one allowed next action. The derivative/scoring
handoff v2 binds all four declared jobs and reviewed source; no private
experiment framework is required.

## Next execution order

1. Finish and verify the unit parent seal. Release its root lease only after
   seal or explicit abort; preserve the resident service.
2. Issue the self parent lease on the same service and command its already
   prepared runtime to generate. Do not launch a duplicate worker.
3. Build unit constrained/free deliveries through the shared deterministic
   builder, preserving the raw parent. Score both complete manifests
   sequentially while self generates, retaining per-sample statistics on the
   first official score.
4. Complete the LOOP judge/twin exact-slice inventories and combined deduplicated
   input inventory. Register one dedicated offline GPU encoding window, then
   promote formal packets and fit actual selected requests. Preserve the two
   plans and the family1.0 GPU-hour generation cap.
5. Seal self, build both derivatives and finish their complete scores. Publish
   all four DR comparisons, delivery/fallback counts, cost and attribution.
   Natural-mixture and inherited equal-call readings retain their meanings;
   sector and sample-rate tables are additional sensitivities. See
   [the saved-score admission](2026-09-10-e21-dr-saved-score-analysis-admission.md).
6. Run eligible LOOP judge/twin, then choose complete-system components from
   formal decisions and complete inherited necessary repeats. Failed G2
   descendants remain held.

## Complete-system implementation boundary

The shared SLURP phase-direct-then-slots-v1 program and actual sealed-state
transfer exist. Its live baseline fragment is held pending a real experiment,
two-stage capacity/budget registration, matched control and delivery binding.
Existing one-stage or sealed-predecessor runs cannot substitute for this test.

Current E21 OJW execution supports direct requests and repair from a sealed
historical predecessor. Reviewer flags are recorded, and phase_review explicitly
refuses on_flag=loop. Therefore an executable live initial-draft, planner and
conditional re-listen path remains to be integrated into the shared controller
and OBS execution. Preserve unique state/contact identities and actual cost
ceilings; Reviewer supplies flags, Planner chooses continuation, and the frozen
Solver retains answer authority. Do not label the four-row bridge or current
component DR/LOOP as a completed live system.

Root will define that bounded integration after the component decisions.
This remaining work does not pause the current GPU queue. CPU preparation stays
within a global8 workers during generation, official scoring runs one complete
job at a time, and active source checkouts remain frozen until closure.
