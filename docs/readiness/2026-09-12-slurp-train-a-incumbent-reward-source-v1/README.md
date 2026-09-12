# SLURP TRAIN-A incumbent reward-source preparation v1

## Status and purpose

Root registered this one baseline-reproduction flight over the existing 1,080-row TRAIN-A construction roster. It reproduces the accepted compact task-agent incumbent through the shared FlightRuntime and OpenJiuwen path: plan, one fixed knowledge action, then solve. It creates source-bound trajectories for later offline RewardLink construction. It adds no speech observation, reviewer, experience memory, selection rule, optimizer update, or effectiveness claim.

The shared TRAIN adapter repair and model-free recall are accepted. Root admission, readiness and separate generation/fit plans are now registered in registration-v1.json. The final clean source check, model-free wire verification, resident identity attestation and actual request fitting remain required before generation. Optimizer proposals retain their separate registration.

## Frozen method and sources

- Dataset fragment: configs/dataset/slurp-speech-native-evo-fold-a-1080.json, SHA-256 4ba55688e80d8d768ec6cfc3ff4bacc9802fb34e4dab54913934015184497215; 1,080 rows, exact audio duration 3,084.5284375 seconds, maximum row duration 10.9425 seconds, split identity 61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6.
- Roster receipt: docs/receipts/rosters/slurp-evo-fold-a-v2.json, SHA-256 1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d.
- A/B-excluded compact snapshot: knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json, runtime content SHA-256 9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b, file SHA-256 f2785aa3521b08e874d4075154e65cc639284497afc789a3654c2c70a65405ef; repository receipt SHA-256 5db718d38426e5e6d2311efbed0c4faf36bf30473c8d00b14e06618257889766.
- Facet vectors: vectors/slurp-kus3/facet-vectors.jsonl, SHA-256 5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e. This is the established safe superset: runtime indexes only facet IDs in the excluded snapshot.
- Fold-A speech queries: prepared/SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1/queries.jsonl, SHA-256 cff97de32d373c318b9c73f703d6ddf173f5150697fc1e25851e8d13cb6ec1f6; 1,080 full-utterance segment rows. Prepared index SHA-256 266206b9f4f83ca79818e5defab8ffc60f6d438a518e9624f14ccac2b7c12287. Registration SHA-256 bfe57de6fd6f3f1f2bdd30fb9c42187415c586593b2c481a939014eb55466daf.
- Existing packet union: /home/chao/feat-cache/slurp-q4km-packets-04ccc72a/EVO-FOLDS-V2-promotion.json, SHA-256 4f048f47830a22d41d0bc81ccb453efd41bf8c6726a462bd1dc11eab36f30247. It holds 2,160 A/B packet identities; runtime restricts it to TRAIN-A.
- Model fragment: q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64; decoder-only, no mmproj, c65536, np4, 16,384 tokens per slot. request_decoding_overrides.max_tokens=256 is the effective phase-request limit. The inherited max64 name/default does not lower these requests.

The task prompts, fixed saea-tool-phase-knowledge-v1 action, K5 content recall, rank/fuse policies, full legal label fill, whole-roster wave barrier, packet/key matcher, and phase-task-tools-then-solve-v1 program are retained from the accepted frame replication.

## Exact arithmetic

Two phases over 1,080 rows give a target of 2,160 generation contacts. The 5 percent ceiling is 2,268. The 108 reserve contacts are budget only and do not authorize adaptive replay. The generation speech ceiling is ceil(2 * 3084.5284375 + 108 * 10.9425) = 7351 seconds. Whole-roster fitting uses 2 * (1 + 3 * 1080) = 6482 endpoints and ceil(2 * 3084.5284375) = 6170 speech seconds. Root set 2.0 utilization-integral GPU hours inclusive of fit and generation.

## Shared adapter candidate

This isolated worktree carries the narrow shared adapter repair at commit 847052982a3959551be53fc2835eb2464c8f9d01 for root review. TRAIN rows require discovery role and an explicit registered population; named TRAIN split IDs must equal the runtime view split name. Mixed TRAIN/DEVEL populations, test IDs, TRAIN under devel or DEV aliases, and population expansion are refused. Legacy DEVEL behavior, empty runtime labels, gold refusal, and the wrapper call shape remain unchanged. No private adapter or launcher was added.

## Model-free preparation after the blocker is repaired

Use the literal checkout source and no editable installation:

~~~bash
REPO=/home/chao/saea-worktrees/training-incumbent-source-prepare-v1
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHON=/home/chao/.venvs/speechrl/bin/python
export PYTHONPATH="$REPO/src" PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1

"$PYTHON" "$REPO/scripts/flights/run_campaign.py" check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path "$LOCK" --experiment slurp-train-a-incumbent-reward-source-v1 \
  --cell slurp-train-a-incumbent-reward-source-v1

mkdir -p "$DATA/prepared/SAEA-SLURP-TRAIN-A-INCUMBENT-REWARD-SOURCE-PREPARE-V1"
"$PYTHON" "$REPO/scripts/flights/run_campaign.py" prepare-phase-recall \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path "$LOCK" --experiment slurp-train-a-incumbent-reward-source-v1 \
  --cell slurp-train-a-incumbent-reward-source-v1 --phase solve --workers 20 \
  --output "$DATA/prepared/SAEA-SLURP-TRAIN-A-INCUMBENT-REWARD-SOURCE-PREPARE-V1/recall.json"
~~~

Require 1,080 recall rows and verify every selected ID belongs to the pinned snapshot. Insert only the returned relpath and SHA-256 at prepared_phase_recall.solve. Then bind root readiness, compose final config and protocol hashes, register generation and fit plans plus ledger rows, and run public check and a model-free full-roster wire check. Changing any other field invalidates recall identity.

Root later starts the registered resident service and invokes the one-cell shared campaign plan. Actual fitting occurs on that service at phase barriers; solve fitting follows fresh plan state. After a complete 1,080-row seal, score the full native TRAIN manifest once through core.driver score-batch --finalize --include-per-sample using a create-only one-job JSONL input and output directory. No partial or repeated score run is admitted.

One recovery is the maximum. A second failure stops the flight and requires a separately registered four-row connectivity proof.
