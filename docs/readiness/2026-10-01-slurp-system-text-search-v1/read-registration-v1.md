# Bind feedback export to its exact registered READ

The whole-system reader already verifies complete-family membership, finalized
attempts, seals, official score receipts and TRAIN-only feedback. Its CLI did
not automatically verify the root READ countersignature required by the
registered protocol. That check depended on the operator. This correction
enforces the existing boundary; it grants no new read or execution authority.

## Interface

Each family specification now includes `read_registration`, a repository-relative
`{relpath, sha256}` pin to its registered analysis recipe. The other fields remain
`family_id`, `expected_members`, `bindings`, `initial_reference_member` and
`reference_family`. A five-field legacy specification fails closed.

The initial recipe declares `initial_members`. It can authorize only the initial
family and the exact same candidate-to-run mapping. Subsequent recipes declare
`family_id` and `expected_members`; a signature for another stage cannot be used.
The recipe's declared READ run ID must resolve to exactly one ledger row, using
the existing flight-registration parser and root-signature predicate. Require
the model-free, zero-contact discovery scope and the exact recipe artifact.
Refuse pending, absent, duplicated, mismatched or altered authority.

Perform this check before opening any task outcome or referenced feedback family.
The original complete-family reader still runs afterward: a root signature is
not a substitute for finalized attempts, valid seals, full rows or unique official
scores. Recheck authority before returning. Save the recipe pin, READ identity
and ledger-row hash with the exported feedback. No command signs or consumes a
READ row automatically.

## Operational sequence

1. Qualify every admitted member using operational metadata and seal verification.
2. Record the exact root countersignature after those conditions pass.
3. Use the existing saved-score receipt adapter and reward-link preparation after
   that gate. Preserve finalized source bytes; invoke no scorer again.
4. Save the complete member bindings and recipe pin in the family specification.
5. Export feedback through `scripts/system_text_search.py feedback`. Prepare L
   packets and capsules through the same revalidating path. B still refuses all
   feedback input before opening it.

Finalize the READ-row record before proposal packet export. A later change to
that authority invalidates exact packet revalidation and must be reconciled
explicitly; it cannot silently change a reserved proposal's context.

## Validation and current limits

The related selection passes 210 tests, including 21 lifecycle CLI tests, the
standard registration checks, complete-feedback, capsule, protocol, archive and
transport tests. CLI statement coverage is 89%. Tests cover unsigned or other
READs, pending and duplicate rows, changed recipes, mismatched members and
stages, wrong scope, authority changes during export, and continued refusal of
an unfinalized member even with a valid signature.

A metadata-only proof against the actual CONTROL2 initial READ row refused with
`READ row is not unambiguously root countersigned`. No task answers, score values,
reference family or model contact was opened. The positive path uses synthetic
authority and exercises the existing reader call; it is not evidence that the
live initial family is ready for a scientific read.

The exact source/test/evidence pins are in
[the continuation receipt](../../receipts/continuation/2026-10-01-system-text-read-registration.json).
The live A/A member, proposer admission and pending owner budget-profile decision
remain separate prerequisites. This correction changes no frozen registration,
worker, serving session, queue, allowance or scientific policy. The milestone
remains separately gated and excluded from optimization.
