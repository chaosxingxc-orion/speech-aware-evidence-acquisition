# The Audio2Tool `seal_and_score = SCORING_FAILED` diagnosis (2026-09-09)

Model-free. Zero model contacts, zero servers, zero sockets, zero GPU, zero paid
API spend. Everything below reads sealed bytes off `$SPEECHRL_DATA_DIR` and runs
the official scorer over them.

## 1. The symptom

The four Audio2Tool wire-check cells that merge wave 3 (master `5299ec53`,
2026-09-07) recorded at `seal_and_score OK` ended at
`seal_and_score = SCORING_FAILED`, `official scorer exited with status 1`,
when they were re-driven on 2026-09-09 during the D1 declaration fix. The
`SCORING_FAILED` status is the strict one: the manifest DID seal COMPLETED and
was then refused by the scorer, which is precisely the state the wire check's
seal stage exists to catch (`core.flight.runtime._wire_check_seal_and_score`).

## 2. The verbatim stderr

`scorer-subprocess-stderr.txt` carries both failing jobs' captured stderr
unedited. Both end at the same line:

```
File ".../core/scorers.py", line 631, in _assert_scoring_entry_gate
    require_clean_study_repo(Path(repo_root))
File ".../core/bundle/git_commit.py", line 199, in require_clean_study_repo
    return _study_commit(Path(repo_root))
File ".../core/bundle/git_commit.py", line 78, in _study_commit
    raise BundleError(
speech_aware_evidence_acquisition.core.bundle.BundleError: study repo
/mnt/d/chao_workspace/saea-worktrees/wt-a2t-d1fix has uncommitted changes; a run
manifest must bind the exact commit that produced the run, never a dirty tree:
?? docs/readiness/2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md
```

One untracked readiness note. Not a scorer fault, not a gold-id fault, not a
manifest fault.

## 3. The bisect, model-free

Every input the official Audio2Tool scorer reads is byte-identical between merge
wave 3 and the branch under test. Blob-level comparison, `git rev-parse
<commit>:<path>`, `5299ec53` vs `480a6e26`:

| path | blob |
| --- | --- |
| `src/.../reproduction/a2t_scorer.py` | SAME |
| `src/.../reproduction/audio2tool_official/__init__.py` | SAME |
| `src/.../reproduction/audio2tool_official/metrics.py` | SAME |
| `src/.../reproduction/audio2tool_official/parse.py` | SAME |
| `src/.../core/scoring_batch.py` | SAME |
| `src/.../rails/adapters/audio2tool.py` | SAME |
| `src/.../core/bundle/git_commit.py` | SAME |

`core/scorers.py` is the single file in that set that moved (+53 lines, commits
`72697607` and `42392d8f`), and both hunks are new scorer REGISTRATIONS on other
carriers -- `slurp-slu-f1-normalized-v1` and `brief-term-recall-v1`. Neither is
on any Audio2Tool cell's `scorers` list.

The verl `scripts` shadowing is NOT involved: nothing under `src/` imports
`scripts.*` at all (`rg 'import scripts|from scripts' src/` is empty), so the
scoring subprocess never resolves that name.

## 4. The commit that broke it

`e41b9030` -- `protect(e0): flight lockfile + load-bearing-surface manifest bind`
(2026-08-16), the repair for the incident that stranded 156 minutes of spent
inference.

It narrowed **one half of a seal**. `_study_commit_for_completed_manifest`, used
when a COMPLETED manifest binds its `study_commit`, began tolerating and
RECORDING dirt confined outside `LOAD_BEARING_SURFACE_PREFIXES` (`src/`,
`configs/`, `docs/arms/`, `scripts/`). The **other half**,
`core.scorers._assert_scoring_entry_gate`, kept calling
`require_clean_study_repo`, which refuses ANY dirt -- explicitly, in that
commit's own words, "unchanged and still fully strict".

From `e41b9030` onward a run can therefore seal COMPLETED over a stray
governance document and then be permanently **unscoreable and unfinalizable on
the very tree that sealed it**: the 2026-08-16 incident, moved one step later.
Merge wave 3 measured `OK` only because the tree happened to be clean; the D1
fix's own readiness note was enough to expose it. The operational hazard was
already known and worked around by hand ("keep the checkout clean for a run's
whole duration"); this is its mechanism.

## 5. The comparator reproduces to the digit

`comparator-reproduction.json` is the aggregate the official scorer produced at
branch tip for the sealed 400-row comparator
`SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell `R-official-raw`, attempt
`attempt-20260904T135250Z-rofficialraw`, run exactly as `core.scoring_batch`
runs it (`python -B -m ...core.driver score --manifest <path>`, `cwd` at the
repo root). Compared against the `comparator.sealed_official_tool_accuracy`
block committed in `configs/experiment/a2t-official-protocol-tail2s-400-v1.json`:

| field | sealed | reproduced |
| --- | --- | --- |
| n | 400 | 400 |
| overall tool accuracy | 61.0 | 61.0 |
| exact match | 20.25 | 20.25 |
| parse rate | 99.75 | 99.75 |
| rows with multiple call matches | 52 | 52 |
| tier1_direct | 60.0 | 60.0 |
| tier2_parametric | 74.0 | 74.0 |
| tier3_multi_intent | 72.0 | 72.0 |
| tier4_implicit | 28.0 | 28.0 |
| tier5_needle | 78.0 | 78.0 |
| tier6_correction | 84.0 | 84.0 |
| tier7_multiturn | 58.0 | 58.0 |
| tier8_intent_blending | 34.0 | 34.0 |

Exit code 0, empty stderr, `"verified": true`. The scorer was never broken.

## 6. After the repair

`wire-check-after-fix.md` records both wire-check scripts re-run without
`--write` on the repaired branch: all four cross-carrier cells and all four
input-rate cells reach `seal_and_score = OK`, and the exact 2026-09-09 failing
condition -- one untracked note under `docs/readiness/` -- now reaches the seal
too, for both carriers.

## 7. What this measurement does NOT authorize

Nothing. No cell is flown, no exposure row is consumed, no contact is made. The
`@ts2` and `@16k` cells still need their own owner GO and their own exposure
rows.
