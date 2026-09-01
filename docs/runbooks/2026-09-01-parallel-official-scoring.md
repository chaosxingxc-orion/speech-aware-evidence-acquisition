# Parallel official scoring runbook

## Outcome

Run independent official-scorer jobs concurrently without changing any
official scorer or metric definition. Each worker receives one complete,
verified run manifest and invokes the existing authoritative scoring path in a
separate process.

Never split one corpus into scoring shards and average their results. Metrics
such as micro-F1 depend on corpus-level sufficient statistics; averaging shard
scores would change the metric. If upstream preparation is sharded, merge and
verify the complete prediction artifact first, build its run manifest, and
submit that one manifest as one scoring job.

## Job file

Write one exact-field JSON object per line. Resolve relative manifest paths
from the job file's directory.

```json
{"job_id":"direct","manifest":"../runs/direct/direct.run-manifest.json"}
{"job_id":"agent","manifest":"../runs/agent/agent.run-manifest.json"}
{"job_id":"random-retrieval","manifest":"../runs/random/random.run-manifest.json"}
```

Job identifiers must be unique and may contain letters, digits, dots,
underscores, and hyphens. Manifest paths must also be unique and must end in
`.run-manifest.json`.

## Run

```bash
bash scripts/evaluate_parallel.sh \
  --jobs /absolute/path/to/jobs.jsonl \
  --output-dir /absolute/path/to/new-score-directory \
  --workers 4
```

For completed attempts that still need their score artifact and terminal
attempt transition, add `--finalize`. Each worker then runs the existing
authoritative finalize command, so the official scorer still executes exactly
once per complete manifest while the independent attempts settle concurrently.

The output directory must be new or empty. The scheduler never overwrites an
existing result. It allows every submitted job to finish, even if another job
fails, and returns a nonzero exit status when any job fails.

## Artifacts

- `<job_id>.score.json`: the validated authoritative result for a successful
  job; `verified` must be `true` and the returned manifest identity must match.
- `<job_id>.stderr.log`: isolated diagnostics for every job.
- `<job_id>.stdout.log`: captured partial or invalid output for a failed job.
- `batch-summary.json`: input-ordered statuses, elapsed time, return codes, and
  result hashes, plus the explicit no-shard aggregation rule.

Choose worker count by measurement. These jobs are CPU and reference-I/O
bound; start at four on the primary host, compare wall time and storage
pressure, and reduce concurrency if the reference volume becomes the
bottleneck. This is evaluation engineering only: it changes neither model
contacts nor scientific sample exposure.
