# Durable archive — the SAEA-P2-r0bias one-shot salvage read (2026-08-16)

This directory is a **preservation record**, not a check that can be re-run. It holds the tooling
and the output bytes of the single offline salvage read of arm `SAEA-P2-r0bias`, attempt
`attempt-20260816T002109Z-4e1f59`. Before this archive existed, the only durable trace of that read
was prose in the umbrella records; the scripts and their outputs lived solely in a Claude Code
session scratchpad under the OS temp tree, which is not durable storage.

## Why the read happened

The five-arm P2 R-ladder block launched 2026-08-16T00:21Z did not fail in science — it failed at
manifest bind. `core/bundle/git_commit.py` refuses to bind `study_commit` against a dirty working
tree, and the English-only rewrite of `AGENTS.md` / `CLAUDE.md` landed in the tree mid-flight. Arm
`SAEA-P2-r0bias` had by then **run its inference to completion** (395 metered model calls,
30959.04 speech-audio seconds) and had written its trace, outputs, all ten replay derivations, the
trace manifest and the server log — yet its manifest was finalized `status: ABORTED` with
`failure_reason` "run succeeded but its COMPLETED manifest could not be built: ... uncommitted
changes".

Because the durable bytes of that attempt survived, one-shot attempt semantics were preserved by
reading **the attempt that actually ran**, offline, exactly once — rather than by flying a second
attempt of the same arm. That read is recorded in `docs/exposure-ledger.md` and in the umbrella
experiment ledger; `SAEA-P2-r0bias` was consequently *not* re-flown in the four-arm resume block.

## Provenance

| Field | Value |
| --- | --- |
| Source | Claude Code session scratchpad `95b8e5b0-424d-494b-9d7b-4f101bc186be` |
| Source path | `C:\Users\35686\AppData\Local\Temp\claude\D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition\95b8e5b0-424d-494b-9d7b-4f101bc186be\scratchpad` |
| Read window | 2026-08-16 **06:48:29 → 07:18:48 local (EDT, UTC−04:00)** |
| Target attempt | `SPEECHRL_DATA_DIR/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59` |
| Attempt manifest status | `ABORTED` (bind failure; inference complete) |
| Copy performed | 2026-08-16, by the post-flight operations task, byte-for-byte with `cp -p` |

The umbrella amendment disclosing this read gives the window as 06:48–06:57. That is the window of
the *probe and decision* phase. The scoring and derivation scripts it authorized continued to run
until roughly 07:11, and the message that triggered the metric-definition amendment was written at
07:18:48. The archive therefore preserves the full 06:48:29 → 07:18:48 span so that the derivation
outputs are not separated from the probes that justified them.

**The read predates the metric pin.** The HER / RIR formulas were pinned only afterwards — see
umbrella `wiki/experiments/speech-aware-evidence-acquisition/2026-08-16-p2-metric-definition-amendment.md`
§2. Anything in these outputs that touches HER or RIR was therefore computed against the criteria
that existed at 2026-08-16 morning, not against the pinned formulas, and must be re-derived from the
preserved bytes rather than quoted directly.

## Were the output bytes found?

**Yes.** The salvage read's derived outputs survive, not merely the scripts:

| File | Bytes | What it is |
| --- | --- | --- |
| `r0bias.asr-wer.json` | 779118 | ASR-WER scorer output — aggregate + per-sample WER, ins/del/sub, `ref_hit_mask` |
| `r0bias.entity-wer.json` | 39193 | Entity-WER scorer output — aggregate, per-entity-type and per-sample |
| `r0bias.copycount.json` | 18397 | Pre-localize echo / copy-count measurement (D7E guard-2 aperture rule) |
| `score_r0bias.log` | 3761 | stdout of the scoring run |
| `copycount.log` | 8680 | stdout of the copy-count run |
| `splice_effect.log` | 1281 | stdout of the replay-splice / HER-substrate run |
| `tailcheck.log` | 1131 | stdout of the artifact-truncation check |
| `verify_identity.log` | 1133 | stdout of the identity re-derivation |

Consequence: **the archival replay of the spent read is not needed to recover the numbers.** That
replay is pre-authorized by the owner (2026-08-16), but it is **not performed by this task** — this
task is preservation only. No script in this directory was executed here, and no scoring was run.

## What the tooling did

- `p2_diag.sh`, `p2_salvage_probe.sh`, `p2_count_r0bias.sh`, `p2_meter.sh`, `p2_reconcile.sh`,
  `probe1.sh`, `probe2.sh`, `probe3.py`–`probe6.py` — established that the aborted attempt's durable
  bytes were complete and countable (trace record kinds, distinct sample IDs, MODEL_REQUEST /
  MODEL_RESPONSE counts, metered audio seconds), i.e. that a salvage read was possible at all.
- `tailcheck.py` / `run_tailcheck.sh` — proved `trace.jsonl` and `outputs.jsonl` end on a complete
  JSON record, so nothing was truncated by the abort.
- `verify_identity.py` / `run_identity.sh` — re-derived the arm config, protocol hash and split
  identity from the committed repository and the umbrella lock, the way `core.bundle.verify` does
  for a COMPLETED bundle, proving the dead manifest's identity still reproduces exactly.
- `score_r0bias.py` / `run_score.sh` — **the read itself.** Calls the study's own frozen scorers
  `core.scorers.score_asr_outputs` and `core.scorers.score_entity_wer_outputs` with the same
  `(outputs_path, lock, root)` signature the in-run `score_bundle` path uses, so the numbers are
  bit-identical to what a COMPLETED manifest would have carried. Writes only to the scratchpad.
- `copycount_r0bias.py` / `run_copycount.sh` — pre-localize echo / copy-count measurement, reusing
  `reproduction.replay_loop._reference_echo_reject`, `_unsupported_reference_word` and
  `core.retrieval.normalize_term` rather than reimplementing them.
- `splice_effect.py` / `run_splice.sh` — whether accepted REPLAY splices reached the final
  transcript, plus the HER substrate under the then-current in-repo criterion.
- `cost_recover.py` — recovered the token/latency aggregates the ABORTED manifest recorded as
  `NOT_AVAILABLE`, by summing the surviving per-call COST trace channel.
- `timing.py` / `run_timing.sh`, `show_han.py`, `checkjob.sh`, `gpu_load.sh`, `why_idle.sh`,
  `env.sh` — cost and host-state instrumentation around the read.
- `p2_resume_probe.sh`, `mk_resume_arms.sh`, `p2_resume_launch_only.sh`,
  `p2_resume_launch_detached.ps1`, `p2r_now.sh`, `p2r_watch.sh`, `p2r_cycle.sh`,
  `p2r_wait_infer.sh`, `p2r_instr.sh`, `p2r_inspect_struct.sh`, `p2r_r0bias_ref.sh`,
  `featcache_check.sh`, `featcache_dir.sh`, `p2r_featcache_probe.sh`, `duty.sh` — the resume
  decision and launch path that followed directly from the read. `mk_resume_arms.sh` built
  `docs/arms/p2-rladder-resume.arms` by **verbatim slicing** of `docs/arms/p2-rladder.arms`, so the
  pre-registered reads and BRANCH RULES could not be altered by retyping.
- `append_ledger.sh` — appended the two 2026-08-16 notes to `docs/exposure-ledger.md`. Preserved
  because it is the authoring record of those ledger entries.
- `msg1.txt`, `msg2.txt`, `p2-metric-msg.txt`, `resume_commit_msg.txt`, `p2r_instr.state`,
  `inventory.py`, `p2_extract.py`, `p2_report.py` — session correspondence, the commit message used
  for the resume commit, and the two reporting helpers (dated 2026-08-15) that the salvage read
  reused.

> **Do not re-run anything in this directory.** These are session-local scripts with absolute paths
> to one machine's scratchpad. `append_ledger.sh` and `mk_resume_arms.sh` *mutate the repository*
> (`docs/exposure-ledger.md`, `docs/arms/`), and re-running the scoring scripts would repeat a read
> whose one-shot budget is already spent.

## Selection rule and withheld bytes

The source scratchpad is a long-lived multi-day session workspace (2026-08-10 → 2026-08-16,
several hundred files including Git clones and unrelated campaign tooling), not a salvage-only
folder. The archive therefore applies an explicit, auditable rule rather than copying the whole
tree:

> Every top-level regular file whose mtime falls in the salvage window
> 2026-08-16 06:48:29 → 07:18:49 local, **plus** the two 2026-08-15 predecessors `p2_extract.py`
> and `p2_report.py` that the read reused.

That yields the 61 files covered by `MANIFEST.sha256`. Three files inside the window were withheld
from the commit but are recorded here so they stay addressable at their source path:

| Withheld file | Bytes | SHA-256 | Reason |
| --- | --- | --- | --- |
| `one.outputs.jsonl` | 23134 | `a879fc4261865dd98fe01cc5050b4705afbd6ed8a7b003634e4bfd81693c402a` | A single raw model-output row (one line, with request/response hashes and response text). The repository must not commit raw traces; the authoritative copy is the attempt's `outputs.jsonl` under `SPEECHRL_DATA_DIR`. |
| `cjk-inventory.json` | 102261 | `d10885f538436e6755cc3bec924084e5f7cf3a01b3bccd7c4335c1af87b4ed95` | Unrelated to the salvage read — a repo-wide CJK path scan belonging to the English-only rewrite that landed as `7bf251f`. |
| `cjk-inventory2.json` | 99825 | `34b856b78c653ec2b39da66e15121ece9220d0f11bc8a9b50f72f3effb5f57d7` | Same, and outside the window (07:19:28). |

## Integrity

`MANIFEST.sha256` lists the SHA-256 of all 61 preserved files, in the format
`sha256sum` emits (binary mode). It does not cover `README.md`, `.gitignore`, or itself, which are
authored by this archive rather than preserved by it. Verify with:

```bash
cd docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage
sha256sum -c MANIFEST.sha256
```

Every preserved file was already LF-only when copied, and `git ls-files --eol` reports `i/lf w/lf`
for all 61, so the repository's `* text=auto eol=lf` normalization introduces no drift: the hashes
above hold against a fresh checkout, not only against the machine that made the copy.

The `.gitignore` in this directory re-includes `*.log` past the repository-wide rule; see its
comment for the rationale.
