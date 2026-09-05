# SLURP closed-list headroom: what the sealed M0 prompt actually offered (2026-09-05)

Exposure row: `SAEA-SLURP-MF-CLOSED-LIST-HEADROOM-V1`, profile `model-free-check`.
Zero model, GPU, tool, embedding, network and audio contacts. No gold read anywhere.

## Why this receipt exists

The 2026-09-04 owner directive that opened the closed-list mission rests on a premise:
that the sealed DEV-1000 M0 arm's prompt "offers NO label inventory: the model must
invent scenario/action/entity-type strings", quoting
`rails/adapters/slurp.py::_INSTRUCTION`. The 2026-09-04 scoring-alignment audit says the
same thing in its caveat 4 ("no closed label list offered to the model").

**That premise is wrong for the flown arm, and the correction changes what the
experiment measures.** `_INSTRUCTION` is only half the system message. The other half is
appended by `rails/runner.py::_agent_messages`:

```python
if task_contract not in system_text:
    system_text = f"{system_text}\n\nTask contract:\n{task_contract}"
```

and `SlurpAdapter.build_task_contract` returns
`render_slurp_ontology(load_slurp_ontology(...))`. All 1,000 sealed `MODEL_REQUEST`
records of `attempt-20260825T053342Z-dev1000m0` carry one and the same 5,747-character
instruction (sha256 `cef527896e9beef5774305e01dc29192fc2d5ca89fba5143e82f0b91a7cb86b8`),
and its `Task contract:` half is a JSON document holding **18 scenarios, 46 actions and
55 entity types** (with up to 5 example fillers per type, 263 filler strings in all).

What that prompt never carried is the **pairing**. `scenarios` and `actions` are two
independent lists, so a reader sees 18 x 46 = 828 implied intents where only **60**
`(scenario, action)` pairs occur in `train`. `SlurpOntology` had no field for the
pairing at all, and `docs/checks/.../2026-08-25-slurp-intent-coverage/` had already
measured the 60 without it ever reaching a prompt;
`analysis/dev100_reviewer_audit.py` had already listed it as a known gap in M0.

## What was measured

`headroom.py` reads the sealed outputs bytes of the two DEV-1000 lock arms and asks of
each prediction only whether it names a **legal** label under the TRAIN inventory --
never whether it is correct, so no annotation of `devel` or `test` is opened.

| arm | rows | scenario outside the 18 | action outside the 46 | (scenario, action) not in train | entity type outside the 55 |
|---|---|---|---|---|---|
| DEV-1000 M0 | 1000 | 86 (8.60 %) | 69 (6.90 %) | **322 (32.20 %)** | 2 of 718 mentions (0.28 %) |
| DEV-1000 BLEND | 1000 | 2 (0.20 %) | 2 (0.20 %) | **21 (2.10 %)** | 0 of 693 (0.00 %) |

Sealed inputs: `runs/SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T053342Z-dev1000m0/arm1-m0-outputs.jsonl`
(sha256 `ea7045d3...decc`) and `.../attempt-20260825T054707Z-dev1000blend/arm2-blend-outputs.jsonl`
(sha256 `542a029a...cf14`).

## Reading

1. **The three lists the prompt DID carry are largely respected**: 91.4 % of M0
   predictions name a listed scenario, 93.1 % a listed action, 99.7 % of entity
   mentions a listed type. A prompt-side inventory works when it is present.
2. **The one it did not carry is where the errors are.** 32.20 % of M0's predictions are
   a structurally impossible pair. M0's official intent accuracy is 53.60, i.e. 46.40
   points of error; the impossible-pair class is 32.20 of those 46.40 points, about
   69 % of the whole intent error. The largest single classes are `general/query` (42),
   `music/play` (34), `qa/query` (30), `cooking/createoradd` (21) and
   `calendar/createoradd` (17) -- and `play` is not a SLURP action at all (51 rows use
   it as one), while `general_query`, `qa_query` and `music_query`-adjacent confusions
   are exactly the scenario/action boundary a 60-pair list disambiguates.
3. **BLEND's mechanism is substantially the pairing.** The locked knowledge cell drives
   the impossible-pair rate from 32.20 % to 2.10 % by supplying TRAIN-mined exemplars
   that carry real intent pairs. A closed intent list supplies the same information for
   free, in the prompt, with no retrieval and no second contact. How much of BLEND's
   +22.10 pp intent margin over M0 survives against a prompt-aligned direct arm is
   therefore the question the registered flight answers.
4. **This is an upper bound, not a prediction.** Removing an impossible pair does not
   make the remaining choice correct. The flight measures what actually happens.

## Consequence for the registered flight

The arm that flies is **M0's prompt plus the missing pairing**, not "M0's prompt plus a
label inventory it never had". The added block is a pure 1,836-character suffix
(sha256 `46ee018e1bd2392c0e3654ddeacf4b7f32209da2a0c00cd7e658afe50ca0dda3`) on the
sealed instruction; the 263 example fillers M0 already carried stay exactly where they
were, so the contrast is not confounded by also deleting them.

## Files

| file | sha256 |
|---|---|
| `headroom.py` | see `MANIFEST.sha256` |
| `headroom-report.json` | see `MANIFEST.sha256` |

Reproduce:

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:$PWD/src
D=docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-headroom
python -B $D/headroom.py --out $D/headroom-report.json
```
