# E21-LOOP-1 wire check — `SAEA-E21-MF-LOOP-1-PREP-V1`

**Zero contacts, zero sockets.** Nothing here constructs a transport, a gate, an attempt store or a
`core.model.FrozenCoreAdapter`; no audio file is opened and no MP3 is decoded, so the pinned absence
of `ffmpeg` is preserved. The only bytes read are the committed fragments and plans, the sealed
comparator's own `outputs.jsonl`, and the hash-verified predecessor artifact.

Runner: `scripts/e21_loop_1_wire_check.py`. Machine-readable half: `wire-check.json`. The cell's
reasoning, its decision rule and its claim surface live in
`docs/readiness/2026-09-08-e21-loop-1-v1-preregistration.md`.

## What it certifies, in four halves

**`config` — the cell composes, and the one factor survives composition.** Both cells reach a
composed config and protocol hash against the roster's own split identity. The arm's BASELINE
fragment differs from KC-E1f's in exactly four keys — `obs_unit_plan`, `obs_unit_plan_sha256`,
`window_review`, `window_observe` — and from the twin's in exactly the same four. Prose keys are
excluded by name from that comparison and the serving geometry is reported as a separate, named
difference: this cell projects the np6 fragment where KC-E1f flew np4, and a prompt fit in SERVER
mode decides it before the first flight contact.

**`plan` — both plans are real, and the twin is a form control rather than a second cell.** Each
plan loads through the real `reproduction.obs_loop` loader, which re-proves it on the bytes it
actually loaded: units in order from 1, one per parent window in ascending order, every unit inside
its named parent window, every unit at or above the refusal-to-shrink floor, and a non-empty word
range inside that window's own pass-1 word count. Both cover 44 of 44 roster calls. The fragment's
declaration is checked against the plan's own provenance, so a fragment that claims one Reviewer and
pins a plan built by another is refused before any contact. And the twin matches the arm on **contact
count and re-cut duration multiset, per call, on 44 of 44 calls**.

**`request` — the rendered request is the one the plan describes, and the floor is the comparator.**
The real `RepairWindowHook`, over the real hash-verified predecessor binding, on four calls:

1. every rendered instruction **ends with exactly** the plan's word range of that window's own
   pass-1 text — an equality on the frame's tail, so it pins the frame, the join and the word range
   in one assertion and cannot be satisfied by a longer span that merely contains the right one;
2. a **fully refused pass 2 rebuilds the sealed comparator's own hypothesis for the call, byte for
   byte** — the selective loop's version of KC-E1f's "a useless pass-2 answer costs nothing", and
   the reason this cell's floor is the comparator by construction;
3. contacted plus back-filled windows equal the call's window count, so the selective plan loses no
   window and the paired read is still over the same 1,593 units.

**`payload` — the cell is wire-ready.** The shared `rails.core_client.payload_binding_stage` over
the cell's own 44-row roster, through the real carrier root, binds.

## What it does NOT certify

It records a composition, a plan proof, a rendered request and a payload binding. It says nothing
about the geometry's throughput, nothing about any score, and it is not a permission: E21-LOOP-1
still needs the owner's GO to fly, and owner Decision 12-G of 2026-09-08 authorized the model-free
preparation only.

## Files

| file | what it holds |
|---|---|
| `wire-check.json` | the whole result: both cells' identities, the two functional diffs, the serving-geometry note, both plans' statistics, the twin's agreement counts, the per-call request half and the payload-binding stage |
| `MANIFEST.sha256` | this directory's byte manifest |
