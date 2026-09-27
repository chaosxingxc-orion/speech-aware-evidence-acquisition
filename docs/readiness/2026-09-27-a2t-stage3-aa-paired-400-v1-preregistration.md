# Cell A2T-AA: preregistration

Registered 2026-09-27 at study commit `eb5e463b`, before any contact, from the
sealed direct baseline's own fragments by script (decision 58). Development numbers only (owner
decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | When the sealed Audio2Tool direct baseline flies twice, request for request, on the same 400 rows in one chain on one resident session, how far do its numbers move? |
| treatment | `a2t-native-role-direct-union4000-v1` unchanged: the direct-only phase program of the shared controller, official-protocol compact registry, promoted speech packets, c98304 np3 max2048 |
| changed | the roster (400 of the same 4,000 ids), the run / attempt / live-fit identities, the ceilings rescaled to 400 rows. Between pass A and pass B only the `live_phase_fit` identities and the `what_this_is` prose differ, and neither enters a request. |
| comparator | none flown; the sealed direct rows of the same 400 ids (`SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1`) are reported beside, never a gate |
| in-chain replicate | pass B is pass A's replicate and pass A is pass B's; both fly in one chain on one session |
| runs | `SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1` / `SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-FIT-V1`; `SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1` / `SAEA-A2T-STAGE3-AA-PAIRED-400-A-FIT-V1`; `SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1` / `SAEA-A2T-STAGE3-AA-PAIRED-400-B-FIT-V1` |
| rows | 4 (smoke), 400, 400 |
| composed config hash | smoke `9adcadaa534c75e9d0f13a5a12fbd7bd979423dec7edbb33f258204fdeb8e63a`; pass A `cfd6783ce1ebd696329bede91fdc2bc91cabe119c283756f2464b443fc435f95`; pass B `bad06cd4ef11a7f41dfdbaed0910f317c2c108937dfa66d745000e4c83a158d0` |
| protocol hash | smoke `d5769316f8634c9e76333a8e483dc2bda9afe6633f726726a917867716a552a7`; pass A `fabed23cfe5b85be32ce6a30b302cf8f0306eb1e6277d3b507cf6011ff9b32d5`; pass B `b538d2aa3b81a5e12312dbe69c43c2c9381aea237b63ffcccd06dbca5f58ddd7` |
| split identity | `965f145f581753874353216a25109a4746627095027cefbab0ed91c88090990a` (smoke `c7057020334be227c430d661953fa3ad3b0b044dfbc97c4e186c5777cb6a5baa`) |
| roster | `docs/receipts/rosters/a2t-paired-400-v1.json` (sha256 `b57275736ff18c048e4d48414348443ce23afae0df1490821bafcae75e499c3d`), seed 20260921, owner decisions 67 and 71 |
| comparator rows | `docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json` (sha256 `f43a83876d3fb6748c17ee1f3fed7adf05a69ec3ddd32eb627ccb1e6c27f40ef`) |
| session | `serving-a2t-native-role-base-np3-max2048-v3` -- the Audio2Tool np3 x 32,768 session, NOT the resident SLURP np4 x 24,576 session |
| authority | docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md rows 67, 68, 71, 76a, 139; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md rules 3 and 6; docs/results/stage2-results-ledger.md row A2T-NULL; owner decisions 28, 86, 101, 140 |

## The read rule (fixed here)

There is no verdict and no admission. Request identity is proven first: `request_sha256` equal on 400 of
400 rows, or the pair is not read as request-identical and the count is the finding. Then, per row, byte
identity of the delivered tool call (`response_text_sha256` equal; the count identical of 400). Then the
paired difference, pass B minus pass A, on the official tool accuracy (`a2t-toolcall-official`; the repo
scorer `a2t-toolcall` beside it, official exact match beside it) with a tier-stratified paired bootstrap
CI95 (10,000 draws, seed 20260903), in the natural-mixture and the equal-tier weighting. **The
CI95 half-width is h_A2T**, the margin every later Audio2Tool interval on this roster is read at (owner
decision 68). Reported beside: the per-tier and per-domain tables with the paper column beside the repo
column; each pass against the sealed direct rows of the same ids; contacts per minute and tokens per
contact (decision 140).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The cell measures the paired-400 roster's OWN NULL and claims nothing: pass A and its request-identical replicate SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1 fly in the same chain on the same resident session, and the CI95 half-width of their paired difference on the official tool accuracy becomes h_A2T, the margin every later Audio2Tool interval is read at (owner decision 68). expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect; claims_benefit is false because an instrument admits nothing.",
      "primary_metric": "official Audio2Tool tool accuracy (scorer a2t-toolcall-official, the pinned release's own metrics.py; the repository scorer a2t-toolcall reported beside it), pooled over the 400 rows in the natural-mixture weighting, with the equal-tier weighting beside it",
      "replicate_run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1",
      "rows": 400
    },
    "SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The cell measures the paired-400 roster's OWN NULL and claims nothing: pass B and its request-identical replicate SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1 fly in the same chain on the same resident session, and the CI95 half-width of their paired difference on the official tool accuracy becomes h_A2T, the margin every later Audio2Tool interval is read at (owner decision 68). expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect; claims_benefit is false because an instrument admits nothing.",
      "primary_metric": "official Audio2Tool tool accuracy (scorer a2t-toolcall-official, the pinned release's own metrics.py; the repository scorer a2t-toolcall reported beside it), pooled over the 400 rows in the natural-mixture weighting, with the equal-tier weighting beside it",
      "replicate_run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1",
      "rows": 400
    },
    "SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The four-row smoke of cell A2T-AA proves the request form, the packet plane, the live phase fit and the seal on the Audio2Tool session before the two 400-row passes. Under instrument rule 5 four rows are a form proof by size; it claims nothing and no number from it is a task measurement.",
      "primary_metric": "none: a four-row form smoke reads no metric",
      "rows": 4
    }
  }
}
```

Both passes declare `cross-flight-with-in-chain-replicate` with `claims_benefit` false and
`expected_effect_pp` 0.0: a request-identical pair is registered to look for no effect and to deliver a
floor. The floor gate's arithmetic at n = 400 (`stage3_effect_floor_check.py --explain`): sampling
half-width 1.474 x sqrt(625 / 400) = 1.8425 pp, rule-3 admission bar 3 x sqrt(625 / 400) = 3.75 pp,
floor 3.75 pp; an expected effect of 0 is below it and that is the point, because this cell claims no
benefit and no finding is raised for a cell that claims nothing. The smoke is `form-proof` by size.

## Geometry and packets

The last flown Audio2Tool cells (SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 and its dual-store sibling, 2026-09-15) served q4km-mmproj-free-a2t-native-role-np3-max2048-v1: -c 98304 -np 3 (three 32,768-token slots), max_tokens 2048, --no-mmproj, LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, port 8080, session serving-a2t-native-role-base-np3-max2048-v2. The resident SLURP session serving-slurp-native-candidate-five-train-a-np4-v1 serves q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1: -c 98304 -np 4 (four 24,576-token slots), max_tokens 512, LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/slurp-q4km-packets-04ccc72a. FlightRuntime.serve attaches only to a session whose recorded identity (model fragment and its sha256, argv flag by flag, env) matches the cell's fragment, and the runtime refuses a speech_feature_root that disagrees with the promotion receipt's feature_root; the two sessions therefore differ in identity twice over (slot count and packet root) and NO Audio2Tool cell can attach to the resident SLURP session. Consequence: Audio2Tool cells do not interleave with SLURP cells inside one session. They fly only after the SLURP session is stopped and SAEA-Serving-A2T is resident (one geometry swap in, one back), which is why decision 69 pays the swap only when at least two Audio2Tool cells are ready -- this chain is three flights on one session.

Every one of the 400 rows already holds a promoted SpeechFeaturePacketV1 under /home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, pinned by the sealed 2026-09-12 promotion receipt prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json (sha256 720d81f63a1923f19893c0ee171e1ab7b47f9a946c1e62a06bdddd839243de8a) that the committed direct baseline pins; the roster builder proved 400 of 400 packet ids present. No CPU packet preparation is registered because none is owed: zero encoder contacts.

## Budgets and failure rule

Per pass: 400 generation contacts (run-cumulative; 400 x the direct-only
program's 1-contact maximum), 1201 live-fit endpoints (1 + 3 x 400, the count
the fit gate requires to the unit), 2761 speech seconds,
0.5 GPU hours, one official complete score. Smoke:
4 contacts, 13 fit endpoints,
21 speech seconds, 0.2 GPU hours, no
score. Expected spend: about 152 s of generation wall per pass at the sealed direct's
own realised rate; the whole chain about 0.15 GPU hours against a 1.2 GPU-hour ceiling. Stop and preserve
on the first failure; a smoke failure closes the chain before pass A, a pass-A failure before pass B. AT
MOST ONE root-diagnosed recovery re-registration per run id (fresh generation AND fit identities); a second
failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No benefit, superiority, generalisation or admission claim from this cell, ever. No mechanism, no
knowledge supply, no tool authority, no prompt or geometry change between the passes. No flight on the
resident SLURP session. No test-split contact, no confirmatory split, no paper-scale profile. No re-flying
of the sealed comparator. No flight before root mints the decision receipt and the three cells are flipped
at one commit, and `--allow-output-change` is never passed.
