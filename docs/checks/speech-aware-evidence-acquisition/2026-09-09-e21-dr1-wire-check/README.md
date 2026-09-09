# DR-1 wire check and geometry projection — `SAEA-E21-MF-DR1-PREP-V1`

**Zero contacts, zero sockets.** Nothing here constructs a transport, a gate, an attempt store or a
`core.model.FrozenCoreAdapter`; no audio file is opened and no MP3 is decoded, so the pinned absence
of `ffmpeg` is preserved. The only bytes read are the committed fragments and receipts, the two
sealed runs' own `outputs.jsonl`, and the two hash-verified snapshot artifacts.

Runners: `scripts/e21_dr1_wire_check.py` and `scripts/e21_dr1_prompt_fit.py --projection-only`.
Machine-readable halves: `wire-check.json`, `projection.json`. The family's reasoning, its decision
rule and its claim surface live in
`docs/readiness/2026-09-09-e21-draft-then-refresh-dr1-v1-preregistration.md`.

## What the wire check certifies, in four halves — RESULT PASS, zero failures

**`config` — the three cells compose, and the one factor survives composition.** Each reaches a
composed config and protocol hash against the roster's own split identity. DR-1c's baseline fragment
differs from **DR-1f's** in exactly `response_postprocessor` and `response_postprocessor_params` —
the delivery rule and the parameters only the bounded rule accepts — and from **DR-1s's** in exactly
`predecessor_snapshot`. Against **KC-E1f's** it differs in exactly the six keys a knowledge-free
refresh is entitled to move: `arm`, `evidence_source`, `brief_max_entries_per_class`,
`predecessor_snapshot`, `repair_frame` and `task_instruction`. Two prose claims the fragments make
are asserted rather than trusted: the three cells share ONE `task_instruction`, and that instruction
**ends with the sealed comparator's own instruction, byte for byte**. The serving geometry is
reported as a separate, named difference — DR-1 projects np6 where KC-E1f flew np4 — and never folded
into the one-factor claim.

**`request` — each arm's floor is its own draft, measured rather than argued.** The real
`RepairWindowHook`, over both real hash-verified bindings, on four calls (160 windows):

1. every rendered instruction **equals** the fragment's own instruction plus the frozen frame filled
   with that window's draft — an equality, not a substring search, so it pins the frame, the join and
   the window-to-draft mapping in one assertion;
2. when every pass-2 answer is refused, the two unit-draft cells deliver the **sealed OBS-E1
   hypothesis** for the call byte for byte, and the self-draft twin delivers the **sealed
   comparator's**, byte for byte, on 4 of 4 calls each. So DR-1c and DR-1f cannot land below OBS-E1's
   transcript and DR-1s cannot land below the comparator's — and the two arms of the family have
   *different floors*, which is a fact about the design and is stated here rather than discovered in
   a verdict;
3. the two delivery rules **agree on every refusal** — an empty response and an empty draft deliver
   the same bytes under both — so the DR-1c/DR-1f contrast is a contrast about edits and not about
   saturation handling;
4. every window of the call is delivered exactly once.

**`delivery` — a divergence probe, labelled as a probe in its own receipt.** It feeds each window's
hook the **comparator's own sealed hypothesis** as if it were the pass-2 response — real text of
exactly the kind a refresh returns, and the only such text this repository can produce without a
contact — and reports what each rule would then deliver. Over the same 160 windows the bounded rule
**refuses 14** (7 by the anchor floor, 7 by the substitution ceiling), **changes 132** and accepts
**654** substitutions, while the free rule would move **8,907** whitespace tokens of absolute count
difference. It predicts nothing about the core. It measures how far the two rules are apart, which is
the quantity the family's guards are set against, and it is also the check that the bounded rule
never moves a window's token count on real text.

The same 160 windows carry **37,338** whitespace tokens of unit draft against **37,913** of
comparator draft — a 1.5 % difference, which is the twin's token match reported as a measurement.

**`payload` — the family is wire-ready.** The shared `rails.core_client.payload_binding_stage` over
the cells' own 44-row roster, through the real carrier root, binds.

## What the projection says about the geometry

Model-free, and it projects from two measurements rather than from a characters-per-token guess: the
comparator's own sealed per-window prompt tokens (which already *are* speech plus template plus the
comparator's instruction) and each binding's sealed draft tokens.

| cell | draft flight tokens (max) | worst request | np6 slot 6,144 | np4 slot 9,216 |
|---|---:|---:|---:|---:|
| DR-1c / DR-1f | 596 | **2,954** | **2.080×** | 3.120× |
| DR-1s | 445 | **2,803** | **2.192×** | 3.288× |

Both clear the study's `slot_tokens >= 2 * worst_required` rule at the declared np6 geometry, with
little room. The threshold is written down **before** the fit measures it: the declared geometry stops
satisfying the rule once the added envelope — one leading instruction sentence plus the frame's fixed
wording, assumed at 100 flight tokens for 103 whitespace tokens — reaches **240** tokens, 2.4 times
the assumption. Lever 1 of the fit's own pre-fixed procedure then takes np4, which carries the same
worst request at 3.120× and changes no request byte.

## What neither of them certifies

They record a composition, a rendered request, a delivery probe, a payload binding and a projection.
They say nothing about any score, nothing about what the core will return, and nothing about the
geometry's throughput. **A projection is not a fit**: token counts are not additive across a chat
template's joins, so the SERVER fit — `scripts/e21_dr1_prompt_fit.py` with no `--projection-only` —
is the flight agent's step, opens a session, and needs its own registered exposure row. The three
DR-1 cells still need the owner's GO to fly and do not have it.

## Files

| file | what it holds |
|---|---|
| `wire-check.json` | all four halves: the three cells' identities, the three functional diffs, both bindings' hashes, the per-call request half with its floor proofs, the refusal-agreement rows, the divergence probe and the payload-binding stage |
| `projection.json` | both bindings' token distributions, each cell's worst request, the added-envelope sensitivity ladder, the slot sweep and the completion-ceiling sweep |
| `MANIFEST.sha256` | this directory's byte manifest |
