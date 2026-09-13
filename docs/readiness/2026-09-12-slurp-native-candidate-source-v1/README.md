# SLURP native candidate source drafts

These files prepare one retained DEV-1000 direct reference and one native answer-or-one-tool source flight. They authorize no model, tool, scorer, service, or exposure contact. The experiment documents remain held templates until root inserts scientific readiness and immutable generation and fit ExecutionPlans.

The direct baseline uses the shared `phase-direct-only-v1` path for one task response. The lookup baseline uses `native-answer-or-one-tool-v1`: `decision-1` may answer directly or request one `saea-tool-candidate-contract-lookup-v1` call containing one to three ordered legal candidate IDs; `final` has no tool and jointly owns the legal intent and entities. A legal final answer may fall outside the requested shortlist. Both arms keep the original speech and the same retained packet route. Neither arm supplies Whisper, memory, retrieval embeddings, or knowledge values.

The lookup baseline binds canonical provider source `deb4e097459157a719e34b3fb46014d5f9bcb86c9e952014c1e02f26474db201`. Its sealed model-free receipt is `prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/receipt.json`, SHA-256 `7b93a1ae1912c97b4be7813cf394629042c0dcc976cf8f74993647aee7213c2b`. The raw catalog SHA-256 is `3e60268b3f940c3018ab8b8c80ccd988b1d1efd6c5a198929c6af05ba21f8263`. The catalog contains all 60 legal intents from 11,514 TRAIN utterances with `min_share=0.02` and no examples. Preparation made no neural or runtime lookup contact.

The raw model fragment file SHA-256 and the resident serving identity are intentionally distinct. The file is `configs/model/q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64.json`, SHA-256 `39ae54d72838b359a893a3938e242859c037cb3af1ddb1e7aca838e33fa45ca0`. The resident identity binds model fragment SHA-256 `7545a1ac3eb0c1e88d4121fdf84726e5201bb9d5ae5a32804cc62a7f6a289f74`. Requests override the inherited fragment name/default to `max_tokens=256`; serving remains decoder-only, no-mmproj, c65536, np4.

The source comparison is descriptive system-source generation. It does not isolate Top-N commitment and does not replace the later matched common-first-pass commitment branches.

After root materializes the held experiment templates, binds readiness and both registered plans, and freezes the source commit, run only the shared model-free checks first:

~~~bash
REPO=/home/chao/saea-worktrees/ROOT_FROZEN_CANDIDATE_SOURCE
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHON=/home/chao/.venvs/speechrl/bin/python
export PYTHONPATH="$REPO/src" PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1

"$PYTHON" "$REPO/scripts/flights/run_campaign.py" check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path "$LOCK" --experiment slurp-native-candidate-source-direct-v1 \
  --cell slurp-native-candidate-source-direct-v1

"$PYTHON" "$REPO/scripts/flights/run_campaign.py" check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao \
  --lock-path "$LOCK" --experiment slurp-native-candidate-source-lookup-v1 \
  --cell slurp-native-candidate-source-lookup-v1
~~~

Do not proceed to fitting or campaign dispatch from this draft. Root must first register exact plan/protocol/config hashes, exposure rows, the resident attestation, and request-fit outputs.
