# Audio2Tool tier-1 official population, v1 — verdict

Two runs flown 2026-09-04 on study commit `e61b424a`, both `baseline-reproduction`, one cell each.

| Run id | Cell | Attempt | Rows | Manifest SHA-256 |
|---|---|---|---:|---|
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` | `T1-official-pop-500` | `attempt-20260904T172609Z-t1officialpop500` | 500 | `17acd0f4c1de9b5f4c658390fb67e8a6065f1628ff09b19bcd77afa47e7f99cf` |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1` | `W-official-raw-yaml` | `attempt-20260904T173219Z-wofficialrawyaml` | 400 | `051ae145a7f994f5ab3d0ba4686ec0292df4d267436350da4448804075575d92` |

Preregistration: `docs/readiness/2026-09-04-a2t-tier1-official-population-v1-preregistration.md`.
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier1-official-population-v1/result-summary.json`
(SHA-256 `4aa4941195866a4c568369d164ef33ff6ea0ec8d8434fd1157099f47baf67837`).
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: FAIL on both cells. But Tier 1 is no longer an unexplained gap — it is a smart_home gap, and it has a named cause.

Both preregistered decisions come out FAIL under the owner's 3-point alignment band. Neither
suspect the replication verdict left standing explains the Tier-1 shortfall:

- **The roster is worth +5.6 pp, not +32.** Drawing the release's own tier-1 population moves tier-1
  tool accuracy from 60.0 (n = 50, frozen 400) to **65.60** (n = 500), against a published 92.4.
- **The whitespace variant is worth nothing.** Paired over the same 400 rows: **+1.00 pp, sign test
  p = 0.5034, CI90 [−0.75, +3.00] pp**. The suspect is dead.

What the 500-row roster buys instead is resolution, and at n = 500 the tier splits by **domain** in
a way n = 50 could never have shown:

| domain | n | tool accuracy | CI90 | paper (all domains) |
|---|---:|---:|---|---:|
| `wearables` | 91 | **93.41** | [87.75, 96.55] | 92.4 |
| `smart_car` | 41 | **92.68** | [83.04, 97.04] | 92.4 |
| `smart_home` | 368 | **55.71** | [51.42, 59.91] | 92.4 |
| **natural mixture** | 500 | **65.60** | [62.03, 69.00] | 92.4 |
| **equal-domain** | 500 | **80.60** | — | 92.4 |

`wearables` and `smart_car` sit **on** the published number. `smart_home` — 73.6 % of the tier-1
population — sits 36.7 pp below it and drags the whole tier down. There is no general "Tier-1
problem" on this runtime.

## 1. `T1-official-pop-500` — the roster cell

Official scorer, n = 500, one contact per row, 100 % parse rate, zero rows naming more than one
call.

| metric | ours | CI90 | paper | delta |
|---|---:|---|---:|---:|
| tool accuracy | **65.60** | [62.03, 69.00] | 92.4 | **−26.80** |
| exact match | 10.20 | [8.18, 12.64] | 92.4 | −82.20 |
| parameter F1 (macro) | 14.40 | — | — | — |
| parameter F1 (micro) | 1.20 | — | — | — |

**Decision: FAIL.** ALIGNED needed ≥ 89.4; 92.4 is far outside the CI90, so
CONSISTENT-WITHIN-NOISE does not apply either. **The extension contingency does not fire**: the
remaining 1,646 tier-1 queries are not flown, and `flight-roster-receipt-remainder.json` stays
unused.

### The roster effect, measured

The frozen 400's own 50 tier-1 rows score 60.00 [48.4, 70.6] under the same scorer on the same
protocol. The official population scores 65.60 [62.03, 69.00]. **Roster effect +5.6 pp**, and the
two intervals overlap heavily — this is not a paired contrast (different populations, only 12
shared queries), so it is two independent estimates of the same tier, not a difference test. The
honest reading is that the roster mattered a little and n = 50 was simply too small to say anything
about tier 1 at all: its CI90 spanned 22 points.

### Exact match is the sharper anomaly, and it is not a scoring artefact

The paper reports **92.4 for both** tool accuracy and exact match on tier 1 — identical figures on
one tier and nowhere else — which means its Qwen3-Omni run attached **no** unsolicited argument to
any tier-1 call while choosing the right tool 92.4 % of the time. Here exact match is 10.20 %
against a tool accuracy of 65.60 %: of the 328 rows that pick the right tool, 277 then attach
arguments the argument-free tier-1 gold does not have. Under the extended `a2t-toolcall-v2`, which
forgives a predicted key whose value equals the registry default, exact match rises to 14.60 % —
+4.4 pp, still 78 pp short. Default-argument credit is not the explanation.

### Where the smart_home misses go — diagnostic, not a metric

Of 163 smart_home misses, **161 name another real tool of the 152-row registry**. Only 2 invent a
name. 79 stay inside `smart_home`; 82 pick the same idea's twin in `smart_car`.

| rows | gold | predicted |
|---:|---|---|
| 12 | `rebootDevice` (smart_home/maintenance) | `restartDevice` (smart_home/automation) |
| 8 | `setSecurityMode` (smart_home/core_control) | `armSecuritySystem` (smart_home/security) |
| 7 | `activateScene` (smart_home/automation) | `activateRoutine` (smart_home/automation) |
| 6 | `setColor` (smart_home/lighting) | `setAmbientLighting` (smart_car/media_cabin) |
| 6 | `setColorTemperature` (smart_home/lighting) | `setAmbientLighting` (smart_car/media_cabin) |
| 5 | `setLighting` (smart_home/core_control) | `setAmbientLighting` (smart_car/media_cabin) |
| 5 | `getAirQuality` (smart_home/climate) | `getAirQuality_diag` (smart_home/diagnostics) |
| 5 | `setGroupLightState` (smart_home/lighting) | `setLighting` (smart_home/core_control) |

The registry holds 86 `smart_car` tools, 53 `smart_home` tools and 13 `wearables` tools. The failure
mode is **near-synonym selection inside a registry that contains near-synonyms**, and the domain
ranking follows the number of confusable neighbours exactly: `wearables` (13 tools, 6 misses in 91),
`smart_car` (86 tools but only 35 distinct gold names drawn, 3 misses in 41), `smart_home` (50
distinct gold names competing with 53 same-domain and 86 cross-domain entries, 163 misses in 368).
This is a component, not a mood: the question it raises is bounded and answerable.

## 2. `W-official-raw-yaml` — the whitespace cell

Official scorer, n = 400, 100 % parse rate, 45 rows naming more than one call.

| tier | ours | CI90 | paper | delta | within 3 pp | paper in CI90 |
|---|---:|---|---:|---:|:--:|:--:|
| tier1_direct | 58.0 | [46.4, 68.8] | 92.4 | **−34.4** | no | no |
| tier2_parametric | 74.0 | [62.8, 82.8] | 84.6 | −10.6 | no | no |
| tier3_multi_intent | 74.0 | [62.8, 82.8] | 74.7 | −0.7 | yes | yes |
| tier4_implicit | 34.0 | [24.1, 45.6] | 33.4 | +0.6 | yes | yes |
| tier5_needle | 76.0 | [64.9, 84.4] | 90.6 | −14.6 | no | no |
| tier6_correction | 82.0 | [71.5, 89.2] | 81.5 | +0.5 | yes | yes |
| tier7_multiturn | 60.0 | [48.4, 70.6] | 54.6 | +5.4 | yes | yes |
| tier8_intent_blending | 38.0 | [27.6, 49.6] | 41.7 | −3.7 | no | yes |
| **overall** | **62.00** | — | — | — | — | — |

Decision tiers are 1, 2, 5, 6; only tier 6 is aligned and the paper value is outside the CI90 on
three of the four. **Decision: FAIL.** Summed absolute per-tier gap 70.5 pp, against 77.3 pp for
`R-official-raw`.

### The paired contrast, which is what this cell is for

Same 400 rows, same official scorer, same official gold, same serving geometry; only the
system-prompt whitespace differs. Tier-stratified paired bootstrap, 10,000 replicates, seed
20260903.

| metric | in-code default | YAML block scalar | delta | saves / harms / ties | sign test p | CI90 |
|---|---:|---:|---:|---|---:|---|
| tool accuracy | 0.6100 | 0.6200 | **+0.0100** | 12 / 8 / 380 | 0.5034 | [−0.0075, +0.0300] |
| exact match | 0.2025 | 0.2175 | +0.0150 | 9 / 3 / 388 | 0.1460 | [+0.0025, +0.0300] |
| parameter F1 | 0.3165 | 0.3247 | +0.0082 | 14 / 10 / 376 | 0.5413 | [−0.0047, +0.0217] |
| parse rate | 0.9975 | 1.0000 | +0.0025 | 1 / 0 / 399 | 1.0000 | [+0.0000, +0.0075] |

**380 of 400 rows are ties.** The prompt-fit receipt had already shown that both spellings render to
exactly the same 3,581 text tokens, so there was no context-length channel for an effect to travel
down, and none appears. The exact-match CI90 excludes zero while its sign test does not, on 12
discordant rows — that is a coin-flip's worth of evidence and is reported, not claimed.

**The whitespace ambiguity is closed.** A config-driven official run and an adapter-default run
produce the same numbers to within noise, so which spelling the authors used cannot account for
anything.

## 3. Our scorer against the official one, on the same outputs

The owner asked for alignment under **both** scorers. `reproduction.toolcall_scoring.
parse_tool_calls_text` now reads the released call-string contract as well as the reconstructed
JSON-array one (`a2t-parse-v2-json-or-callstring`), so for the first time this repository's own
scorers can read its own official-protocol runs: **0 parse failures** on all 900 rows, against 400
on the replication flight.

`T1-official-pop-500` (tier 1 only, n = 500):

| metric | official | v2 | delta | rule behind the gap |
|---|---:|---:|---:|---|
| tool accuracy | 65.60 | 65.60 | **+0.00** | — (they agree exactly) |
| exact match | 10.20 | 14.60 | +4.40 | default-argument credit (V2b) |
| parameter / slot F1 | 14.40 macro, 1.20 micro | 0.00 slot F1 | — | different definitions; tier-1 gold is argument-free, so v2's (tool, key, value) triple space is empty |

`W-official-raw-yaml` (all eight tiers, n = 400):

| tier | official TA | v2 TA | delta | official EM | v2 EM | delta | rule behind a >3 pp gap |
|---|---:|---:|---:|---:|---:|---:|---|
| tier1_direct | 58.0 | 58.0 | +0.0 | 12.0 | 16.0 | +4.0 | default-argument credit |
| tier2_parametric | 74.0 | 74.0 | +0.0 | 24.0 | 24.0 | +0.0 | — |
| tier3_multi_intent | 74.0 | 24.0 | **−50.0** | 30.0 | 2.0 | **−28.0** | first-call-only vs ordered sequence |
| tier4_implicit | 34.0 | 34.0 | +0.0 | 20.0 | 20.0 | +0.0 | — |
| tier5_needle | 76.0 | 76.0 | +0.0 | 18.0 | 16.0 | −2.0 | — |
| tier6_correction | 82.0 | 80.0 | −2.0 | 34.0 | 34.0 | +0.0 | — |
| tier7_multiturn | 60.0 | 60.0 | +0.0 | 20.0 | 20.0 | +0.0 | — |
| tier8_intent_blending | 38.0 | 12.0 | **−26.0** | 16.0 | 0.0 | **−16.0** | first-call-only vs ordered sequence |
| **overall** | **62.00** | **52.25** | −9.75 | 21.75 | 16.50 | −5.25 | — |

**The two scorers agree exactly on tool accuracy on every single-call tier.** They diverge only on
tiers 3 and 8, and the rule is named and structural: the official HF adapter never populates
`all_tool_calls`, so the official scorer reads only the **first** parsed call against the **primary**
gold tool, while `a2t-toolcall-v2` compares the whole ordered predicted sequence with the whole
expected sequence. On exact match the second named rule is default-argument credit (v2 drops a
predicted key absent from gold when its value equals the registry default; the official scorer
counts it as a parameter error), worth +4.0 to +4.4 pp on tier 1 and nothing elsewhere. Parameter F1
is not differenced at all: the official figure is a macro average of per-sample key P/R/F1 and v2's
slot F1 is micro over `(tool, key, value)` triples, so the two answer different questions and are
reported side by side.

For the owner's alignment question the answer is therefore: **on this carrier our current scorer and
the official scorer are identical on the metric the paper reports (tool accuracy) wherever gold asks
for one call, and differ by a known, named rule wherever gold asks for several.**

## 4. Deviations still in force

1. **Quantization.** Q4_K_M against the release's bf16. Untouched here; it is the last of the three
   ranked suspects still standing and has its own preregistered probe.
2. **Tier-1 population reconstruction.** The rule is derived from `tier1_dataset.py` and verified on
   all 2,146 query directories (2,145 agreements, 0 disagreements, one documented exception,
   `query_01982`). If the authors evaluated their **internal** corpus — 25 speakers per query
   rather than the two the public release ships — "first successful speaker" resolves to a different
   wav for most queries. That is unknowable from the release and is the largest residual uncertainty
   about this cell.
3. **The 654.6325 s row.** `tier1_direct:003943` was kept for fidelity, and it was served: it
   encoded through the bf16 mmproj and returned a well-formed call string. It is one row in 500.
4. **Sample rate.** Every Audio2Tool wav is 24 kHz mono 16-bit, not the 16 kHz the README claims.
   Both rosters are the same material, so nothing in this comparison turns on it.
5. **Serving geometry.** `-np 2` for T1 (forced by the 654 s row) and `-np 3` for W (identical to
   `R-official-raw`); neither changes a request byte.
6. **Chat template, seed, temperature.** Unchanged from the replication and all inert or recorded.

## 5. Throughput

| quantity | T1-official-pop-500 | W-official-raw-yaml |
|---|---:|---:|
| contacts | 500 of 540 registered (508 planned) | 400 of 410 registered (408 planned) |
| speech audio | 1,668.914042 of 1,750 s | 2,159.688 of 2,250 s |
| serving geometry | `-c 49152 -np 2`, 24,576/slot | `-c 49152 -np 3`, 16,384/slot |
| model load | 10.2 s | 10.0 s |
| generation wall | 282 s | 211 s |
| end-to-end wall (preflight to server stop) | 330 s | 250 s |
| summed per-call latency | 229.79 s | 300.12 s |
| mean per-call latency | 0.460 s | 0.750 s |
| prompt tokens per call | 3,633 | 3,660 |
| completion tokens per call | 14.2 | 15.8 |
| GPU `enforced.power.limit` before / after | 100.00 W / 100.00 W | 100.00 W / 100.00 W |

The per-call latency inverts against the wall clock because the two cells serve different slot
counts: T1's requests are individually faster (shorter audio on 499 of 500 rows) but only two run
at a time, while W's are slower each and three run at a time.

One attempt each, FINALIZED, zero aborted, zero orphans, no recovery re-registration used on either
run.

## 6. What this authorizes

Nothing new. The population is discovery data, no knob was tuned on it, and this is not a
superiority, generality or Stage-3 claim. Mechanism work stays stopped.

What it changes is the shape of the open question, which is now much narrower than it was this
morning:

- **Two of the three suspects are closed.** The roster is worth +5.6 pp and the whitespace variant
  is worth nothing. Quantization is the only one of the three still open.
- **Tier 1 is a `smart_home` phenomenon.** `wearables` (93.41) and `smart_car` (92.68) reproduce the
  published 92.4 on this runtime, at this quantization, under this protocol. Whatever the gap is, it
  is not a general inability to do direct tool calling.
- **The named component is near-synonym selection in a registry that contains near-synonyms.** 161
  of 163 smart_home misses name a real registry tool; half of them the same idea's twin in
  `smart_car`. A candidate tool set narrower than all 152 — which the replication verdict already
  floated — would act exactly here, and so would anything that disambiguates `rebootDevice` from
  `restartDevice`.
- **Exact match remains the sharper anomaly** and is not a scoring artefact: 10.20 % against a
  published 92.4 %, and only +4.4 pp of that is default-argument credit.

Whether to spend the next flight on quantization (the registered probe), on a narrowed candidate
set, or on asking the authors which corpus and which tool set produced Table 3, is an owner
decision.
