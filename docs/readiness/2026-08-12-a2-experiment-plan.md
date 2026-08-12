# Experiments on the A″ (a2) baseline — plan (2026-08-12)

Standing owner sequence closed by this plan's premise: featcache locked (HBM purchase measured),
batch locked (np8 bare + np8 evidence), baseline packaged
(`2026-08-12-hbmfree-baseline-verdict.md`, the consolidated A″ verdict). Everything below runs
on the a2 substrate: fixed windows, tail 0, slice-parallel ×8, featcache warm, mmproj off-GPU.
Naming map: Wave A2-1 here is the run the verdict doc queues as "E-005" — the formal ID is
assigned at registration time.

Phase note: the "no task over 30 minutes" rule governed the perf-tuning phase. The campaigns
below are science reads with per-arm walls beyond 30 min at n=10; they need the owner to close
the perf phase (decision point D-1 below). Fast-3 pilots stay inside the cap.

## Wave A2-0 — substrate hygiene (fast, no owner decision needed)

1. **Determinism re-pin on a2-evid** (~2×20 min, discovery): twice-run of
   `SAEA-BENCH-hbmfree-evid` shape to pin the evidence-arm noise floor (bare floor is 0.11 pp;
   evidence floor unmeasured). One registration, two attempts, paired per-sample read.
2. **Cold-start receipt** (one-off, ~25 min): one never-cached corpus slice set (e.g. 3 shortest
   E-22 samples) through a2-evid to price the CPU-encode cold pass and verify back-fill + next-run
   hits. Produces the operational rule for every future new-carrier campaign.

## Wave A2-1 — R4 re-read on the clean floor (the flagged question)

The n=3 flag (matched 0.1498 vs bare 0.1397) says the old R4 conclusion — context value =
domain priming, matched ≈ mismatched ≪ nocontext — was read on a floor 9 pp noisier than today's.
Re-run the three arms on a2: **nocontext / matched / mismatched × n=10 discovery split**.

- **Pilot first, no D-1 needed**: a fast-3 trio (~1 h as three <30-min tasks) re-reads the
  contrasts at n=3 against the noise floor from Wave A2-0. Graduation gate to the n=10
  triplet: any pre-registered contrast with |Δ| ≥ 0.5 pp (plus D-1).

- New fragments (no code): `fixed-batch-nocontext8` (matched8 minus evidence, instruction held
  constant with the matched arm per R4 design) and `fixed-batch-mismatched8`
  (`evidence_mismatch: true`). Both legal on the slice-parallel path (evidence constant
  per sample).
- Cost on a2: old era burned ~43 min per evidence arm on fast-3 alone; a2 read ~20 min. The
  n=10 set is ~5× fast-3 audio → ballpark **1.5–2 h per evidence arm, ~4–5 h the triplet** —
  under half the old-era price. Registration: one block, three rows, per-row caps sized from the
  probe-B rate.
- Readout: per-sample paired deltas (noise floor from Wave A2-0), the critical contrast
  matched-vs-mismatched (domain priming vs content use), and entity-slice WER once the scorer
  decision (D-3) lands.

## Wave A2-2 — E-003 evidence-form contrasts (the study's SUPPLY question)

With OBS efficiency settled, the science axis moves to SUPPLY form: same matched ConEC
content, varied presentation (placement is already locked by prompt_order v2; form axes:
digest vs raw, entity-list vs prose, dose curves within the measured ≤7.6k envelope). Each form
is one baseline fragment on a2-evid; slice-parallel makes a 4-form × fast-3 pilot ≈ 4×20 min,
inside the cap, before any n=10 spend. Pilot first, then the owner picks which forms graduate
to n=10.

## Wave A2-3 — carrier breadth (standing owner demand: not only E-21/E-22)

- **E-22 entry**: bare + matched arms on the E-22 discovery split (cold pass priced by Wave
  A2-0 item 2). E-22 has no ConEC layer — its evidence source decision (D-2) gates the matched
  arm; bare-core WER on a2 runs regardless.
- **ConEC-as-carrier** (its own audio, not just its contexts): needs the D-2 sourcing decision
  and a slot-size check against its evidence packs (≥9.2k ⇒ np drop or SUPPLY cap, per the
  verdict's sizing rule).

## Owner decision points

- **D-1**: close the perf-tuning phase (re-admit >30-min science runs at n=10)? Wave A2-1/A2-3
  are blocked on this; A2-0 and the A2-2 pilot are not.
- **D-2**: E-22/ConEC evidence sourcing for matched arms off E-21.
- **D-3**: entity-class WER scorer admission (carried from the W-A..W-D validation plan).
- **D-4**: after Wave A2-1, whether R4's conclusion stands, flips, or needs n beyond 10 —
  decides what E-003 inherits as its context prior.

Carried unchanged from the W-A..W-D validation plan (still open, owner-side): carrier
lock-profile batch policy; secondary-carrier engineering; confirmatory-touch disposition
id 4420696; audio2tool id collision SAEA-E-002→E-006; B-5/D-6 gaps. The registered
np16short bench (commit 95272dc) is recommended closed as not-pursued per the verdict's
disposition.

Sequencing: A2-0 immediately (fits today's cap), A2-1 fast-3 pilot next, A2-2 pilot after,
A2-1 n=10 on D-1 + pilot signal, A2-3 on D-1+D-2.
The W-A..W-D validation plan's perf-sensitive items (throughput, cost-model, batch-scaling
entries) recalibrate against a2 numbers as they execute; its science items are unchanged.
