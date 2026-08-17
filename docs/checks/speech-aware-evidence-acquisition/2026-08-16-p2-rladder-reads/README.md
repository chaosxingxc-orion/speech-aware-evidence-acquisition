# Registered read — the SAEA P2 R-ladder ceiling block (2026-08-16)

This directory is the durable receipt of the **one-shot registered read** of the P2 R-ladder
resume block. It holds the pinned suite's machine-readable output (`report.json`) and the full
captured stdout of the run that produced it (`rendered.txt`). Nothing here is a conclusion:
**verdict document authored separately by the research lead.**

## Provenance

| Field | Value |
| --- | --- |
| Read executed | 2026-08-16, completed **20:10:04 local (EDT, UTC−04:00)**; wall time ≈ 20 min |
| Code commit | `2814bd9` — `fix(p2-reads): conform the branch evaluator to the pre-read pins; add the salvage input path (F1-F9)` |
| Working tree at read time | clean at `2814bd9` (`git status --porcelain` empty before and after) |
| Suite entry point | `scripts/p2_reads.py` → `speech_aware_evidence_acquisition.analysis.p2_reads` |
| Environment | WSL2 `Ubuntu-24.04`, `~/.venvs/speechrl` (Python 3.12), `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<repo>/src`, `SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data` |
| Model contact | none — the suite is model-free and read-only; it never opens a model session and never mutates an attempt directory |
| Exit status | `0`, empty stderr |

## Exact command line

```bash
python scripts/p2_reads.py \
  --r0bias-salvage-dir "$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage" \
  --r1verify-run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1verify" \
  --r2draft-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r2draft" \
  --r0wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r0wrong" \
  --r1wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1wrong" \
  --output "<scratchpad>/report.json"
```

`REPO` is this repository's checkout root. `report.json` and `rendered.txt` were written to a
session scratchpad first and copied here byte-for-byte with `cp -p`.

## The five input sources

| Arm | Source kind | Path / attempt | Manifest binding |
| --- | --- | --- | --- |
| `r0bias` | `salvage-json` | `docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage/` (`r0bias.asr-wer.json`, `r0bias.entity-wer.json`, `r0bias.copycount.json`) | preserved outputs of the already-spent one-shot salvage read of `attempt-20260816T002109Z-4e1f59`; the sealed raw attempt trace was **never re-opened** |
| `r1verify` | `completed-attempt` | `runs/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529` | `status: COMPLETED`, `study_commit 7bf251fb6f40d42ec201fe51c7043ef1d157efee` |
| `r2draft` | `completed-attempt` | `runs/SAEA-P2-r2draft/attempt-20260816T131610Z-930eca` | `status: COMPLETED`, `study_commit 7bf251fb6f40d42ec201fe51c7043ef1d157efee` |
| `r0wrong` | `completed-attempt` | `runs/SAEA-P2-r0wrong/attempt-20260816T155116Z-4e93d3` | `status: COMPLETED`, `study_commit 7bf251fb6f40d42ec201fe51c7043ef1d157efee` |
| `r1wrong` | `completed-attempt` | `runs/SAEA-P2-r1wrong/attempt-20260816T181330Z-f9a51f` | `status: COMPLETED`, `study_commit 7bf251fb6f40d42ec201fe51c7043ef1d157efee` |

Run directories live under `SPEECHRL_DATA_DIR` and never enter Git. `SAEA-P2-r1verify` also carries
`attempt-20260815T233245Z-6a98bd` (`status: ABORTED`, `study_commit a001a22e…`) and
`attempt-20260816T025734Z-23a43f` (no terminal manifest — the dirty-tree bind death); the suite's
`find_completed_attempt` selected the single `COMPLETED` attempt and skipped both.

## Governing registration and pins

| Document | Path |
| --- | --- |
| Pre-registered arms, reads, and branch rules | `docs/arms/p2-rladder-resume.arms` (header copied verbatim from `docs/arms/p2-rladder.arms`) |
| Branch-rule operationalization pins (authored pre-read) | `docs/p2-branch-rule-pins.md` |
| HER / RIR metric definitions mirror | `docs/p2-metric-definitions-mirror.md` |
| r0bias salvage archive (input) | `docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage/` |

## Files

| File | SHA-256 |
| --- | --- |
| `report.json` | `c5de852096790d731cfdc119828faa92705f3cd9c0d7bc96e2ad6adc90b24bf0` |
| `rendered.txt` | `ca4d7eea6341cb2ac03c25ff2d55c2c1d9b96196dcc3b14183f64ed7e0a2952d` |

`report.json` is the suite's `saea-p2-reads-v1` document verbatim; `rendered.txt` is the complete
captured stdout, including the tool's trailing "wrote machine-readable summary to …" line, which
still names the scratchpad path the run actually wrote to.

The `exclusion_warnings` field in `report.json` is empty and no F7 banner appears in `rendered.txt`:
both decisive co-primary contrasts landed at the pre-registered `n_effective_paired == 6` with
exactly the four registered zero-oracle-candidate ids (`4365024`, `4365948`, `4366429`, `4384964`)
excluded.

**Verdict document authored separately by the research lead.**
