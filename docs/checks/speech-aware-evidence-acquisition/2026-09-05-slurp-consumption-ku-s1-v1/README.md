# SLURP consumption cells KU-S1c and KU-S1 — receipts (2026-09-05)

Preregistration: `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md`.
Verdict: `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md`.
Cell KU-S1c of the 2026-09-05 three-dimension experiment program section 4b: the equal-contact,
no-knowledge control of the consumption dimension. Cell KU-S1 was **refused before registration**
and never flew; `containment-analysis.json` is that refusal's evidence.

| file | what it is | contacts spent |
|---|---|---|
| `containment-analysis.json` | the model-free ruling on KU-S1: whether either KU-S1c control turn, all 1,000 phase-2 control turns, and a `KbFacetProvider` top-5 supply packet survive `rails.runner._assert_agent_control_excludes_knowledge_payloads` under each candidate snapshot. Produced by `scripts/slurp_ku_s1_containment_analysis.py` | none, of any kind |
| `prompt-fit.json` | `saea-phase-prompt-fit-v1`: both phases of both KU-S1c cells, all 2,000 distinct envelopes, measured on the resident server through `/apply-template` + `/tokenize`. **Pinned** by `configs/baseline/slurp-phase-draft-revise-v1.json` and re-rendered at every preflight. Produced by `scripts/slurp_ku_s1c_prompt_fit.py` | 0 generated tokens; 1 `/props`, 2,000 `/apply-template`, 4,000 `/tokenize` |
| `wire-check-ku-s1c.json` | the whole request path against a fake gate and a fake transport | 0 model contacts, 0 sockets |
| `smoke-receipt-ku-s1c.json` | the four-row end-to-end smoke, `SAEA-SLURP-KU-S1C-SMOKE-4-V1`. **Its eight responses are a wiring proof and are not a result** | 8 contacts, 30.022 audio s |
| `flight-receipt-ku-s1c.json` | the flight, `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1`, one attempt, no recovery | 2,000 contacts, 5,769.5874 audio s |
| `read.json` | the single registered read: gold opens here, once, after the seal. Produced by `scripts/slurp_ku_s1c_read.py` | none; 0 model, GPU, tool, embedding, network |
| `result-summary.json` | the verdict's machine-readable summary, assembled from the receipts beside it by `build_result_summary.py` | none |
| `build_result_summary.py` | that assembler, reading only this directory | none |
| `MANIFEST.sha256` | sha256 of every file above | none |

## The three arms `read.json` scores

`CLOSED-LIST` is the sealed comparator's own outputs (identity anchor: it must reproduce its
verdict's numbers exactly, and does). `KU-S1C` is this flight's sealed outputs — the **revise**
phase's response, which is the one that stands. `KU-S1C-DRAFT` is the **draft** phase's own sealed
responses, read from the flight's `.phases.json` and scored through the same registered scorer over
the same complete 1,000 rows. The draft arm costs no extra contact and adds no exposure; it exists
because KU-S1c differs from the comparator in two ways at once — an added CONTROL turn and an added
CONTACT — and only the draft row separates them.

## Reproducing

```bash
# the KU-S1 ruling, from frozen bytes
python scripts/slurp_ku_s1_containment_analysis.py <out.json>

# the prompt fit (spawns the server; zero generated tokens)
python scripts/slurp_ku_s1c_prompt_fit.py <out.json>

# the read (scoring-side; gold opens once)
python scripts/slurp_ku_s1c_read.py \
  --outputs <run>/<run_id>.outputs.jsonl \
  --run-manifest <run>/<run_id>.run-manifest.json \
  --phases <run>/<run_id>.phases.json \
  --flight-receipt flight-receipt-ku-s1c.json \
  --out read.json

# the summary, from this directory
python build_result_summary.py --out result-summary.json
```

Per-row outputs, traces and phase summaries live under `SPEECHRL_DATA_DIR/runs/`, never in Git.
