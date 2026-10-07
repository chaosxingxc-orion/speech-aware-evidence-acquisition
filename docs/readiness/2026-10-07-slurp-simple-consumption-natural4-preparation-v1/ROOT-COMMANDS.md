# Root countersignature, frozen checks and normal control transition

These instructions are prospective. No dispatch or control transition has been performed by the engineering implementer.

1. Review `natural4-prospective-validation-v1.json`, the eight `*-plan-prospective-v1.json` documents and `natural4-engineering-queue-v1.json`. Check actual C4 registration SHA `975bb7c9fb4525082a3bc191d20736a7493df5328b4302a884fd0ba4712c302a` and actual qualification SHA `47de73ed7217c042321abcc36ed027767fddc4bc8b77181f1b038477b8efff93`.
2. Root authors a decided DATA admission at `coordination/simple-consumption-natural4-owner227-v1/root-admission-v1.json` from the prospective template, adding its actual decision timestamp and authority. Keep the exact eligible eight IDs, capacity pins, 4/4 resource policy, structural-only scope, no next panel and held learning. Record its raw SHA-256.
3. Invoke the narrow document authoring helper once from the chosen preparation checkout (substitute the actual decision SHA):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" /home/chao/.venvs/speechrl/bin/python -B "$REPO/docs/readiness/2026-10-07-slurp-simple-consumption-natural4-preparation-v1/root-countersign-natural4-v1.py" --repo-root "$REPO" --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data --decision-relpath coordination/simple-consumption-natural4-owner227-v1/root-admission-v1.json --decision-sha256 "$DECISION_SHA" --root-countersign
```

4. Review/commit the eight registered plans and exposure rows. Serially integrate the reviewed preparation and registration, then create one clean detached frozen worker at the exact integrated commit. Revalidate exact source, prepared artifact identities and hashes. For each of seed, seed-aa, review-off and solver-lookup, use the existing commands with `CELL=slurp-native-stage3-simple-consumption-<member>-engineering-smoke-4-v3`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" /home/chao/.venvs/speechrl/bin/python -B scripts/checks/flight_registration_check.py --repo-root "$REPO" --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data --cell "$CELL" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root "$REPO" --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data --runtime-root /home/chao --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json --experiment "$CELL" --cell "$CELL"
```

5. Root revalidates the current original terminal/task state, no live generator/scorer or owned child, no STOP/flight lock, resident service/session identity and idle health, fresh telemetry and actual Windows memory. Earlier snapshots establish no present liveness. Preserve the completed historical queue/status/done/control bytes using the normal root-owned completed-job archive procedure. Never modify an old receipt, clear caches or release a live guard.
6. Root installs the reviewed fresh queue into `/home/chao/batch-queue.json`, points the ordinary `/home/chao/batch-flight-repo.txt` and `/home/chao/batch-flight-commit.txt` to the exact clean worker/commit, and preserves historical status/done markers before starting a new job. The queue must remain byte-identical to the reviewed `natural4-engineering-queue-v1.json`. These are root control actions; this package performs none.
7. Use the existing Windows `SAEA-Batch-Driver` task and existing `scripts/flights/batch/batch_driver_task.sh` wrapper. Do not create a new launcher. The existing driver runs only the four registered engineering workers and structural inspections. Record actual task/worker/service/startup receipts at launch, use a job-scoped script monitor, and delete it after verified terminal with no admitted child. Stop on the original first failure; no automatic retry.

Natural zero-lookup outcomes are retained. No forced lookup, official score, quality read, learner export, scientific comparison or next-panel dispatch is included.
