# Migration manifest

Adopting any code from W1–W4 or the umbrella into this repository requires a row here **before**
the copy lands, following the copy-and-verify protocol: register source repo + commit + path +
rationale → copy minimal files (never move, never rewrite history) → hash-verify pre/post → tests
pass in this repo → only then update umbrella references.

Inventory source commits at registration time: umbrella `e47fc33`, W1
(`speech-mllm-training-free-rl`) `7ed41f6`.

## Candidate inventory (registered 2026-08-03; nothing adopted yet)

| Source | Target | Mode | Status |
|---|---|---|---|
| umbrella `common/src/speechrl_common/` (audio/io, rl/metrics, models/generative_omni, models/prompts, tracking/mlflow_logger, utils/seed) | dependency `../../common` | DEPEND (editable install, no copy) | ACTIVE |
| W1 `scripts/baselines/two_pass_runner.py` | `src/.../models/` frozen-core adapter reference | COPY_AND_VERIFY | ADOPTION_PENDING |
| W1 `scripts/baselines/provenance.py` | `src/.../tracing/` | COPY_AND_VERIFY | ADOPTION_PENDING |
| W1 `scripts/baselines/metrics.py`, `stats.py`, `deterministic_draw.py` | `src/.../scoring/` + experiment stats | COPY_AND_VERIFY | ADOPTION_PENDING |
| W1 `scripts/loaders/_common.py`, `registry.py` | `src/.../data/` loader skeleton (pattern only) | COPY_AND_VERIFY | ADOPTION_PENDING |
| W1 `scripts/knowledge/kb_retrieve.py`, `kb_schema.py`, `corpus_lock.py` | `src/.../evidence/` | DEFER_TO_METHOD | NOT_ADOPTED |

Explicitly not migrating: W1's 27 probe-era dataset loaders, baselines wave/cell one-shot scripts,
the full KB build pipeline, and any `_repro` history. Earnings21/Earnings22/ConEC loaders are new
code in this repository.

## Adopted rows

(none yet)
