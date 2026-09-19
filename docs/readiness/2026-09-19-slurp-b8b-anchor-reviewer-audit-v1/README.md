# Cell B8b-anchor launch runbook: the Reviewer slot-audit block, re-based on the anchor

Item E19 re-bases cell B8b and registers it as a new single-cell package. The registration agent
made **zero model, tokenizer, encoder, ASR, scorer, server and paid-API contacts**: it touched no
run directory, held no flight lock and started, stopped or queried nothing. Its only writes outside
the repository are the two model-free `prepare-supply` artifacts under `prepared/` and the root
decision receipt under `coordination/`.

Full statement:
[`../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md`](../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md).

## 0. Why this package exists

Cell B7a v2 (Node Context Policy level L1) read **HARMFUL** on 2026-09-19
([`docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md`](../../results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md)):
official pooled SLU −0.31 pp [−1.81, +1.12], intent −0.65 pp [−2.18, +0.87], and +11.6 % GPU hours
for no gain. Owner decision 32 was pre-authorised for exactly this outcome: cells B7r and B7c close
unflown, level L2 stays unflown, and **cell B8b is re-based on the anchor and re-registered**. The
L1-based registration
[`../2026-09-19-slurp-b8b-reviewer-audit-v1/README.md`](../2026-09-19-slurp-b8b-reviewer-audit-v1/README.md)
is superseded.

**The block never depended on the L1 policy.** The B7a v2 rendering diagnostics are explicit: *0
parsed of 1,243 structured review-finding rows — FALLBACK-RAW on 100 % of them*. The audit read no
parsed Reviewer output. It only needed the structured **rendering slot** of the Reviewer's own draft
boundary — somewhere to be appended. Item E19 gives it a second attachment, `sealed-draft`: with the
boundary at `raw`, the block is appended to the **sealed Solver response** the Reviewer already
receives. The fragment then declares no `context_policy` at all, and the ON-vs-OFF request diff is
exactly the block, on the Reviewer contacts.

## 1. What is registered

| | |
| --- | --- |
| arm run | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` |
| arm attempt | `attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1` |
| arm FIT run / attempt | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-reviewer-audit-anchor-train-fold-a-fit-v1` |
| arm composed / protocol | `04592f9515a24cc3f34f57787202209d3391f04f363e4d863e1ce6c3cc6f0ae2` / `8b339a25d25e6a53a1d7efff57ad46861f8ba0a84d7f29f2257919cf496b7e13` |
| arm fragments | `configs/baseline/slurp-native-anchor-reviewer-audit-train-fold-a-v1.json`, `configs/experiment/slurp-native-reviewer-audit-anchor-train-fold-a-v1.json`, `configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1.json` |
| arm prepared supply | `prepared/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json`, file `4d3233fd…`, **output `ba5e1faa…` = the sealed anchor's own** |
| smoke run | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1` |
| smoke attempt | `attempt-slurp-native-reviewer-audit-anchor-smoke-4-generation-v1` |
| smoke FIT run / attempt | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-reviewer-audit-anchor-smoke-4-fit-v1` |
| smoke composed / protocol | `b27a7ecdc32565e2d5d26735ce4d0076e7bc0df6cbe35092572905c2cfebffd3` / `07cd8bb07b14119b96b8c3ce352534f79cac1a26bca57b017a3096ea913b956c` |
| smoke fragments | `configs/baseline/slurp-native-anchor-reviewer-audit-smoke-4-v1.json`, `configs/experiment/slurp-native-reviewer-audit-anchor-smoke-4-v1.json` |
| smoke prepared supply | `prepared/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v1.json`, file `b89ec1ca…`, output `512583ec…` |
| the one factor | `native_episode.reviewer_audit` = the released view `slot-audit-v1` (release `eaa2dd0d…`, snapshot `0cc3f96c…`, table content hash `d4cd4bf3…`, template `probes/ncp_slurp_slot_audit_reviewer_v1.txt` `88cc927d…`; 60 intents, 54 entity types, 9,354 construction utterances) |
| the second key, **not** a factor | `native_episode.finite_completion_policy` = `"deliver-latest-or-abstain"` |
| comparator | the sealed dual-store anchor, run `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (official pooled SLU-F1 48.53363, intent 77.96296 = 842/1080, n = 1,080) |
| margins | cell B0r's own null, h_SLU **1.1218** / h_intent **1.0051** (owner decision 38's fallback: the anchor has no request-identical replicate of its own) |
| budgets (arm) | 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, **1 official complete score** |
| budgets (smoke) | 44 generation contacts, 176 FIT endpoints, 117 repeated speech seconds, 1.0 fit-inclusive GPU hour, 24 native task-contract calls, **zero scoring jobs** |
| service | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, decoder-only Q4_K_M, c98304 np4, 24,576-token slots |
| readiness | both cells **`held`**, with the `preparation` requirement pinned and **no decision requirement yet** |

Both arms are **node-free**: neither carries the delivery-time normaliser node (module M3, cell
B8a). The verdict must state that.

## 2. The launch step: `scripts/flights/repin_cell.py`

The decision receipt is already minted at
`coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-v1.json`, decision id
`slurp-b8b-anchor-reviewer-audit-admission-v1`. The coordinator applies it and flips readiness in
one cycle, **one cell per package invocation** (the B4 org-cells lesson: `repin_cell.py` rewrites
every plan in a readiness package, so a package holding a sibling cell's plans gets them rewritten
too — here both cells share one package, so run the tool once for both cells together, never once
per cell).

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$REPO/src

$PY -B "$REPO/scripts/flights/repin_cell.py" \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-reviewer-audit-anchor-smoke-4-v1 \
  --cell slurp-native-reviewer-audit-anchor-smoke-4-v1 \
  --experiment slurp-native-reviewer-audit-anchor-train-fold-a-v1 \
  --cell slurp-native-reviewer-audit-anchor-train-fold-a-v1 \
  --readiness-dir "$REPO/docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1" \
  --preregistration "$REPO/docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md" \
  --decision coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-v1.json \
  --decision-id slurp-b8b-anchor-reviewer-audit-admission-v1 \
  --set-ready
```

`--allow-output-change` must **never** be passed. Each cell's prepared artifact already exists and
its identity digest already matches its own composed configuration, so the rebuild is a pure
identity check; a refusal means something moved and must be diagnosed, not overridden.

### 2.1 A blocker the coordinator must clear first

`core.flight.cli check` **cannot pass on this geometry today**, for a reason that has nothing to do
with this cell. Since item E17 merged, `core.flight.runtime._assess_prompt_budget` measures the
preflight prompt budget against the **live 24,576-token slot** instead of the retired
32,768-token module default. On the SLURP np4/ctx24k geometry the **anchor's own** Perception
prompt then fails it:

```
prompt budget COMPACT_REQUIRED (not ALLOW) for phase 'perception':
  rendered_text_tokens 18,640   required_window_tokens 19,183
  slot_limit_tokens 24,576      physical_margin +5,393
  operational_reserve 8,192     operational_margin -2,799
  payload_sha256 1315b387d21c24feaa6af03e918ef4f0ba4fc14fc51c18373dc01ca9b4ceab46
```

It reproduces **byte for byte with and without** this cell's two declared keys — same
`payload_sha256`, same token counts — so it is a pre-existing condition of every SLURP native cell
on this geometry, not a property of cell B8b-anchor. It must be cleared before any flight:
a declared `context_budget_limits` block on the composed fragments, a wider serving slot, or a
revisited operational reserve. That is a coordinator/owner call, and this package does not make it.

Because `check` refuses, the composed and protocol hashes above were derived **model-free** through
`core.flight.repin.compute_cell_identity`, which composes exactly the four fragments the CLI
composes. `repin_cell.py` re-derives them and asserts they agree; if the budget blocker is still
open when the tool runs, its final `check` pass will report the same refusal.

## 3. Pre-launch checklist

1. The prompt-budget blocker of section 2.1 is cleared.
2. The decision receipt is applied and both cells read `ready`.
3. A clean **detached** flight worktree at the launch commit; a dirty tree kills `finalize`.
4. No flight lock held; one experiment in flight at a time.
5. The resident session identity is `serving-slurp-native-candidate-five-train-a-np4-v1`; agents
   **attach**, never spawn or stop.
6. The Windows Scheduled Task carrying the flight has its battery and idle conditions off and no
   execution time limit; power settings are not touched while it runs.
7. `PYTHONDONTWRITEBYTECODE=1` (bytecode under the frozen scoring package closes the D3 gate) and
   `PYTHONPATH=$REPO/src`.
8. Never run `pip install -e` from a flight worktree: it repoints the shared venv.

## 4. The four-row smoke

Flies first, as soon as the GPU is free. Standalone worker lease plus
`core.flight.cli worker`; no campaign, no scorer. Expected cost: about 20 generation contacts
(≈5 per row) against the 44-contact ceiling, up to 176 FIT endpoints, about 53 speech seconds.

### Accept only if all six hold — structural acceptance only

1. About five contacts per row plus revisions, **no row above 11**, and 4 of 4 rows delivered.
2. The `slot_audit` receipt on **every Reviewer contact of 4 of 4 rows**, with schema
   `saea-reviewer-slot-audit-v1`, `view_id` `slot-audit-v1`, `release_sha256` `eaa2dd0d…`,
   `snapshot_sha256` `0cc3f96c…`, `table_content_hash` `d4cd4bf3…`, `template_id`
   `probes/ncp_slurp_slot_audit_reviewer_v1.txt`, `template_sha256` `88cc927d…`, the three declared
   thresholds and `flag_counts` carrying all four names including the zeros. **At least one Reviewer
   contact of every row carries `applied: true`**; an `applied: false` / `reason: "draft-unparsed"`
   contact is acceptable beside it.
3. The block is an **addition**: the last `block_chars` characters of the exposed
   `reviewer:current-draft` text hash to `block_sha256`, and the text before them is the **sealed
   Solver response byte for byte**. No other boundary row carries a `slot_audit` block, and the
   compilation record's `template_sha256s` carries exactly the block's three assets.
4. **Every** boundary row is at `level: "raw"` with `template_id: null`, and every row without a
   `slot_audit` block has `rendered_sha256` equal to its source's `content_sha256`. That equality is
   the whole request-channel claim, checked rather than asserted.
5. The request-fit receipts: every realized request fits.
6. Any row whose `terminal_disposition.reason` is `"finite_completion"` is **retained and
   reported**, not an error. An **abort** on `finish_reason` `length` is a failure: it would mean the
   declared `finite_completion_policy` did not reach the runtime.

The Perception request is *expected* to be byte-identical to the anchor's own four-row bytes, but it
is not an acceptance criterion: greedy decoding is not bitwise reproducible across batch
compositions, so the request-byte claim is proved over a deterministic fake transport in
`tests/unit/test_native_episode_runner_reviewer_audit.py`, not on the wire.

## 5. The 1,080-row arm

Opens only after the smoke seals. Flown by `core.flight.cli campaign` over
`configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1.json`, which schedules the one
official score at finalize. Expected cost about 5,420 contacts and 3.6 GPU hours against the 12.0
ceiling. **`coordinate-fit` must not be run separately**, or the FIT row is double-charged.

## 6. The paired read

Pinned by [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and preregistration section 6. The
comparator is the sealed anchor's own score artifact; it is never re-flown or re-scored. The rule is
fixed before any number is seen and the read happens **exactly once**. Output root
`DATA/analysis/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1/`; verdict document
`docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md`.

## 7. Post-read

* **ADMITTED** — the coordinator writes the `episode`-class switch entry into
  `docs/receipts/harness-admission.json` (form in `protocol-registered-v1.json`
  `harness_admission_entry_form`) and the module enters the SLURP default plan.
* **NEUTRAL or HARMFUL** — no default-plan edit, and under owner decision 30 the one-factor
  NEUTRAL/HARMFUL streak advances toward the v2.0 lock trigger.

Either way: run `engineering_base_check`, `harness_admission_check`, `results_ledger_check`,
`finite_completion_policy_check` and `tool_catalog_check`, and close the four exposure-ledger rows.

## 8. Things the coordinator should know

* **The efficiency note is per role.** The block adds tokens to the Reviewer contacts only. The
  verdict reports prompt tokens per role beside the anchor's, never a whole-run figure alone.
* **The second declared key is asymmetric by construction.** The sealed anchor flew without
  `finite_completion_policy` and its receipt records zero finite completions, so on the comparator
  side the key would have changed nothing. The asymmetry is measured, not assumed, and the verdict
  states it.
* **`core.flight.cli wire-check` remains unavailable** for any native-episode cell; the substitute is
  `tests/unit/test_native_episode_runner_reviewer_audit.py`.
* **Comparator hashes are carried, not re-derived.** Nothing in this package re-reads the anchor's
  run directory.
* **There is deliberately no `check` receipt in this package**, for the reason in section 2.1.
