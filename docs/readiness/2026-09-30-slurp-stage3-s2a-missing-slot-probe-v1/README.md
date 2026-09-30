# S2a missing-slot proposal probe: registration package skeleton (HELD, DRAFT, NOT REGISTERED)

**State: HELD draft skeleton.** This directory holds this README only. It contains no plan, protocol, fit plan, facts,
recipe, roster derivation, config fragment, exposure-ledger row or stage-3 measurement block. No gate should read
anything here as a registered cell. Nothing may fly from it. The design is
`docs/superpowers/specs/2026-09-30-slurp-s2a-missing-slot-proposal-probe-design.md`.

## Blocking items, in order

Registration waits for these. Each item names its own authority.

1. **An owner row extending decision 201's transcript exception** from post-delivery verification to Solver-side
   *proposal* of candidate values (design section 5, item 1).
2. **The S2a.1 offline read** (zero contacts), reviewed with the owner. It covers:
   - the tool's recall ceiling T on the 70 not-in-supply MISSING items of COMP-1b Fold A;
   - the tool's false-candidate rate;
   - the abstain threshold fitted on TRAIN Fold B.
3. **An owner row for the DEV-2000-ADDED E5-0 pass** (a `speech-tool` ledger row written before contact), unless the
   owner moves the probe to Fold A (item 4).
4. **The owner's ruling on fold discipline:** DEV-2000-ADDED as briefed, or COMP-1b Fold A, or DEV with the probe ids
   excluded from S2c.
5. **The build:**
   - the `saea-tool-missing-slot-proposal-v1` wrapper and its catalog pin;
   - `phase_tools` admission of the tool;
   - the `tool-offer:missing-slot-proposal` module component (`pending` until built);
   - the `tool_offer_slot_types` carrier hook;
   - the chosen offer-arm form (design section 5, item 5).

## What the registered package will contain (planned, not present)

Everything below is written by script, from the A2 fragment `configs/experiment/slurp-native-stage3-comp1b-dev2000-added-v1.json`,
only after items 1-5 close. The planned contents are:

- **Two runs in one chain.**
  - Offer arm: `SAEA-SLURP-STAGE3-S2A-PROPOSAL-PROBE-V1`.
  - Twin: `SAEA-SLURP-STAGE3-S2A-PROPOSAL-PROBE-TWIN-V1`.
  - Each has its FIT sibling. Every one of these ids is a placeholder.
- **The roster derivation** from `scripts/analysis/slurp_s2a_probe_roster.py`. It carries the stratum P and stratum R
  counts, the id-list sha256 and the split identity. It carries no types and no item maps.
- **A `form-proof` measurement block** with `claims_benefit` false and `expected_effect_pp` 0.0. The block states the
  re-declaration arithmetic of design section 2, but does not apply it.
- **An analysis recipe** covering:
  - the delivery and pin checks;
  - the per-stratum quantities of design section 2;
  - the paired net conversion, with Wilson and Clopper-Pearson intervals;
  - the whole-roster prediction by exact re-score.
- **Budgets:** about 0.6-1.1 GPU-h expected, with a cap of 2.0. The contact ceiling is computed by the loader.
- **Failure policy:** at most one recovery re-registration.

## Prohibitions carried from the design

The prohibitions follow CONV and KPROBE:

- no pooled, roster-level, effectiveness, superiority or generalisation claim;
- no admission mode;
- no test-split contact;
- no system-default tool invocation;
- no gold, type or per-row hint in any runtime file;
- no flight before a root decision receipt and a flip.
