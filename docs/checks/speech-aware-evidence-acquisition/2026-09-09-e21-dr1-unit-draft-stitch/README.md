# DR-1 unit-draft stitch — `SAEA-E21-MF-DR1-PREP-V1`

**Zero contacts of every kind.** No model, GPU, server, socket, tokenizer, tool, embedder or network;
no MP3 is decoded and no audio is resampled, so the pinned absence of `ffmpeg` is preserved. No
reference transcript, `wer_tags` sidecar, gold label or scorer is opened. Six sealed files are read —
two run manifests, two `outputs.jsonl` and two `trace.jsonl` — and nothing else.

Builder: `scripts/build_e21_unit_draft_snapshot.py`. Rule:
`analysis.e21_unit_draft_stitch` (`saea-e21-unit-draft-majority-overlap-v1`). Machine-readable half:
`stitch-proof.json`. Committed binding:
`docs/receipts/e21-unit-draft-obs-e1-speaker-turn-units-v1.json`. The family this feeds, its decision
rule and its claim surface live in
`docs/readiness/2026-09-09-e21-draft-then-refresh-dr1-v1-preregistration.md`.

## What it is

Owner Decision 13-J asks for a draft-then-refresh episode: the Observe stage uses the SHORT speech to
draft quickly, and the Plan stage hands the model the LONG speech together with that draft. The short
half is already sealed — `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` decoded all **5,122** speaker-turn
units of the 44 discovery calls — so DR-1's pass 1 is READ, not re-flown, exactly as KC-E1f read the
comparator's.

This receipt is the arithmetic between the two grids, and nothing else. It moves no audio, aligns no
words and runs no forced alignment: it decides, per unit, which of the comparator's **1,593** sealed
90-second windows owns it, and concatenates.

**The rule.** A unit is owned by the window it overlaps most in seconds; a tie goes to the earlier
window (windows are scanned in ascending index and an overlap must be strictly greater to displace
the incumbent, so the rule is deterministic and needs no second sort key). A window's draft is its
owned units' sealed texts joined by `reproduction.obs_loop`'s own stitch rule — a single space, empty
texts contributing nothing.

## What it proves, in the order the proofs must hold

1. **Each sealed run rebuilds itself.** `analysis.e21_window_pairing.assert_stitch_reproduces_outputs`
   refuses unless every recovered call rebuilds its own sealed `outputs.jsonl` hypothesis byte for
   byte — run on the comparator (1,593 windows, 44 calls, 0 saturated, 439,532 completion / 1,935,965
   prompt tokens) and on the unit run (5,122 units, 44 calls, 3 saturated, 445,342 / 2,255,812). Both
   sets of counts are checked against the numbers those runs' own verdicts publish, so the build is
   checked against a claim rather than against whatever it happens to find.
2. **Ownership is a monotone partition.** Units tile their call in ascending time and windows do the
   same, so the owning window index is non-decreasing in unit index — asserted, because without it
   the stitch would reorder the call's own words. All **5,122** units are owned exactly once.
3. **The drafts rebuild OBS-E1's corpus text.** Per call, concatenating the per-window drafts equals
   the sealed OBS-E1 hypothesis for that call, **byte for byte, on 44 of 44** — asserted against the
   sealed `outputs.jsonl` directly rather than through proof 1, so the chain is checked end to end.
4. **Every drafted row names the comparator's own window.** Id, index and all three bounds, to 1e-9 s.
   `reproduction.repair_loop.RepairWindowHook` matches a cut window against its bound predecessor's
   bounds to 1e-6 s and refuses otherwise; a drift would fail at a flight's first contact, so it
   fails here instead.

## The two windows that own no unit, reported rather than smoothed over

A window shorter than the unit covering it loses every tie. That happens exactly **twice in 1,593** —
`4361631#w0050` (1.429 s) and `4387865#w0025` (2.573 s) — and both are the **last, remainder window
of their call**. The corpus loses nothing: the words spoken there are inside the covering unit's
text, and that text is delivered by the preceding window, which is why proof 3 still holds byte for
byte. Their draft is the empty string, and both DR-1 delivery rules refuse an empty draft as
`empty_predecessor` and deliver the empty string, so the constrained and the free arm treat those two
windows identically.

## The token accounting, and the one place it needed care

A window's draft cost is the sum of the sealed OBS-E1 completion-token counts of the units **whose
text is in the draft** — the server's own counts on the flight tokenizer, so the prompt fit projects
from a measurement rather than from a characters-per-token guess. A **saturated** unit spent its
1,024-token cap and contributed the empty string (`obs_loop`'s quarantine), so charging its tokens to
a prompt fit would inflate three windows by a whole cap each. Both figures are therefore reported:
the owned-unit total is **445,342**, conserved to the digit against the sealed run; the draft total is
**442,270**; and the difference is exactly **3,072 = 3 × 1,024**.

| distribution, per window | min | median | p95 | max |
|---|---:|---:|---:|---:|
| units owned | 0 | 2 | 8 | 16 |
| draft characters | 0 | 1,312 | 2,050 | 2,794 |
| draft whitespace tokens | 0 | 229 | 361 | 505 |
| **draft flight tokens** | **0** | **273** | **432** | **596** |
| comparator's own pass-1 prompt tokens | 75 | 1,232 | 1,232 | 1,232 |

## What it does NOT do

It records an arithmetic regrouping of two sealed runs. It scores nothing, admits nothing and
authorizes nothing: no cell is registered to fly, `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` stays
REJECTED under its own preregistered rule, KC-E1f's admission stays provisional with its replication
UNMET, and OBS-E1b stays prepared and unflown.

## Files

| file | what it holds |
|---|---|
| `stitch-proof.json` | both runs' identity anchors, the three stitch proofs, the ownership distribution with the two empty windows named, and the token distributions |
| `MANIFEST.sha256` | this directory's byte manifest |
