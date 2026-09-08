# The OBS-E1 transport unit, v2: the coordinator's minimum-duration rule

Exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V2` (`model-free-check`), registered before the build
and closed after. **Zero frozen-core, diarizer, GPU, embedder, tokenizer, network and paid-API
contacts.** Built from the same two sealed inputs v1 used and nothing else; no reference text was
opened.

| | |
|---|---|
| coordinator's decision | 2026-09-08, under the owner's OBS-E1 GO: "a 16-sample unit wrapped in a 2-second tail is a diarizer artifact, not a transport unit" |
| predecessor | `SAEA-E21-MF-SPEAKER-TURN-UNITS-V1`, `docs/receipts/obs/e21-speaker-turn-units-v1.json`, receipt `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-speaker-turn-units/` |
| sources (identical to v1) | `SAEA-E21-TOOL-DIARIZATION-V1` (`attempt-20260907T045837Z-5b3f93`) and the sealed slices of `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (`attempt-20260904T233816Z-bcd338`) |
| reference-word source | `SAEA-E21-MF-WINDOW-PAIRING-V1`, sha256 `e2e7da6f…7f800` |
| population | all 44 `earnings21-original` discovery calls, split identity `fcc1b0bc…d69e` |
| module / runner | `analysis/e21_speaker_turn_units.py` (`plan_units_v2`) · `scripts/e21_speaker_turn_units_build.py --schema-version v2` |
| tests | `tests/unit/test_e21_speaker_turn_units.py`, 52 total (41 v1 + 11 v2) |
| plan | `docs/receipts/obs/e21-speaker-turn-units-v2.json`, sha256 `0f5f0139…8eb03b` |
| wall clock | 53.244 s, single process, CPU only, `CUDA_VISIBLE_DEVICES` empty |

Before this build ran, `plan_units` (v1) was rebuilt against the same two sealed inputs and diffed
byte for byte against the committed `docs/receipts/obs/e21-speaker-turn-units-v1.json`: **identical**
(sha256 `fed5188b86d672b2d2a9c8f1b55dc51fe5712776fc06cc938dc759854d52026a` on both). The refactor that
extracted `_base_spans` (rules 1-3, shared by both builders) changes no byte of v1's output.

## 1. The rule that changed, and the one that didn't

Rules 1 (never cross a diarized speaker change), 2 (snap onto a nearby pause), 3 (the 90 s cap) and
5 (the 2.0 s delivered tail) are v1's, byte for byte — `_base_spans` is the one piece of code both
builders call. **Rule 4 is replaced** by one explicit exception to rule 1: a span under 1.0 s now
merges into whichever ADJACENT unit is LONGER, of EITHER speaker, ties going to the PRECEDING
neighbour. The 90 s cap still holds — a merge that would break it tries the other neighbour, and a
sliver with no admissible neighbour on either side keeps its sliver and is flagged `short-kept`,
exactly as v1 flags one it cannot merge. Every merge is recorded on the surviving unit's
`absorbed_units` (the sliver's own span, its own dominant speaker, and whether absorbing it crossed a
speaker change), and the unit is flagged exactly one of `same-speaker-merge` / `cross-speaker-merge`.

## 2. Headline: v1 vs v2

| | v1 | v2 |
|---|---:|---:|
| units | 5,288 | **5,122** (-166, -3.1 %) |
| units under 1.0 s | **166** | **0** |
| duration min | 0.001 s | 1.001 s |
| duration median | 16.060 s | 17.775 s |
| duration mean | 26.730 s | 27.596 s |
| duration max | 90.000 s | 90.000 s |
| purity (`speaker_share`) mean | 0.9431 | 0.9506 |
| purity at/above 0.99 | 4,156 (78.6 %) | 4,033 (78.7 %) |
| total unit CUT audio | 141,345.852687 s | 141,345.852687 s (unchanged) |
| total unit DELIVERED audio | 151,921.852688 s | 151,589.852688 s (-332.0 s = -166 × 2.0 s tail) |
| reference words attributed | 359,765 | 359,765 (unchanged) |
| units with no reference word | 21 | 1 |

**The coordinator's "expected zero or near zero" landed at exactly zero.** Every one of v1's 166
sub-1.0-s slivers is absorbed by v2's rule; none is kept. Total cut audio is exactly conserved
(merging redistributes seconds between adjacent units; it creates and destroys none), and the
delivered-audio saving is exactly the removed units' tails, to the microsecond.

Duration distribution, pooled over all 5,122 units:

| min | p05 | p25 | median | p75 | p90 | p99 | max | mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.001 s | 1.750 s | 5.043 s | **17.775 s** | 45.750 s | 71.168 s | 88.088 s | 90.000 s | 27.596 s |

## 3. Merges: how many, and of which kind

166 pre-merge sub-1.0-s spans were absorbed (v1's own `_merge_short` absorbed 8 of these same 166,
all same-speaker; v2's rule absorbs all 166). They land on 166 surviving units:

| | count |
|---|---:|
| flagged `same-speaker-merge` (v1 would also have merged these — only the CHOSEN neighbour differs, since v1 always tries the preceding one first while v2 compares durations) | 13 |
| flagged `cross-speaker-merge` (the sliver's own dominant speaker differed from, or was silent against, the absorbing neighbour's — the one genuinely new behaviour) | 153 |
| **total merged units** | **166** |

174 absorbed-sliver records exist on those 166 units (159 units absorbed exactly one sliver, 6
absorbed two, 1 absorbed three: `159×1 + 6×2 + 1×3 = 174`) — a cascade where an already-merged unit
was itself still short enough to draw in a further sliver. The base-span count both builders share
before rule 4 (`_base_spans`'s output) is confirmed identical by closed-form arithmetic:
`5,288 (v1 units) + 8 (v1 merges) = 5,296 = 5,122 (v2 units) + 174 (v2 absorbed-sliver records)`.

**Purity is recomputed, not assumed.** Every merged unit's `speaker`/`speaker_share`/`speaker_count`
comes from the same `window_speakers` call v1 already makes, run over the merged unit's own new span
— so a cross-speaker merge visibly costs purity rather than silently keeping `speaker_share == 1.0`.
Corpus-wide purity mean rises slightly (0.9431 → 0.9506) because removing 166 fragmentary,
often-impure short units from the denominator outweighs the handful of merges that made a
previously-pure unit share its span with an absorbed sliver.

## 4. Section 4 strata, recomputed for v2

Same six strata the preregistration's section 4 reports for v1, recomputed at the v2 unit grain
(v1's own numbers in parentheses):

| stratum | grain | v2 distribution (v1) |
|---|---|---|
| dominance | `dominated` / `shared` at the 0.60 threshold | 4,916 / 147 (+59 silent) — v1: 5,034 / 153 (+101 silent) |
| speaker count | `speakers=0/1/2/>=3` | 59 / 3,898 / 1,126 / 39 — v1: 101 / 4,024 / 1,128 / 35 |
| unit length | `<1 s` / `1–10 s` / `10–60 s` / `>=60 s` | 0 / 2,006 / 2,284 / 832 — v1: 166 / 2,010 / 2,281 / 831 |
| cut kind (`end_cut`) | `pause` / `turn-boundary` / `forced-cap-split` / `call-end` | 4,387 / 676 / 15 / 44 — v1: 4,471 / 758 / 15 / 44 |
| the no-pause call | `4366522` alone | 36 units (v1: 38) — see §5 |
| sector and sample rate | the release's own two strata | unchanged from v1: the merge rule touches no metadata outside the cut |

`forced-cap-split` as an `end_cut` (15) and as a FLAG (23, both sides of a split) are identical
between v1 and v2 by construction, since rules 1-3 are shared and forced splits happen before rule 4
ever runs. The `<1 s` → `0` bucket is the headline; the small shifts in the `1-10 s` / `10-60 s` /
`>=60 s` buckets are the boundary units a merge pushed across the 10 s or 60 s edge, not new
population.

## 5. The no-pause call, apart

`4366522` (1,817.7 s, zero detectable pauses ≥ 300 ms) carries 36 v2 units against v1's 38: two
slivers merged. A 0.966 s same-speaker sliver at 1280.005–1280.971 s merged into its preceding
neighbour (`4366522#u0021`, flagged `same-speaker-merge`, `speaker_share` 0.913 after the merge), and
a 0.646 s sliver at 1585.765–1586.411 s merged across a speaker change into a `forced-cap-split`
neighbour (`4366522#u0027`, flagged `cross-speaker-merge`, `speaker_share` 0.990). All 36 units still
end on an active frame — the merge rule changes nothing about this call's total absence of pauses.

## 6. Tiling and coverage

`assert_tiles` passed inside the builder on every one of the 44 calls (the build would have raised
`SpeakerTurnUnitError` otherwise, and none did). It was independently re-verified against the WRITTEN
plan bytes after the fact (not only inside the builder that produced them): every call's units start
at 0, end at that call's own `decoded_duration_seconds`, abut with no gap and no overlap, no unit is
empty, no unit exceeds the 90 s cap, and no unit is under 1.0 s without carrying `short-kept`. All
44/44 calls carry units; every plan block's `decoded_duration_seconds` equals that call's own sealed
90-second window total to the microsecond; the attributed reference words sum to the sealed 359,765
exactly.

## 7. Claim surface

Discovery data. This row produces a transport UNIT and its tiling proof, not a result: no
superiority, generality, transcription-quality or Stage-3 claim, no knob tuned on the evaluation ten,
no Earnings-22 contact, no frozen-core contact. It licenses no flight — cell OBS-E1 needs its own
exposure row and the owner's GO regardless of which plan version it flies. It supersedes v1 as the
candidate transport unit for a future OBS-E1 flight; v1's own row and receipt stay in place,
unrewritten, as a record of what v1 measured.
