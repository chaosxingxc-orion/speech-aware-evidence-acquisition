# Named F0 fault: omitted owner allowance at manifest serialization

The operational checkpoint `docs/receipts/continuation/2026-10-01-milestone-seal-monitor-v1.json` records MILESTONE-00-PLAN ABORTED after 12,343 model contacts and 3,010 output records. Its written COMPLETED flag was rejected by seal validation; there is no valid complete seal or official score. MILESTONE-01 has no generation attempt. P-SV-4 halted on STOP. This report reads no task result.

## Root cause and correction

`core.bundle.manifest._manifest_document` manually serializes the execution plan. `owner_allowance` is an InitVar and is absent from `dataclasses.asdict`, so serialization dropped the pinned allowance even though the admitted live plan carried it. Independent final-report validation subsequently refused the reconstructed plan. Add the path and SHA only when the live plan carries an allowance. Keep discovery/dev serialization unchanged. Do not infer authorization from a manifest status or mint an allowance inside the writer.

The model-free regression covers serialization, reconstruction, signed-source verification and rejection after allowance-byte mutation, plus the no-allowance discovery shape. The change is to future writers only. No historical manifest, attempt, response, score or STOP marker is edited.

## Successor proposal, not authorization

`milestone-successor-proposal.json` names a fresh pair and fresh FIT identities on the exact original 3,010-row roster. Both original scientific configurations stay fixed; the new slot-knowledge mechanism is not substituted into this comparison. The pair entails 6,020 new complete trajectories, with inherited maxima of 66,220 generation contacts and 264,880 FIT endpoint contacts across both arms, and two official score jobs. These are upper bounds, not expected consumption.

The owner must explicitly authorize a successor allowance. The old allowance does not permit reusing the failed attempt or sealing its old output. Obtain the successor signature only after presenting this fault and proposal. Then bind the new code, allowance and registration into new configurations and validate them before dispatch. The original final-report failure policy takes precedence over the ordinary one-recovery rule.
