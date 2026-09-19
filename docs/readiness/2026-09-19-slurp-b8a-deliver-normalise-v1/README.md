# Cell B8a launch runbook: the delivery-time normaliser node

Everything the coordinator needs for cell B8a is in this directory and in the committed configs.
**Five steps remain: mint the decision receipt (section 2), re-pin and flip the smoke, commit, fly
the four-row smoke, then run the model-free read.** Preregistration:
[`../2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md`](../2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer, server and paid-API
contacts**, never started, stopped or queried the resident service, never wrote a run directory
(sealed outputs were read only through copies under a temporary directory), and did not touch any
flight in progress.

## 0. Why this cell exists, in one paragraph

Owner directive 26 puts this program's offline analyses **inside agent nodes**; owner decision 23
makes the bar and every final evaluation the **official, unprojected** SLURP number. Module M3 —
USE projection v3 (`R_action`, then legal-label projection v2, then filler normalisation P2) — has
lived in the scorer since item E4, where the official scorer credits none of it. Item E11 built the
same rule as a deterministic, zero-contact delivery node. Cell B8a decides it. Because the node is
deterministic and makes no contact, **its admission is read model-free from sealed arms**; the only
thing a flight still owes is a four-row proof that the node executed *in the agent*.

## 1. What is registered

| item | value |
| --- | --- |
| smoke cell | experiment and cell `slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1` |
| smoke run / attempt | `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1` / `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-generation-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-FIT-V1` / `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-fit-v1`, 176 endpoints, inside the same worker |
| baseline | `configs/baseline/slurp-native-anchor-exemplars-k20-deliver-normalise-v3-smoke-4-v1.json` |
| experiment | `configs/experiment/slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1.json` |
| composed / protocol (smoke) | `c281111fa1f79d03cedf741614c6941544a8f0ee4ffca43a8796ee2e4ab2fc74` / `2095bbfd11767a497d16b880b62e34325cd60af8a47a503961ae92bbc0015e5e` |
| prepared supply (inherited pin, to be rebuilt by the re-pin tool) | `prepared/SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1/phase-supply-v1.json`, SHA-256 `eca235e6719888cc629b6e4efbdb4a31666637aca656538fac3c76ce78899e0f`, **output** SHA-256 `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |
| budgets (smoke) | 44 generation contacts, 176 FIT endpoints, 117 repeated speech seconds, 1.0 fit-inclusive GPU hour, 24 native task-contract calls, **zero scoring jobs** |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held`, with the inherited `preparation` requirement and **no decision requirement**; the coordinator mints the receipt and flips with the tool of section 2 |
| model-free read | registered in the preregistration section 8 and in [`analysis-recipe-v1.json`](analysis-recipe-v1.json); no GPU, no model contact, no flight |
| **no full-roster B8a arm is registered** | the node's effect over any sealed arm is computable from that arm's own bytes; `configs/experiment/slurp-native-b8a-deliver-normalise-v3-{anchor,exemplars-k20}-train-fold-a-v1.json` stay `held` from item E11 and are **not** part of this package |

Protocol hashes were computed the way the precedent computes them, model-free:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-exemplars-k20-deliver-normalise-v3-smoke-4-v1",
            "slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb"))'
```

**The method is verified against sealed registered values on this tree.** The same two calls
reproduce the sealed anchor recovery's protocol
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c` and cell B1's recovery arm's
composed `114b791752e160ed0f409fedf12d034b3cc05a8789b4423d1700cc6cb7df000c` / protocol
`c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d`.

**These hashes describe the fragments exactly as committed** — readiness `held`, the inherited
preparation requirement, **no decision requirement**, the inherited prepared pin. Re-pinning,
adding the decision requirement and flipping readiness each change them. **Do not do that by hand —
use the tool of section 2.**

## 2. The launch step: `core.flight.repin`

Shell prelude for every command below:

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"
```

**The coordinator mints the decision receipt first** — this package deliberately does not, because
a registration agent has no admission authority. Write it to
`$DATA/coordination/slurp-b8a-deliver-normalise-v1/root-admission-v1.json` in the same shape cells
B0r, B4b, B4b-rep and B5e use, with decision id **`slurp-b8a-deliver-normalise-admission-v1`**.

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
    --cell slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --readiness-dir docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1 \
  --preregistration docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md \
  --package-name slurp-b8a-deliver-normalise-v1 \
  --decision coordination/slurp-b8a-deliver-normalise-v1/root-admission-v1.json \
  --decision-id slurp-b8a-deliver-normalise-admission-v1 \
  --set-ready
```

**Expect a rebuild, and expect it to prove something.** The baseline inherits cell B1's own
recovery-*smoke* prepared pin. Item E11 changed `core/flight/runtime.py`, which is one of the files
the prepared artifact's identity digest pins, so `core.preparation.load_artifact` will refuse that
artifact for this cell and the tool will derive a fresh one into
`prepared/SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1/phase-supply-v1.json`.
`_compare_artifact_output` then **refuses the rebuild unless the new Perception selection is
byte-identical to the inherited one** (output SHA-256
`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`, 4 of 4 rows). That refusal is
the model-free proof that the delivery node moves no knowledge-selection byte.

> **`--allow-output-change` must never be passed here.** If the output SHA-256 stops being
> `512583ec…`, a merge changed the knowledge channel — **stop and report**.

Drop `--set-ready` and the two `--decision` flags to re-pin only, for example after merging master.
The tool recomputes the composed and protocol hashes, rewrites this README, the preregistration, the
plan pairs, the protocol document and the exposure-ledger notes for the package's run ids, then runs
`core.flight.cli check` and asserts the runtime-derived hashes agree. **Commit the result before
launching**: a COMPLETED manifest reads `study_commit` at finalize and refuses a dirty tree.

## 3. Pre-launch checklist

1. Owner decision 27's order is respected: the **B4b replicate resume** is closed before this cell
   opens. One experiment in flight.
2. `git -C "$REPO" status --porcelain` is empty. **Fly from a clean detached worktree pinned at the
   admitted commit.** No receipt from this preparation lives inside the repository.
3. No other flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`. **Attach only, never spawn or stop.**
5. If the smoke is launched as a Windows Scheduled Task (owner decision 24), register the task with
   the **battery and idle conditions disabled and no execution time limit** — `schtasks /query /tn
   <task> /xml` must show `<DisallowStartIfOnBatteries>false</…>`,
   `<StopIfGoingOnBatteries>false</…>` and `<ExecutionTimeLimit>PT0S</…>` — and keep `powercfg`
   away from the machine for the duration. The B5e abort of 2026-09-18T14:40Z was exactly this
   condition firing.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Do **not** run `scripts/checks/derived_media_confinement_check.py` from inside the checkout: it
   rewrites `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/`
   and would dirty the tree the manifest reads at finalize.

A contact-free `check` can be re-run at any time on a clean tree (the re-pin tool runs it for you):

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --cell slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1
```

## 4. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --cell slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --owner root-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --cell slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1.worker-lease.json"
```

If the smoke runs as a Scheduled Task instead of an open terminal, the task's action is that same
`worker` command, with the lease issued first and its token file passed through; the task
conditions of section 3 item 5 apply unchanged.

Expected: a few minutes of wall clock, about **20 generation contacts** (5 per row; 44 is the
ceiling), up to 176 FIT endpoints, about 53 repeated speech seconds, **no scorer**.

### Accept only if all five hold — structural acceptance only

1. the trace carries Perception, Solver, Reviewer and Planner contacts, **five per row**, and no row
   exceeds 11;
2. the Solver request carries the twenty `train-exemplars::…` typed content blocks, and there is one
   `*.request-fit.json` per realized contact under
   `$DATA/prepared/SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-FIT-V1/attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-fit-v1/`,
   every one with `every_request_fits = true` and every required-token count below 24,576;
3. **the `native_episode_receipt.deliver_normaliser` block is present on 4 of 4 rows**, with
   `schema` `saea-deliver-normaliser-v1`, `normaliser_id` `saea-deliver-normalise-v3`, `version`
   `1`, `carrier_lock_key` `slurp` and `applied: true`;
4. **the replay reproduces the delivered bytes on 4 of 4 rows** (command below), and the prediction
   triple parsed out of each delivered answer equals the v3 scorer's own triple;
5. the worker prints a seal, the manifest is sealed and the tree is still clean.

> **What the four rows will probably not show.** On the sealed B1 arm's own bytes the rule repairs
> nothing on all four of these rows (`applied: true`, `changed: false`, `rendering_suppressed:
> true`, 4 of 4). Greedy decoding at temperature 0 is not bitwise reproducible across batch
> compositions, so a repair may occur — but **acceptance does not require one**. The repair path is
> proved by the 1,080-row sealed replay on three arms (preregistration section 6) and by the E11
> unit tests.

Inspect the seal, model-free, over a COPY — never open a run directory for writing:

```bash
RUN=SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1
ATT=attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-generation-v1
WORK=$(mktemp -d)
cp "$DATA/runs/$RUN/$ATT/$RUN.outputs.jsonl" "$WORK/outputs.jsonl"

$PY -B -m speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay \
  --outputs "$WORK/outputs.jsonl" \
  --normaliser saea-deliver-normalise-v3 \
  --output-dir "$WORK/replay"
```

Expect `model_calls: 0`, `rows: 4`, `rows_already_normalised: 4` (every row carries the receipt),
and each replayed `text` equal to that row's own delivered `text` — that equality is criterion 4.
Release the lease. A failure stops cell B8a until the fix is proven on this same four-row roster.

## 5. The model-free admission read — no GPU, no model contact

Registered in preregistration section 8 and pinned by [`analysis-recipe-v1.json`](analysis-recipe-v1.json)
and [`sealed-inputs-v1.json`](sealed-inputs-v1.json). It may run **in parallel with any GPU flight**
(owner decision 27) because it makes no contact of any kind and never touches the resident session.

**The driver is to be written** as
`src/speech_aware_evidence_acquisition/analysis/b8a_delivery_node_read.py`; the recipe is its
contract. Once it exists:

```bash
$PY -B -m speech_aware_evidence_acquisition.analysis.b8a_delivery_node_read \
  --repo-root "$REPO" --data-root "$DATA" --lock-path "$LOCK" \
  --recipe docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/analysis-recipe-v1.json \
  --work-dir "$(mktemp -d)" \
  --output-dir "$DATA/analysis/SAEA-SLURP-B8A-DELIVER-NORMALISE-PAIRED-ANALYSIS-V1"
```

It must, in this order: verify every sealed SHA-256 in the recipe; copy each sealed
`outputs.jsonl`; replay `saea-deliver-normalise-v3` over each copy asserting `model_calls: 0` and
1,080 rows in and out; score OFF and ON with `slurp-slu-official-train` and with
`slurp-slu-f1-normalized-v1-train` over byte-identical copies of the sealed bundle; **assert the
STOP condition** — the three OFF arms reproduce 48.53 / 77.96, 61.14 / 80.19 and 62.34 / 80.09, and
the three ON arms reproduce 51.99 / 79.35, 62.67 / 81.76 and 63.78 / 81.85, each to the hundredth —
and only then emit the paired contrasts, the per-scenario tables and owner decision 17's
net-harmed-rows diagnostic.

Read **once**. The decision rule is fixed in preregistration section 8 and is not edited after a
number is seen. Verdict:
`docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`.

## 6. Post-read

- **If ADMITTED or NEUTRAL**: the coordinator writes the `docs/receipts/harness-admission.json`
  entry in the form preregistration section 3 fixes, and adds
  `native_episode.deliver_normaliser = {"normaliser": "saea-deliver-normalise-v3"}` to
  `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`.
  `scripts/checks/harness_admission_check.py` requires both and is the oracle. **From that moment
  every later official SLURP number this program reports is produced by a system that contains the
  node** (preregistration section 4), and every later cell owes a statement of which side of the
  node its comparator sits on.
- **If HARMFUL**: no plan entry, the E4 scorer-side form keeps its diagnostic role, and the record
  keeps the negative — the harness-admission table records negatives as loudly as positives.
- Either way, run `python scripts/checks/harness_admission_check.py`,
  `python scripts/checks/results_ledger_check.py` and
  `python scripts/checks/engineering_base_check.py`, and close the three exposure-ledger rows.

## 7. Deviations the coordinator should know about

- **The idempotence exception.** Re-applying the node to its own output changes nothing on
  1,080 / 1,080 rows of cell B1 and of cell B5e, but on **one** anchor row a `date` filler is not a
  fixed point of P2 (it converges at the second application). Invariant I7n requires *determinism*,
  not idempotence, and the read is unaffected because the scorer applies P2 exactly once and so does
  the node. It does mean `rails/delivery_normalisers.py`'s unqualified "idempotent by construction"
  is proved on cell B1's rows and is not a general property, and that a future ON arm's idempotence
  witness may legitimately report a `changed: true` row. Engineering finding; no code was changed by
  this registration.
- **No `check` receipt is on file** and that is deliberate — see preregistration section 12.
- **`core.flight.cli wire-check` remains unavailable** for any native-episode cell, as it was for
  the anchor, B0, B0r, B1, B4b and B5e: `FlightRuntime._dispatch_phase_program` refuses a native
  episode whose transport is not the real shared speech renderer, and `wire_check` installs a text
  transport double.
- **The E11 full-cell fragments are not this package's.**
  `configs/experiment/slurp-native-b8a-deliver-normalise-v3-anchor-train-fold-a-v1.json` and
  `…-exemplars-k20-train-fold-a-v1.json` were committed `held` by item E11 as engineering
  artefacts. Cell B8a's admission does not need them and this package does not flip them. If a
  later decision wants an in-agent 1,080-row arm, it is a new registration with its own owner GO.
