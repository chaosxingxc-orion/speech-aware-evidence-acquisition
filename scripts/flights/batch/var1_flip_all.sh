#!/bin/bash
# Flip the whole VAR-1 construction-variant family to ready on master: model-free, SEVEN cells in
# seven re-pin cycles (the four-row smoke, then VAR1-PLAN, VAR1-PLANR, and the four variants).
#
# Root runs this AFTER minting coordination/slurp-stage3-var1-v1/root-admission-v1.json (decision
# id slurp-stage3-var1-admission-v1) AND after rewriting that receipt's eligible_run_ids to this
# family's FOURTEEN run ids and its budget caps to this family's -- without that step
# core.flight.campaign.declared_readiness refuses every cell but the first ("run ... is not
# eligible in decision receipt"). Section 10 of the preregistration states the receipt edit.
#
# The SEVEN FIT cells (slurp-native-stage3-var1-{plan,planr,ex-k10,ex-k30,ex-div,per-k16c5}-r01c-
# fit-v1 and slurp-native-stage3-var1-smoke-4-fit-v1) are NOT flipped: they are spend identities,
# never flown as generation cells.
#
# ORDER MATTERS. The smoke flips first because it flies first. VAR1-PLAN flips before VAR1-PLANR
# because PLANr is defined as PLAN's request-identical second pass: its prepared first-phase supply
# MUST reproduce VAR1-PLAN's byte for byte, and the check is only meaningful once PLAN's is minted.
# A different value means the replicate is not a replicate -- stop and report, never pass
# --allow-output-change.
#
# Sibling flips invalidate each other's pinned hashes: repin_loop_generic.sh re-runs each cycle
# until the readiness package converges at one HEAD. Untracked files count as dirt for
# core.flight.cli check; the tree must be clean of them before this runs.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-24-slurp-stage3-var1-v1
cat > /home/chao/var1-smoke-commit.txt <<M
research: flip the VAR-1 four-row family smoke to ready (Stage-3 construction-variant rollout: the VAR1-PER-K16C5 contract shape -- five Perception candidates, sixteen intent cards -- on the first four R01C rows; owner directive 2026-09-24, handoff routes F3/F4; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-var1-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
for K in plan planr exk10 exk30 exdiv perk16c5; do
cat > /home/chao/var1-$K-commit.txt <<M
research: flip VAR-1 cell $K to ready (Stage-3 construction-variant rollout of the locked v2.0 plan on the 625-row R01C construction roster: VAR1-PLAN comparator, VAR1-PLANR own null, four single-knob construction variants; owner directive 2026-09-24, handoff routes F3/F4; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-var1-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/var1_repin_smoke.sh    $RD slurp-native-stage3-var1-smoke-4-v1      smoke-generation    /home/chao/var1-smoke-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_plan.sh     $RD slurp-native-stage3-var1-plan-r01c-v1    plan-generation     /home/chao/var1-plan-commit.txt     || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_planr.sh    $RD slurp-native-stage3-var1-planr-r01c-v1   planr-generation    /home/chao/var1-planr-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_exk10.sh    $RD slurp-native-stage3-var1-ex-k10-r01c-v1  exk10-generation    /home/chao/var1-exk10-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_exk30.sh    $RD slurp-native-stage3-var1-ex-k30-r01c-v1  exk30-generation    /home/chao/var1-exk30-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_exdiv.sh    $RD slurp-native-stage3-var1-ex-div-r01c-v1  exdiv-generation    /home/chao/var1-exdiv-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/var1_repin_perk16c5.sh $RD slurp-native-stage3-var1-per-k16c5-r01c-v1 perk16c5-generation /home/chao/var1-perk16c5-commit.txt || exit $?
cp /home/chao/var1-perk16c5-flight-commit.txt /home/chao/var1-flight-commit.txt
echo "flight commit $(cat /home/chao/var1-flight-commit.txt)"
