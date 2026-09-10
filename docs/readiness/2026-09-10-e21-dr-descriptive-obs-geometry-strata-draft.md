# Draft registration: E21 DR descriptive OBS-geometry strata

**Status: draft for owner review. Do not use these fields for admission, primary
gates, interval claims, or any effectiveness decision.**

## Purpose and scope

This draft registers a descriptive, content-free join between the frozen
OBS-E1 unit plan and the current E21 DR fixed-window roster. It introduces
window-level geometry descriptors only. It does not read a response, reference,
score, treatment outcome, model trace, tokenizer result, or bootstrap draw.

The source unit-level harm tables remain historical OBS-E1 evidence. The new
window aggregates below were not inherited preregistered strata. They can
describe composition after the owner approves this draft, but cannot alter the
DR primary gates or select a population, metric, threshold, or comparison.

## Frozen inputs

| Input | SHA-256 |
|---|---|
| OBS speaker-turn unit plan v3 | `b2cb3899531187329b09218d0e09e3003407d0e84918122bc8d8541d08b75976` |
| DR window metadata | `1c5a7c34e208a4148aa1d2d92f97f2116667285cd77dccdaa5ac990335046e75` |
| DR call metadata | `5631d6fee9ba032f95abdabf2f9ec9e7fc680b6fe9deb48cc37e50d72a12af23` |
| DR metadata preparation receipt | `bd427dae68dda3ac3b8bcb18ccb0577f55a9c74634df0dcc546cf8af4f69bb1e` |
| Geometry receipt | `3549a0a9cfcce25ef8114d73834f93b668984b7998313d8234b869606b048b20` |

The external geometry receipt is
`DATA/coordination/e21-dr-obs-v3-geometry-audit.json`. It records 44 calls
and 1,593 fixed windows, with every window covered exactly once by the union of
its same-call v3 unit overlaps. It refuses a unit-plan gap, an overlap, a
missing call, a duplicate window ID, or a window whose overlapping-unit
durations do not sum to its own duration.

The v3 plan records source window-row SHA-256
`e2e7da6ff07b4539a8bebd6adb040125344fbeaf6fd4be08db889b3a6827f800`.
The DR metadata names historical roster SHA-256
`98d431f24f6d94a4f08c1830ca08ed271106d33d660ac40d0fa93a1c3d7db144`.
They differ. This draft establishes coordinate coverage by sample ID, fixed
window index, and time bounds; it does not assert byte identity between those
two roster documents.

## Proposed descriptive variables

For a DR window `W=[w_start,w_end)` and a same-call unit
`U=[u_start,u_end)`, define overlap duration as
`o(W,U)=max(0,min(w_end,u_end)-max(w_start,u_start))`. Include a unit only
when `o(W,U)>0`.

- **Overlap-duration-weighted mean unit duration:**  
  `sum(o(W,U) * duration(U)) / sum(o(W,U))`.

- **End-cut composition:**  
  For every recorded `end_cut` kind, retain the number of overlapping units
  and `sum(o(W,U))` seconds. The receipt retains the complete observed
  category mapping rather than collapsing it or assigning a quality direction.

- **Internal unit-boundary count:**  
  Count each tiled v3 unit end exactly once when
  `w_start < unit.end_seconds < w_end`. A boundary exactly on a fixed-window
  edge belongs to neither window interior.

- **Existing speaker dominance:**  
  Retain it as a separate historical descriptor. Do not combine it with these
  geometry variables or infer speaker dominance from an overlap-weighted
  average.

The receipt records 5,078 internal unit boundaries across all fixed-window
interiors. This is a geometry count, not a harm count or a treatment result.

## Historical definitions retained as provenance

The historical unit duration, nearest-boundary, and `end_cut` definitions
are in
`docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md`
(lines 106éÝyø§yÓ113, 16:éÝyø§yÓ177, 192éÝyø§yÓ207, and 217 onward) and its machine-readable
counterpart
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-person-harm-decomposition/person-harm.json`.
The v3 coordinate and `end_cut` serialization is defined by
`src/speech_aware_evidence_acquisition/analysis/e21_speaker_turn_units.py`;
the pinned plan loader is
`src/speech_aware_evidence_acquisition/reproduction/obs_loop.py`.

These references do not transfer the old unit-level harm strata to DR
windows. The proposed variables are new descriptive geometry aggregates and
must remain labeled as such.
