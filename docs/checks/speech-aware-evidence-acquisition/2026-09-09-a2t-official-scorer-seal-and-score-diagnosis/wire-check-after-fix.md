# The wire checks after the repair (2026-09-09)

Both scripts re-run WITHOUT `--write`, so no committed receipt moved and this
file is the record. Branch `wt/a2t-scorer` at `736d3efc`, tree clean before and
after (`git status --porcelain` empty at both ends). Model-free: zero model
contacts, zero servers, zero sockets, zero GPU, zero paid API spend.

## `scripts/cross_carrier_tail2s_wire_check.py`

| carrier | cell | rows | preflight | wire_check stop class | `seal_and_score` |
| --- | --- | --- | --- | --- | --- |
| audio2tool | `R-official-tail2s-smoke-4` | 4 | `gate-not-authorized` | `none` | **OK** |
| audio2tool | `R-official-tail2s` | 400 | `gate-not-authorized` | `none` | **OK** |
| slurp | `closed-list-tail2s-smoke-4` | 4 | `gate-not-authorized` | `none` | **OK** |
| slurp | `closed-list-tail2s` | 1000 | `gate-not-authorized` | `none` | **OK** |

Both SLURP cells also BIND and are IDENTITY-CLOSED (4/4 and 2/1000 rows checked
against a 9,690-file closure). The SLURP stop class `slurp-packet-root-missing`
that the preregistration named is CLOSED, not bypassed:
SAEA-SN-DEV1000-TS2-PREPROCESS-V1 promoted all 1,000 `@ts2` packets and
`c1f63599` pinned that promotion receipt into
`configs/baseline/slurp-direct-closed-list-tail2s.json`.

## `scripts/a2t_input_rate_16k_wire_check.py`

Gold-id rail on this branch: LANDED
(`rails/adapters/audio2tool.py::Audio2ToolAdapter.gold`).

| variant | cell | rows | preflight | wire_check stop class | `seal_and_score` |
| --- | --- | --- | --- | --- | --- |
| 16k | `R-official-16k-smoke-4` | 4 | `none` (row registered) | `none` | **OK** |
| 16k | `R-official-16k` | 400 | `none` (row registered) | `none` | **OK** |
| 16k+ts2 | `R-official-16k-tail2s-smoke-4` | 4 | `gate-not-authorized` | `none` | **OK** |
| 16k+ts2 | `R-official-16k-tail2s` | 400 | `gate-not-authorized` | `none` | **OK** |

Every Audio2Tool cell's own per-cell receipt records `status: OK`, `failed: 0`,
`succeeded: 1`, `verified_attempt_state: OPENED`, and all four registered
scorers ran to completion: `a2t-toolcall-official`, `a2t-toolcall-v2`,
`a2t-toolcall`, `cost`. No cell stops at `a2t-gold-id-rail-missing` and none at
`seal-and-score-not-ok`.

The committed 2026-09-07 receipt under
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-a2t-input-rate-16k-wire-check/`
is the pre-rail measurement and is NOT rewritten here; it records the four cells
stopping at `a2t-gold-id-rail-missing`, which was true when it was taken.

## The repair, proven under the exact failing condition

Re-running with the 2026-09-09 shape restored -- ONE untracked note under
`docs/readiness/`, `git status --porcelain` showing `?? docs/readiness/...` --
both carriers' 4-row cells still reach the seal:

```
?? docs/readiness/2026-09-09-seal-and-score-probe-note.md
  arm=bare-core             contacts=4 payload_keys=10 ... seal_and_score=OK
  arm=speech-feature-query  contacts=4 payload_keys=18     seal_and_score=OK
```

Before `04ac31ce` that same tree gave `seal_and_score = SCORING_FAILED`,
`official scorer exited with status 1`. The probe note was removed again; the
tree is clean.

## What these numbers are not

`seal_and_score` runs the registered scorers over `WireCheckTransport`'s canned
response, never over model output. It proves the manifest/verify/ledger/score
link runs and nothing else. No cell is authorized, no exposure row is consumed,
and the `@ts2` / `@16k` cells still need their own owner GO.
