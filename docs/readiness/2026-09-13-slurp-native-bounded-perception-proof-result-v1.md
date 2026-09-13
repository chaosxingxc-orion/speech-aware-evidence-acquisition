# Bounded Perception engineering proof passed

The registered four-row TRAIN engineering proof generated and sealed all four
native episodes on frozen WSL commit 5a9e78f5dc309f16631e5d5b21687a1850609e7d.
It consumed 20 model calls and 52.9778125 repeated speech seconds, with 80 actual
fit endpoint contacts. Perception/Solver/Reviewer/Planner used 4/4/8/4 model calls.

All four Perception responses ended with stop and passed the configured bounded
JSON contract, distinct legal candidate IDs, at most 12 words per distinction,
and empty metadata arrays. Their completion lengths were 138, 58, 102 and 147
tokens, under max512. Every sent request matched its fit boundary. Every delivered
output exactly matches a source-bound Solver response. These rows did not exercise
revision-limit delivery; that path retains its synthetic graph/custody tests.

No official scorer ran and no task-quality metric was read. The worker stopped
after seal, so the normal score-driven attempt finalization had not run. Root
verified the complete bundle and engineering criteria, then used the existing
AttemptHandle.finalize_with_receipt API to finalize this scoreless engineering
closure with its exact verification receipt. The run manifest and model outputs
were not rewritten.

Verdict: PASS_ENGINEERING_ONLY.
Manifest SHA256: abf763b56bde3413155b9bdf1e2d83126bcf2a297200035768c5c22ccb263e1b.
Verdict SHA256: 8f4c5d755f69cda645c9c8f3c356ef188a34effe32256bc51d689f0e2606e8a9.
DATA coordination directory:
coordination/slurp-native-bounded-perception-proof-v1.

The two failed full-system attempts stay closed and unscored. Four engineering
rows do not establish task effectiveness, full-roster reliability or successful
replication. The next complete-system version requires separate source preparation,
registration and a matched max512 direct comparator.
