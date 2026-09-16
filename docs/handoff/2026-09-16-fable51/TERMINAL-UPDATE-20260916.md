# Typed-context system recovery: capacity failure and closure

Root decision: CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY.
Terminal time: 2026-09-16T17:07:37.744607Z, campaign exit code 1.
This is an engineering failure, not a negative task-effectiveness result.
Supersede the earlier running-state snapshots; preserve them as historical records.

## What completed and what did not

- Current system attempt: ABORTED, 6,645 generation contacts and 18,136.492 repeated
  speech-input seconds. Contacts are not completed recording counts.
- Actual per-contact capacity checks: 6,646 receipts, 6,645 fitting and one failing;
  26,584 endpoint contacts. These are separate from generation contacts.
- No complete system manifest or official system score exists.
- The failed oversized request itself made zero generation contacts.
- The direct comparator remains complete, FINALIZED and first-scored, with quality unread.
- The held matched replica is ineligible because its predecessor did not complete.
- Original 507-contact failure, four-row proof and this recovery remain separate records.
- The current exact source remains frozen at
  9bf27b28708bb93607138e7bcd1eacb66eab3f08.
- The observer ended normally on the terminal event. The decoder remained resident,
  four slots idle, approximately 22.4 GiB allocated. This was not a server restart.

No partial task score, model answer or reference text was read for this diagnosis.
Root extracted only exception classes and stack-frame metadata from the log tail, inspected
the corresponding frozen source and read numeric request-fit receipts. Do not describe that
as no log access at all; it was bounded technical metadata extraction, not a raw tail display.

## Established triggering cause

The failing Reviewer request had:

| Quantity | Tokens |
| --- | ---: |
| Text | 24,299 |
| Speech | 65 |
| Special tokens | 2 |
| Maximum completion reserve | 512 |
| Total required | 24,878 |
| Registered slot | 24,576 |
| Margin | -302 |

The actual-request guard in core/preparation_fit.py, fit_contact, line 1329 raises
PreparationError("native contact request exceeds the registered capacity").
The exception propagates through the native role workflow and terminates the campaign.
The guard correctly prevented an oversized generation; the package did not provide a
qualified bounded continuation when a dynamically constructed Reviewer request no longer fit.

The same episode's numeric capacity sequence was:

| Contact | Text tokens | Total required | Remaining margin |
| --- | ---: | ---: | ---: |
| Perception 0 | 3,639 | 4,218 | 20,358 |
| Solver 0 | 12,073 | 12,652 | 11,924 |
| Reviewer 0 | 13,024 | 13,603 | 10,973 |
| Reviewer 1 | 13,960 | 14,539 | 10,037 |
| Reviewer 2 | 24,299 | 24,878 | -302 |

Speech and output reserve are unchanged throughout. The last Reviewer transition adds
10,339 text tokens. This establishes dynamic text growth as the proximate capacity issue.
It does not establish which semantic card, tool response or duplicated content dominated
that growth; those claims would require a further source-bound structural audit.
Do not guess that all growth came from a particular tool or from rejected-call feedback.

The earlier four-row proof established execution and rejection settlement on those four
trajectories. It did not establish that every possible later tool-result/history combination
would fit. This failure also does not invalidate the separate successful multi-call
rejection repair: the observed exception is capacity-related, not missing tool observations.

## Consequences for the research plan

1. Close this flight. No third attempt, prefix salvage, score on a partial cohort, renamed
   replay or held-replica bypass.
2. Preserve the useful older replicated SLURP base. No quality conclusion is available for
   this typed-context package and it cannot be promoted.
3. Keep the direct first score intact and unreleased under the current paired-read contract.
   A later reuse would require an explicit compatible analysis/experiment binding.
4. Prioritize the shared dynamic context/capacity interface before any new GPU successor.
   This is engineering needed for a valid system, not a demonstrated accuracy improvement.
5. Preserve the future candidate, slot and tool designs as conditional proposals. They do
   not authorize adding those mechanisms while repairing this failed registration.

## Bounded next engineering work for Fable5.1

Use the frozen source and hashed failure receipt to locate the exact context transition.
Inspect structure and provenance without reading partial task quality. Separate base task
instructions, accumulated knowledge, role view, tool definitions and required call/result
pairs. Determine which bounded public interface can prevent an admitted action from creating
a continuation that exceeds capacity.

Compare only defensible approaches: lossless removal of duplicated static material,
role/candidate-specific source-bound projection, or prospective action/result admission that
reserves capacity for a valid reporting/termination continuation. Preserve all observations
in canonical storage. Model-facing projection must keep applicable constraints and required
tool custody; it cannot silently drop inconvenient evidence or fabricate a successful report.

Prove the selected behavior with synthetic worst-case histories and the source-bound failing
request shape. Treat any changed model-visible projection, fallback or serving geometry as
an explicit new system version. Keep output max512 and current geometry for diagnosis;
do not lower the cap or add context to manufacture a pass and call it the same experiment.
A later justified geometry change must apply to its registered comparison as a whole.

A separately admitted four-row engineering proof can establish the repaired interface before
any distinct full-roster system experiment. It does not grant a third attempt on the closed
flight, establish effectiveness, or replace complete capacity/custody accounting.
Do not turn this task into an open-ended hardening program.

The owner need not reapprove this metadata diagnosis and closure. Present any proposed new
scientific comparison, added contacts or material scope change concretely before requesting
a new decision where required. Never reinterpret the old recovery authorization.

## Evidence and operational custody

All local artifacts below are under
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-typed-context-vs-direct-v1/:

- root-campaign-system-recovery-terminal-v1.json: original process exit receipt.
- observer-system-recovery-v1.json:
  d463515627204fb82804b40f84c1ec224dcd703aba5c1798615251b931c1da5c.
- root-system-recovery-capacity-metadata-v1.json:
  f12725f0ad34182946527d19a24ee5b11e168d553e107414a2a2086da93f792a.
- root-system-recovery-closure-v1.json:
  6cbe548587958f4b32622c5496b1cc9c532671bb9c24ba1109adfc13623f737f.

The failing request-fit receipt SHA-256 is
98f6bcf9ab3370711821bfd44bccc1d0d6f0b669204d0fd5dd1a32d93b14f3f7.
Its full path and source-bound numeric sequence are in the closure receipt.
The failed rendered request-body hash is
0c633077e231a5040423fbbf6debf31814dddd06d9f14b046ef0936ef3f38d4c.

No service, lease or runtime source was changed during closure. Before any future admitted
contact, reconcile actual process/lease ownership using existing guarded operations.
Do not remove lock files merely because the original campaign process is dead.

Read the [English terminal exposure successor](../../receipts/2026-09-16-typed-context-terminal-exposure.md) for contact accounting. The original exposure ledger is preserved unchanged.
