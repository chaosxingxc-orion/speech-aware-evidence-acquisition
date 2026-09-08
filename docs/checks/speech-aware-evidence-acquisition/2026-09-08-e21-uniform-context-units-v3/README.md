# The OBS-E1b form twin's plan: equal clock units, the same context

Exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V3` (`model-free-check`) — the same row the arm's plan
was built under, because this is the same builder run with one flag. **Zero contacts of every kind,
and no waveform opened.**

| | |
|---|---|
| plan | `docs/receipts/obs/e21-uniform-context-units-v3.json`, sha256 `10a7e5d7736a1523211926dc1ec6322eb9fe73427c8ff9abc3e358bf0464d1f8` |
| arm it is the twin of | `docs/receipts/obs/e21-speaker-turn-units-v3.json`, sha256 `b2cb3899…b75976` |
| builder | `scripts/e21_speaker_turn_units_build.py --schema-version v3 --from-plan <v2> --uniform-seconds 27.60` |
| inherited from the source plan | the 44-call roster and each call's `decoded_duration_seconds`, and nothing else |

## What it varies, and what it holds

**One thing varies: where the boundaries are.** Each call is cut into equal 27.60-second clock units
instead of into its diarized speaker turns, and then given the arm's own context rule — the same
5.0 s nominal margin, the same 10.0 s floor, the same 90.0 s ceiling, the same even split with the
call-bound clamp — and delivered through the same ownership stitch, the same instruction, the same
arm, the same geometry and the same harness.

| | arm (speaker turns) | **twin (uniform 27.60 s)** |
|---|---:|---:|
| units = contacts | 5,122 | **5,144** (+0.43 %) |
| turn seconds cut | 141,345.853 | **141,345.853** |
| context seconds | 49,968.499 | **51,440.000** |
| delivered cut | 191,314.352 | **192,785.853** (+0.77 %) |
| delivered with the 2.0 s tails | 201,558.352 | **203,073.853** |
| mean delivered cut | 37.351 | **37.478** |

Contact count, delivered seconds, the context mechanism and the stitch are matched; the cut is not.
That is the whole design: if the arm improves and the twin does not, the speaker-turn cut is what
worked; if both improve equally, the extra audio is.

**27.60 seconds is not a new number.** It is the contact-matched control the OBS-E1 preregistration
itself named as OBS-E1b (`decision.equal_contact_question`) and deliberately declined to register
while OBS-E1 was in flight.

## Two honest asymmetries

* **No reference-word ranges.** The sealed per-window reference-word counts were partitioned over the
  SPEAKER turns; re-interpolating them onto clock units would invent an attribution nothing measured.
  The seam never reads the field and the twin's numbers come from the scorer.
* **No speaker facts.** A clock unit has no dominant speaker, so `speaker` is null, `speaker_count`
  is 0 and every unit is flagged `uniform-clock-unit`. The arm's duration and speaker strata do not
  exist on this plan and are not invented; the twin's own strata are the realized context seconds,
  the boundary ownership rule and position in the call.

One unit of the 5,144 falls under 1.0 s — the remainder of a call whose duration is nearly a multiple
of 27.60 s. That is the fixed-window cutter's own behaviour on its last window, kept rather than
patched, and it is reported here rather than hidden.

## What this receipt cannot conclude

Nothing about either cell's effect. This is a plan, and no arm has been flown with it. The twin is
preregistered in `docs/readiness/2026-09-08-e21-obs-e1b-context-units-v1-preregistration.md` §5 and
waits on the ARM's verdict, its own exposure row and the owner's GO.
