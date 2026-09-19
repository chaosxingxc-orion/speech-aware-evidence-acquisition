# Cell EFF-1 launch runbook: constant native tool-schema rendering on the sealed anchor

Status: **REGISTERED BEFORE CONTACT. BOTH CELLS `held`.** Author: the EFF-1 registration agent,
worktree `/home/chao/saea-worktrees/fable-eff1`, branch `fable/eff1`, base commit `6851acdc`.
Produced with **zero model, tokenizer, encoder, ASR, scorer and server contacts**; `SPEECHRL_DATA_DIR`
was read read-only apart from this cell's own model-free prepared artifacts.

Read first:
[`../2026-09-19-slurp-eff1-tool-constant-v1-preregistration.md`](../2026-09-19-slurp-eff1-tool-constant-v1-preregistration.md),
the measured motivation
[`../../results/2026-09-19-slurp-throughput-root-cause-v1.md`](../../results/2026-09-19-slurp-throughput-root-cause-v1.md)
(lever **L1**), and the mechanism
[`../../superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md`](../../superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md).

## 0. What kind of cell this is, in one paragraph

**EFF-1 is an EFFICIENCY cell.** Its primary deliverables are throughput measurements — prefilled
prompt tokens per row, GPU hours per 1,080 rows, contacts per row, slot occupancy, utilisation, the
per-position cache table, and `distinct_tool_schemas_sha256 == 1` on every row — read from the
flight's own sealed receipts, trace and manifest and from the resident session's `server.log`. Its
**admission rule is NEUTRAL**: the official pooled SLU micro F1 and intent accuracy must be
**non-inferior** against the sealed dual-store anchor at the B0r own-null margins. There is no
ADMITTED-on-a-gain clause. The efficiency numbers are reported whatever the verdict word is. **An
efficiency cell does not count toward owner decision 30's headroom trigger.**

## 1. What is registered here

| file | what it is |
| --- | --- |
| `protocol-registered-v1.json` | the registered protocol: authority, base, the one factor and the one non-factor key, the comparator, the efficiency deliverables and how they are measured, metrics, diagnostics, resampling, the decision rule, smoke acceptance, prompt fit, budgets, the resume clause and what is not claimed |
| `generation-plan-v1.json` / `-registered-v1.json` | the 1,080-row arm's prospective and registered execution plan |
| `fit-plan-v1.json` / `-registered-v1.json` | the arm's native contact-fit plan |
| `smoke-generation-plan-v1.json` / `-registered-v1.json` | the four-row smoke's plan |
| `smoke-fit-plan-v1.json` / `-registered-v1.json` | the four-row smoke's FIT plan |
| `analysis-recipe-v1.json` | the paired non-inferiority read **and** the required efficiency tables |

Config fragments: `configs/baseline/slurp-native-anchor-tool-constant-train-fold-a-v1.json`,
`configs/baseline/slurp-native-anchor-tool-constant-smoke-4-v1.json`,
`configs/experiment/slurp-native-tool-constant-anchor-train-fold-a-v1.json`,
`configs/experiment/slurp-native-tool-constant-anchor-smoke-4-v1.json`,
`configs/campaign/slurp-native-tool-constant-anchor-train-fold-a-v1.json`.

## 2. The one configuration change

`native_episode.tool_schema_rendering: "constant"`, on the sealed dual-store anchor baseline. `OFF`
is the key's absence, which *is* the anchor's configuration.

`native_episode.finite_completion_policy: "deliver-latest-or-abstain"` is declared beside it. It is a
**harness declaration required by `scripts/checks/finite_completion_policy_check.py`, not a factor**:
it renders no request byte, and `docs/receipts/slurp-finite-completion-exposure-v1.json` proves zero
finite completions on the anchor, so the comparator side is provably unaffected. See the
preregistration, section 3.3.

## 3. Mint the receipt, then re-pin and flip

The coordinator mints
`$DATA/coordination/slurp-eff1-tool-constant-v1/root-admission-v1.json` with decision id
**`slurp-eff1-tool-constant-admission-v1`** (already written by this registration in the shape cells
B0r, B4b, B5e, B8a and B8b use), then re-pins and flips.

**Re-pin BOTH cells in one cycle.** Round 2 of the re-pin tool rewrites the protocol document's
SHA-256 inside *every* plan in this package, so re-pinning one cell alone leaves the other cell's
ledger `Plan SHA256` stale.

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"

$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-tool-constant-anchor-smoke-4-v1 \
    --cell slurp-native-tool-constant-anchor-smoke-4-v1 \
  --experiment slurp-native-tool-constant-anchor-train-fold-a-v1 \
    --cell slurp-native-tool-constant-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-19-slurp-eff1-tool-constant-v1 \
  --preregistration docs/readiness/2026-09-19-slurp-eff1-tool-constant-v1-preregistration.md \
  --package-name slurp-eff1-tool-constant-v1 \
  --decision coordination/slurp-eff1-tool-constant-v1/root-admission-v1.json \
  --decision-id slurp-eff1-tool-constant-admission-v1 \
  --set-ready
```

> **Memory rule, and it applies here.** `repin_cell.py` rewrites every plan in a readiness package.
> This package contains exactly one cell family (smoke + arm), which is the shape that rule asks for;
> there is no sibling cell in it whose closed plan could be rewritten.

**No rebuild is expected, and that is the point.** Both baselines already pin **this cell's own**
prepared artifacts, built in this registration with the model-free `prepare-supply` step under each
cell's own run id:

| cell | prepared artifact | SHA-256 | Perception `output` SHA-256 |
| --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json` | `84b8ea643bdb9e5a47a9bb5dd39d1101fcaae3cde22116739464fdd6799c7659` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| smoke | `prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1/phase-supply-v1.json` | `b46ce333c2636bbe94d067b40f976cd0ba80723096187bd60d1a2bfb7c1a844a` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |

`core.flight.repin.ensure_artifact_pinned` will find both pins **valid**, rebuild nothing, and add
nothing to `assert_no_residue`'s scan — which is exactly why this package did not inherit the
anchor's pins. The two Perception outputs were asserted **by hand** in the registration against the
sealed anchor preparation's own output and the shared four-row reference, and both matched exactly.
That hand assertion replaces `_compare_artifact_output`, which does not run when there is nothing to
rebuild.

> **`--allow-output-change` must never be passed.** If either output SHA-256 stops matching, a merge
> changed the knowledge channel — **stop and report.**

**Commit the re-pin before launching**: a COMPLETED manifest reads `study_commit` at finalize and
refuses a dirty tree.

Drop `--set-ready` and the two `--decision` flags to re-pin only, for example after merging master.

## 4. Pre-launch checklist

1. One experiment in flight. The arm does not open before this cell's own four-row smoke seals.
2. `git -C "$REPO" status --porcelain` is empty. **Fly from a clean detached worktree pinned at the
   admitted commit.** No receipt from this preparation lives inside the repository.
3. No other flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`. **Attach only, never spawn or stop.**
5. If a flight is launched as a Windows Scheduled Task (owner decision 24), register the task with
   the **battery and idle conditions disabled and no execution time limit**, and keep `powercfg` away
   from the machine for the duration.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Do **not** run `scripts/checks/derived_media_confinement_check.py` from inside the checkout: it
   rewrites a receipt directory and would dirty the tree the manifest reads at finalize.
9. **Note the session's log position before the smoke starts.** The efficiency read joins
   `server.log` records to client contacts per slot; recording the byte offset of `server.log` (and
   of `monitor.jsonl`) immediately before the lease opens makes that join cheap and unambiguous
   afterwards. This is a convenience, not a gate.

A contact-free `check` can be re-run at any time on a clean tree (the re-pin tool runs it for you):

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-tool-constant-anchor-smoke-4-v1 \
  --cell slurp-native-tool-constant-anchor-smoke-4-v1
```

## 5. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open, then run the
standalone worker against `--experiment slurp-native-tool-constant-anchor-smoke-4-v1 --cell
slurp-native-tool-constant-anchor-smoke-4-v1`, exactly as every earlier four-row form smoke of this
roster is run.

**Acceptance is the preregistration's section 10, all eight criteria.** The three that are specific to
this cell:

* **`distinct_tool_schemas_sha256 == 1` on every row**, from the sealed
  `saea-native-tool-schema-rendering-v1` block, with `authority_tool_names` `[]` on perception /
  solver / planner against `["saea-tool-task-contract-v1"]` on the two Reviewer contacts;
* **every Reviewer request byte-identical** to the sealed anchor's request at the same position of the
  same sample id, and the perception / solver / planner payloads differing from the anchor's in
  **exactly one key, `tools`**, with `tool_choice` still `"none"`. The anchor has **no four-row smoke
  of its own** — it flew once, directly, over the 1,080-row roster — so the comparator is the anchor's
  own sealed trace under `$DATA/runs/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/`,
  restricted to these four sample ids, which are members of that roster. That trace is **read-only**:
  never write to it, and read no answer, reference or quality field of it;
* **the cache actually moves at the server.** The server-reported cached-token share at the
  first-Reviewer and Planner positions must rise from the anchor-era 23.6 % and 19.8 % toward the
  same-tools handover's 83.5 %, and the packet re-decode share at those positions must fall from
  100 % toward 0. Four rows cannot establish a rate, so no threshold gates the smoke here — but a
  cached share that does **not** move means the mechanism did not reach the server, and that **is** a
  failure.

No scorer. No answer, reference or quality interpretation. A structural smoke result is never a
quality result.

## 6. The arm

Re-pin the arm again (without `--set-ready` if it is already ready, for the protocol-hash reason in
section 3), then fly
`configs/campaign/slurp-native-tool-constant-anchor-train-fold-a-v1.json` through the shared campaign
path. The campaign acquires its own `GenerationLease` against the resident session and schedules the
one official score at finalize. **`coordinate-fit` must NOT be run**: the FIT gate runs inside the
same campaign, and a standalone fit run would double-charge the FIT row.

## 7. The read

`analysis-recipe-v1.json`, whose output root is
`$DATA/analysis/SAEA-SLURP-EFF1-TOOL-CONSTANT-ANCHOR-V1-PAIRED-ANALYSIS-V1`. Two halves, both
mandatory:

* the **efficiency tables** (recipe `efficiency_tables_required`): the headline throughput row, the
  five-position cache table with the B4b column **labelled as a reference**, the constancy table, the
  prefill join-quality share, the client prompt-token rise stated as an expected rise, and the slot
  occupancy / utilisation block;
* the **paired non-inferiority read** against the sealed anchor, under the decision rule fixed in the
  preregistration's section 7, with the STOP condition checked first.

The verdict document is `docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`. It must state,
in these words, that **an efficiency cell does not count toward decision 30's headroom trigger**, and
— if the read is NEUTRAL — that the key now enters the SLURP default plan, that every later cell and
the test read adopt it, and that a later cell registered against a sealed **per-role** arm must say
so.

## 8. Registered hashes (pre-flip)

| item | value |
| --- | --- |
| arm composed / protocol | `02b13593d920d6dd93977cf608da8812cb86ddaae3a1222b0287fe50f7507602` / `dc357b14d608d1fd19ea1a879c3fde59809e0af01a0726c2131eabd513af54ab` |
| smoke composed / protocol | `a007c30b35856a411afcf921d62a618a2a853ec4f044e38f108d2440ed42fc01` / `67746f3211e5e62f330fd2f658c0a60673506725d847b9f1ce166ce989d17fcc` |
| `protocol-registered-v1.json` | `6ef936762b024d812b4045db163dd0a3f6bd45c084af5e514cae6d6c1287b1cb` |
| `generation-plan-registered-v1.json` | `04fd70c68b179b236b106ed9cf310d7b46b7cf671ca5572cf13791af6d015704` |
| `fit-plan-registered-v1.json` | `82f72d71b270b627e8d3b0c15fc2bc43b575283e01696dd3d76481b9a4f1f354` |
| `smoke-generation-plan-registered-v1.json` | `d241965ffece2d58aee659bb4e199e4f9341d706142413192a67daf1bf0f75af` |
| `smoke-fit-plan-registered-v1.json` | `48a7ba70b1fe9dd8d447198be44c34f1615b2af92fb2344a1ebd3d9a2fe19f44` |
| `analysis-recipe-v1.json` | `9c7858476e500413fd733ddde333efef570170facd8641d8a2a4c54754bcc83c` |

These are the values of the five config fragments and of the files in this directory **exactly as
committed**: readiness `held`, this cell's **own** preparation requirement pinned, no decision
requirement. `scripts/flights/repin_cell.py` rewrites every one of them in dependency order at the
flip; never edit one by hand.

The method was verified on this tree: composing cell B7a v2's own four fragments reproduces its
registered composed `73a817ff…` / protocol `f5a6733f…`, and its smoke's `fbe7556e…` / `1f3bdd15…`.

## 9. What this package does not authorise

No readiness flip, no model contact, no `prepare-supply` beyond the two model-free artifacts already
built and pinned here, no re-pin, no default-plan edit and no harness-admission entry. The admission
entry for the module "constant native tool-schema rendering" is written from the sealed verdict,
never from this registration.
