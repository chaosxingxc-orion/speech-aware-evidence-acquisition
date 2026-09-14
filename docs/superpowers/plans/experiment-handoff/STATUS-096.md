# Status 096: TRAIN A anchor closed and next system admitted

Date: 2026-09-14. Keep the owner goal active.

The TRAIN Fold A recovery is COMPLETED / FINALIZED and the campaign is scored.
All 1,080 ordered samples passed structural/source checks and the first complete
official score succeeded. Generation made 5,417 calls; no second score was run.
Root wrote a source-bound quality release before reading full metric values.

The complete result and all 18 scenario strata are recorded in
../../../results/2026-09-14-slurp-native-train-a-anchor.md.
Official SLU F1 is 48.53363%, intent accuracy 77.96296%, and complete intent/entity
exact match 29.35185%. Correct-intent but nonexact-entity cases number 525.
C0 coverage is 937/1080 (86.75926%); conditional selection is 842/937
(89.86126%). Of the 143 misses, 110 lack an own-intent card in the actual initial
request. This association is not causal and excludes cross-card contrasts.

Root admits one complete-system successor with Reviewer-selected evidence tools
and one Planner candidate refresh. Its full-task comparison remains against the
same TRAIN A anchor, with no component causal claim or candidate-width change.
Read the new protocol and final configuration under
../../../readiness/2026-09-14-slurp-native-candidate-refresh-tools-train-fold-a-v1/.

DATA/coordination/slurp-native-candidate-refresh-tools-train-fold-a-v1/
admission-v1.json has SHA256
0d567c24a03d0d7271afbd8081b799b00865484c144c9226ef99c47ec8deafca.

The current service session serving-slurp-native-train-a-recovery-np4-v1 remains
resident at PID 767. Power configuration is settled. Reuse it with four 24,576
token slots, max512 and no mmproj. Local Whisper is invoked on CPU only when
Reviewer selects it; no fixed ASR preprocessing. Complete final supply, exposure
and clean-source checks before launch. The latest launch receipt, if present,
is in the successor DATA coordination directory. No launch is asserted here.

Preserve runtime checkout 826a77c7 and diagnostic checkout ebe19c52. Fold B is
untouched. The full next system, actual training-free proposal/consolidation/
disjoint-evaluation cycle and later carrier extensions remain unfinished.
