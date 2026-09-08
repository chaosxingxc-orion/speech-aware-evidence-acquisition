# The OBS-E1b transport unit, v3: v2's turns, each with its own context

Exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V3` (`model-free-check`), registered before the build
and closed after. **Zero frozen-core, diarizer, GPU, server, socket, tokenizer, tool, embedder,
network, audio-decode and paid-API contacts.** Unlike v1 and v2 this build opens no waveform at
all: the turns were cut from the sealed slices once, and v3 does not re-cut them.

| | |
|---|---|
| what asked for it | `docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md`, candidate (a): 93.4 % of OBS-E1's 61 excess PERSON errors sit within three seconds of a unit boundary, 78.7 % inside units under ten seconds, and BOTH edges are damaged — the shape of a missing-context failure, not of a truncate-at-the-tail one |
| predecessor, and the only input | `SAEA-E21-MF-SPEAKER-TURN-UNITS-V2`, `docs/receipts/obs/e21-speaker-turn-units-v2.json`, sha256 `0f5f0139…8eb03b`, re-read at that pin |
| population | all 44 `earnings21-original` discovery calls, split identity `fcc1b0bc…d69e` (inherited, not re-derived) |
| module / runner | `analysis/e21_speaker_turn_units.py` (`context_bounds`, `add_context`, `assert_context`) · `scripts/e21_speaker_turn_units_build.py --schema-version v3` |
| plan | `docs/receipts/obs/e21-speaker-turn-units-v3.json`, sha256 `b2cb3899531187329b09218d0e09e3003407d0e84918122bc8d8541d08b75976` |
| tests | `tests/unit/test_e21_unit_plan_v3.py` |

**This receipt registers no cell, admits nothing and licenses no contact.** OBS-E1 stays REJECTED
under its own preregistered rule; this file describes a plan, and a plan is data.

## 1. What v3 adds, and what it refuses to move

v3 is a **derivation of the committed v2 plan**. Every unit's span, duration, speaker, dominance
share, speaker count, start cut, end cut, active-frame flag, flags, absorbed slivers and
reference-word range are v2's, and the builder asserts that field by field, on all 5,122 units,
before it writes a byte. `assert_tiles` — v1's own proof obligation — is re-run on the turns.
So the **transport unit is unchanged**; what changes is only the audio delivered for it.

Each unit gains four numbers: `context_start_seconds`, `context_end_seconds`,
`context_left_seconds`, `context_right_seconds`, plus the derived `delivered_cut_seconds` and
`delivered_seconds`. The rule (`context_bounds`) is:

1. **a nominal 5.0 s margin on each side.** 5.0 s is the middle of the three margins the harm
   decomposition priced (+3 / +5 / +10) and the one whose worst request that section measured at
   1,323 tokens against a 6,144-token slot;
2. **a floor of 10.0 s of delivered cut** — a short turn is given *more* context, never less;
3. **a ceiling of 90.0 s of delivered cut**, which is `MAX_UNIT_SECONDS`, so a long unit receives
   less context or none;
4. the extra seconds are split **evenly** between the two sides, and a side that runs out of call
   hands its remainder to the other side.

**The ceiling is the load-bearing choice.** `reproduction.obs_loop._load_unit_plan` already refuses
any unit longer than `obs_buffer_seconds`, and the slot receipt certified the 90-second window at
2.72x against the 6,144-token slot. Capping the *delivered* cut at the same 90 s means that refusal
keeps passing untouched, the slot needs no re-certification, and the units that receive nothing are
exactly the ones the measurement says need nothing: units of sixty seconds or more were **better**
in OBS-E1 than in the comparator, by seven errors.

The floor never binds on this plan (`units_raised_to_minimum` = 0) and that is arithmetic, not
luck: v2 leaves no unit under 1.0 s, so turn + 2 x 5.0 s is at least 11.0 s for every unit. It is
kept as a stated rule because a future plan with a smaller minimum would need it.

## 2. What the plan costs

| | v2 (OBS-E1, as flown) | **v3** |
|---|---:|---:|
| calls | 44 | 44 |
| units = contacts | 5,122 | **5,122** |
| turn seconds cut | 141,345.853 | **141,345.853** |
| context seconds added | 0 | **49,968.499** |
| delivered cut (turn + context) | 141,345.853 | **191,314.352** |
| delivered with the 2.0 s tails | 151,589.853 | **201,558.352** |
| against the comparator's 141,345.853 s | 1.0725x | **1.4260x** |
| delivered cut, min / median / max | 1.09 / 25.78 / 90.00 | **11.00 / 27.78 / 90.00** |
| mean delivered cut | 27.596 | **37.351** |

**Contacts do not move** — the factor is what each contact carries, not how many there are.

### Where the context goes

| turn duration | units | share | turn seconds | context seconds | mean context per unit | mean delivered cut |
|---|---:|---:|---:|---:|---:|---:|
| **< 10 s** | 2,006 | 39.2 % | 8,866 | 20,060 | **10.00** | **14.42** |
| 10–60 s | 2,284 | 44.6 % | 70,570 | 22,840 | 10.00 | 40.90 |
| ≥ 60 s | 832 | 16.2 % | 61,909 | 7,068 | 8.50 | 82.91 |

4,874 of the 5,122 units receive the full 10.0 s; 248 are trimmed by the 90 s ceiling and 15 receive
none at all. 52 units are clamped on the left (they sit at a call's start) and 53 on the right.

### The overlap the stitch needs

Every boundary between two units is delivered to both of them. Over the 5,078 boundaries the shared
region is **10.0 s at the median**, 15.0 s at most, and **0.0 s on seven of them** — the seven where
a 90-second unit's ceiling left no room. Those seven fall to the ownership stitch's `no-overlap`
rule, which is byte for byte what a v1/v2 plan already does.

## 3. What `assert_context` refuses

Five properties, checked on every unit of every call before the plan is written, each a refusal and
never a repair: the context stays inside the call; it covers its own turn; the delivered cut meets
the 10 s floor (or the whole call is shorter than it); it stays under the 90 s ceiling; and **each
turn boundary lies inside the audio both of its units received**, which is the property that makes
the region around it transcribed twice and therefore alignable.

One property is deliberately **not** asserted: that the context bounds are ordered across units.
They are not, and need not be. Call `4320211`'s first unit is a 37.39 s turn at the very start of
the call: it has no room on its left, spends its whole 10 s margin on the right, and its delivered
span `[0, 47.39)` swallows the next unit's `[32.39, 44.05)` entirely. The ownership stitch resolves
each boundary from **its own** pair of units, so extra coverage costs delivered seconds and nothing
else. The build measured this rather than assumed it, and the assertion was rewritten to the
property the stitch actually needs.

## 4. What this receipt cannot conclude

* **Nothing about OBS-E1's status.** It stays REJECTED. This plan is a design input to a
  preregistered successor, not an amendment.
* **Nothing about whether context helps.** The harm decomposition's "addressable share" is a
  ceiling on what a mechanism could reach, never a prediction that it will; no arm has been flown
  with this plan and none is authorized.
* **Nothing about the stitch.** The plan says which audio is delivered. Which words a unit then
  owns is `reproduction.obs_ownership`'s question, decided and proved under exposure row
  `SAEA-E21-MF-OBS-E1B-SEAM-V1`.
* **The delivered-second totals are the plan's own arithmetic**, exact by construction; the GPU-hour
  and wall-clock consequences are projections and live in the preregistration, labelled as such.
