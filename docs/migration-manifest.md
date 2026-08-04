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
| umbrella `common/src/speechrl_common/` (audio/io, rl/metrics, models/generative_omni, models/prompts, tracking/mlflow_logger, utils/seed) | dependency on the umbrella `common` package | DEPEND_WITH_PIN (no copy) | DEFERRED_UNTIL_FIRST_CONSUMPTION (2026-08-03 ruling: `src/` imports nothing from `speechrl_common` today, so no dependency is declared; see policy below) |
| W1 `scripts/baselines/two_pass_runner.py` | `src/.../models/` frozen-core adapter reference | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |
| W1 `scripts/baselines/provenance.py` | `src/.../tracing/` | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |
| W1 `scripts/baselines/metrics.py`, `stats.py`, `deterministic_draw.py` | `src/.../scoring/` + experiment stats | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |
| W1 `scripts/loaders/_common.py`, `registry.py` | `src/.../data/` loader skeleton (pattern only) | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |
| W1 `scripts/knowledge/kb_retrieve.py`, `kb_schema.py`, `corpus_lock.py` | `src/.../evidence/` | DEFER_TO_METHOD | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |
| W1 `scripts/repro_asr_best_of_n_v2.py` | best-of-N runner reference (livelock fix bundle) | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `28d8f0d`; hardcoded `/mnt/d` paths must be removed at adoption) |
| W1 `scripts/repro_asr_best_of_n_llamacpp.py` | original best-of-N runner reference | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `f9d111a`; hardcoded `/mnt/d` paths must be removed at adoption) |
| W1 `scripts/gpu_session.sh` | GPU serving-session harness reference | COPY_AND_VERIFY | SNAPSHOT_RESCUED (`reference/w1-snapshot/`, `7ed41f62`) |

W1's local checkout was retired on 2026-08-03 by owner ruling; the remote is retained as a cold
backup (umbrella `docs/integrity/retired-repository-registry.json`). The thirteen candidate files
were rescued verbatim into `reference/w1-snapshot/` (per-file SHA-256, source commit and quarantine
status in its `SNAPSHOT.md` and `SHA256SUMS`). They remain unintegrated
`QUARANTINED_REFERENCE_NOT_EXECUTABLE` material: promotion into `src/` still requires a dated
adoption row here, removal of absolute paths, plus passing tests.

### Shared-code dependency policy (`speechrl_common`)

Ruling 2026-08-03 (post-reorganization remediation, P1-1): this repository declares **no**
dependency on `speechrl_common` while `src/` does not import it. On first real consumption:

1. add the dependency pinned to an **exact umbrella commit**
   (`speechrl-common @ git+https://github.com/<owner>/exploring-l4-intelligence.git@<commit>#subdirectory=common`),
   regenerate and commit `uv.lock`, and update this row to ACTIVE with the pinned commit;
2. `uv pip install -e ../../common` stays a **local development override only** — CI and release
   reproduction must install from the pinned commit;
3. every formal experiment record then fills the `shared code revision` binding in the umbrella
   experiment ledger, even when the study commit is unchanged.

Explicitly not migrating: W1's 27 probe-era dataset loaders, baselines wave/cell one-shot scripts,
the full KB build pipeline, and any `_repro` history. Earnings21/Earnings22/ConEC loaders are new
code in this repository. General-audio loaders or experiment paths found inside the quarantined W1
snapshot (including AudioSet/FSD/ESC-family work) are outside the speech-only domain and cannot be
promoted by an adoption row in this study.

## Adopted rows

(none yet)
