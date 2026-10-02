# Shared single-member process memory guard

Recorded 2026-10-02T11:03:39.341044+00:00 by ChatGPT root.

## Status and authority

Offline engineering is complete; UPDATE2 recovery remains HELD for proposed owner decision 218. This change does not grant recovery, start a worker, change the current queue, dispose an attempt, archive a lease, clear STOP, or modify any frozen source. Owner 216 and 217 were approved and executed for their separate earlier scopes. Neither covers the UPDATE2 startup failure.

## Shared execution and custody

`core.flight.process_guard` supervises exactly one ready registered campaign cell through the existing `core.flight.cli campaign --experiment` entry. It adds no controller, scorer, model path or scientific action. It requires its exact frozen checkout, clean Git identity, disabled bytecode writes and receipts beneath `data-root/coordination`. The same campaign still owns all contact, authorization, seal and official-score gates.

The batch driver opts into this supervisor only when both `process_start_gib` and `process_floor_gib` are declared. It rejects a combined campaign plan, a separate unsupervised smoke, incomplete threshold declarations or an ambiguous single-member route. Existing campaign-plan, engineering and artifact paths retain their behavior. A failed supervised step stops the driver before its next member; no retry is implemented.

The supervisor samples Windows free memory before process creation and throughout execution. The proposed queue starts only at or above 14.5 GiB and stops below 10 GiB. The 14.5 GiB threshold is additional operational headroom, not a measured full-generation bound. Any stricter existing guard still applies. Missing, invalid, failed or timed-out observations refuse startup or stop an owned worker. Default sample spacing is 5 seconds, observation timeout 10 seconds and termination grace 5 seconds. This sampled mechanism cannot guarantee that no sub-interval excursion occurs.

Each child starts a private process group. On a stop, only that owned group is signaled. The leader is not reaped during the grace interval, preserving its group identity while the supervisor terminates any surviving scoring descendant. Separate resident service, telemetry and unrelated processes are not targets. A worker's failure exit remains a failure. Exclusive receipt creation preserves the command, policy, identity, observations and disposition. Original task artifacts and control records remain untouched.

## Verification

The first new guard tests failed because the module did not exist. Batch-loop tests then reproduced the old combined-plan dispatch before the guarded route was added. A further real subprocess test found that a terminating leader could leave a SIGTERM-ignoring scoring descendant alive; the corrected group-lifetime rule passes that regression. All fixtures are synthetic local processes; no research task, model, tokenizer or official scorer is contacted.

The related suite passes **194 tests**: owned-process custody, real extracted batch-loop routing, existing engineering and artifact inspection, campaign configuration, queue/readiness, serving resource policies and resource clocks. Scoped statement coverage of `process_guard` is **94%** (160 statements, 10 unexecuted). Ruff checks, Bash syntax and the engineering-base gate pass.

Tests include startup refusal before any child, finite thresholds, unavailable and hung readers, exact floor behavior, literal argument preservation, one-shot child failure, receipt non-overwrite, unchanged sibling survival, uncooperative child and descendant termination, exact frozen-root checks, single-cell readiness, threshold ambiguity, first-failure stopping and original campaign-plan routing. Batch tests replace registration/model/scorer boundaries with fixtures; they are not proof of live registration, seal or score success. The existing single-member 2.14 GiB preflight proof also remains preflight-only.

## Proposed recovery queue and remaining gates

The [v2 queue](2026-10-02-slurp-system-text-update2-memory-recovery1/proposed-sequential-queue-v2.json) supersedes the prior draft only by adding the two explicit memory thresholds to each of the same eight steps. SHA-256: `030b7b41b7836467479bd0d833a0db1cda3fc659a3d5551c1ee5af73d2c9e99e`. The v1 draft is preserved. Member order, identities, scientific settings, 400 rows each, 3,200 total trajectories and original proposal allocations are unchanged. This queue is **not installed**.

After an explicit owner 218 ruling, root must still complete the exact abandoned-entry disposition, successor first-attempt preparation, whole-family registration/READ recipe, frozen source, admission and live checks. Full-family scientific READ remains unsigned. No partial UPDATE2 result exists or was read. All other carrier and proposal holds remain in force.

At the metadata-only check at 11:01Z, L-parent remained OPENED with zero calls/audio and no manifest; the seven other attempts were absent. STOP remained the exact 10:27:53Z incident. Windows free memory was 14.195 GiB, below the proposed 14.5 GiB startup threshold; no launch was attempted. Service telemetry was fresh, healthy and idle, with 22,976 MiB GPU memory. Expected idleness requires no new outage notification.
