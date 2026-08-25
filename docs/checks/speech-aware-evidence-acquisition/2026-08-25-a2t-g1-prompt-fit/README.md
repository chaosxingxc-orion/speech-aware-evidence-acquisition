# A2T stage G1 — the session-bound prompt-fit gate: **FAIL. STAGE G1 STOPS.**

Date: 2026-08-25. Row `SAEA-SN-MF-A2T-G1-PROMPT-FIT-NP8` (`docs/exposure-ledger.md`),
registered at commit `11d2ec2d` BEFORE any contact; generator `scripts/a2t_g1_prompt_fit.py`
committed at `545cfc27` before that. Receipt `prompt-fit.json`, sha256
`fd1edfa1d7fc6aa852775d368865237a24d3033f7c56f92e6ab7752d24ea69c6`.

Authority: `docs/readiness/2026-08-25-a2t-generality-campaign-plan.md` §3.6 (the G1 gate is
"prompt-fit passes"), the G0 PASS `docs/readiness/2026-08-25-a2t-g0-report.md`, and the locked
cell `docs/readiness/2026-08-25-baseline-lock-verdict.md` §4, whose np8 serving profile is
carried UNCHANGED.

> **Registered stopping rule, fixed in the ledger row BEFORE the measurement: if the worst
> envelope's margin against one slot is NEGATIVE, stage G1 STOPS OUTRIGHT — no campaign row,
> no preprocessing pass, no canary, no arm — and the registry is not shrunk to manufacture a
> fit.**
>
> **Measured: the margin is negative for BOTH arms, by a wide margin. VERDICT: FAIL. G1 STOPPED.**

## 1. The measurement

Both envelopes were rendered through the REAL `rails.runner._agent_messages` shapes via
`core.model.transport._ordered_speech_feature_content` / `_speech_history_texts`, with
`rails.adapters.audio2tool.Audio2ToolAdapter` supplying `build_task_contract` and
`assemble_prompt`. No prompt string is reimplemented, so the certified shape is the shape a
flight would send. Token counts are EXACT, from the resident service's own tokenizer.

| envelope | text tokens | + 2 special | verdict against an 8,192-token slot |
|---|---|---|---|
| `m0-direct-decode` | **13,236** | 13,238 | **over by 5,046 before any audio or output** |
| `blend-evidence-decode-worst` | **19,047** | 19,049 | **over by 10,857 before any audio or output** |

The frozen tool registry is 50,291 characters and is counted exactly ONCE
(`task_contract_counted_once: true` — for this carrier `build_task_contract` returns the
registry that `assemble_prompt` already embeds, so `_agent_messages` appends no second copy).

**The headline is the M0 arm, not the evidence arm.** M0 carries no evidence slot at all: it is
the bare prompt-matched direct decode with the registry in the system message — the exact form
that produced the published A0 comparator. It overruns a slot by 5,046 tokens *while being
credited with zero audio tokens and zero output reserve*. The BLEND overrun is a further
consequence, not the cause.

### 1.1 Margins, all three variants

| accounting | prompt tokens | completion reserve | margin vs 8,192 |
|---|---|---|---|
| worst envelope, zero speech, locked SLURP completion (64) | 19,049 | 64 | **−10,921** |
| worst envelope, zero speech, A2T completion (1,024) | 19,049 | 1,024 | **−11,881** |
| worst envelope, reference speech (514), A2T completion | 19,563 | 1,024 | **−12,395** |

**Required context per slot: 20,587. Available: 8,192. The requirement is 2.51× the budget.**

Two disclosures the numbers depend on, both carried at every citation:

- **Speech-feature tokens are counted as ZERO in the primary bound, deliberately.** Audio2Tool
  has no promoted speech-feature packet root — the prior A2T flights encoded audio live through
  the mtmd feature cache `/home/chao/feat-cache/audio2tool-q4km` (490 legacy `.feat` entries, 249
  MB, no packets) — so no packet can be measured without first flying a preprocessing pass. Zero
  is the strictly most generous assumption available; it can only help the prompt fit. **A
  negative margin computed at zero speech tokens is therefore a LOWER BOUND on the deficit and
  cannot be an artefact of the assumption.** The 514-token reference figure applies the landed
  np8 SLURP receipt's own measured rate (117 tokens / 8.126875 s and 78 / 5.312 s ≈ 14.4
  tokens·s⁻¹) to this carrier's longest item (`tier7_multiturn:001590`, 35.714 s); it is a
  reference and never the gate.
- **Two completion budgets are reported because the carriers genuinely differ.** The locked SLURP
  fragment caps completion at 64 tokens — sized for one short intent label, and unable to hold a
  JSON call list. The registered A0 baseline on THIS carrier used 1,024
  (`configs/model/q4km-featcache.json`). The gate is evaluated at 1,024; the 64-token margin is
  shown alongside so the difference is visible rather than buried. **This is a second
  carrier-forced deviation from the locked cell, independent of the context deficit**, and it
  would have to be registered explicitly by any future G1.

## 2. Why this happened — the serving geometry, measured rather than assumed

The resident service, verified live at preflight, runs:

```
llama-server ... -c 65536 -np 8 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --no-mmproj
```

llama-server divides `-c` across `--parallel` slots, so **65,536 / 8 = 8,192 tokens per slot**.
That is the locked cell's serving profile, and it was sized for SLURP, whose whole BLEND
evidence prompt was measured at **6,174 tokens against the same 8,192 slot, margin +1,954**
(`docs/checks/.../2026-08-24-dev100-c3-prompt-fit-np8/prompt-fit.json`).

**Audio2Tool's bare registry contract is larger than SLURP's entire evidence prompt — 13,236
against 6,174, a factor of 2.14.** The task contract is 50,291 characters against SLURP's 5,424,
a factor of 9.3.

This was foreseeable from the comparator and is confirmed here rather than discovered: the A0
flight's own committed launcher (`docs/checks/.../2026-08-18-pa2t-a0-flight/launcher/flight_identity.py`)
records that it dropped its model fragment's `-np 4` to **`-np 1`**, giving the whole 49,152-token
context to one sequence, *precisely because* `-np 4` would have yielded 12,288 tokens per slot —
"BELOW this flight's own ~12.6k-token registry prefill". **A0 could not fit its own prompt at
12,288 tokens per slot. The locked profile offers 8,192.**

Note that A0's own estimate (~12.6k, and the binding config's "~12693 estimated prompt tokens")
was an *under*-estimate: the exact tokenizer count is **13,236**, because the registry is dense
JSON whose punctuation tokenizes more finely than a chars/4 heuristic predicts.

## 3. What this is, and what it is not

**This is not evidence that the paradigm fails to transfer.** Nothing here touches retrieval
quality, fusion, dispatch, or decode. G0's reachability gate still stands at PASS (lexical
ceiling@5 = 0.7925 vs A0 tool accuracy 0.5425, +25.00 pp). What is established is narrower and
purely mechanical:

> **The locked cell's serving geometry — not the locked cell's knobs — is physically incompatible
> with the Audio2Tool contract size. The paradigm was never given the chance to run.**

It is also **not** a licence to shrink the registry. Summarizing, truncating, or retrieving over
the 152-row registry would change M0 away from the published A0 comparator (0.5425 tool accuracy
with the full registry in-prompt), and the resulting comparison would silently answer a different
question than the one the campaign plan §4.3 commits to.

## 4. The projection — what a registered single-variable change would cost

The deficit is in **tokens per slot**, and per-slot context is `-c` divided by `-np`. At the
unchanged total context of 65,536 the entire fix is one integer:

| `-np` | tokens per slot | M0 needs 14,776 | BLEND worst needs 20,587 |
|---|---|---|---|
| **8 (current, locked)** | 8,192 | **FAIL** (−6,584) | **FAIL** (−12,395) |
| 4 | 16,384 | PASS (+1,608) | **FAIL** (−4,203) |
| **3** | 21,845 | PASS (+7,069) | **PASS (+1,258)** |
| 2 | 32,768 | PASS (+17,992) | PASS (+12,181) |
| 1 (A0 used `-c 49152 -np 1`) | 65,536 | PASS | PASS |

(M0 and BLEND requirements include the 514-token reference speech allowance and the 1,024-token
A2T completion reserve.)

**`-np 3` is the minimum that clears the worst envelope; `-np 2` is the first setting with real
headroom** (+12,181), and it leaves total context — hence total KV cache and VRAM — unchanged,
so it needs no re-measurement of memory. The cost is throughput: 2 concurrent slots instead of
8, roughly a 4× reduction in achievable parallelism, which for a ~100-item G1 subset is minutes,
not hours.

**Three things that change must be registered together, and none of them is a policy knob:**

1. `-np 8 → 2` (or 3). This is a **serving-geometry** change, not a change to α, τ, k, fusion
   m/c/l, rank weighting, prior source, boundary stage, or percept admission — every one of
   which stays at the locked v1 cell.
2. `max_tokens 64 → 1024`, forced by the output shape (a JSON call list, not a label).
3. The A2T speech-feature packet root, which does not exist and must be materialized by a
   label-free preprocessing pass before any arm can fly on a `--no-mmproj` decoder.

Whether (1) and (2) forfeit the campaign plan §4.1 "transfers-unchanged" claim is a decision for
the owner, not for this row. The honest framing available: they are **carrier-forced serving
parameters, not tuned knobs** — the locked *policy* cell is untouched — but they are still
changes, and the plan's own §4.1 says any A2T-specific change is registered as such.

## 5. Spend

0 frozen-core contacts, **0 decoder evaluations, 0 generated tokens**, 0 tool contacts, 0 audio
seconds decoded, 0.0 GPU hours, 0 gold labels opened. Tokenizer surface exactly as registered:
1 `GET /props`, 2 `POST /apply-template`, 4 `POST /tokenize`. `model_contact: false`.

The resident service (`saea-np8-dev100-r6-base`, pid 2768, port 8080) was never started, stopped,
respawned, probed for state, or reconfigured; `/health` returned ok before and after and it is
left UP with its keepalive intact. Its chat-template hash `45777d2e…da2c8` is byte-identical to
the one the landed SLURP np8 prompt-fit receipt recorded, confirming the same instance and the
same template.

## 6. Artifacts

| artifact | sha256 |
|---|---|
| `prompt-fit.json` | `fd1edfa1d7fc6aa852775d368865237a24d3033f7c56f92e6ab7752d24ea69c6` |
| `scripts/a2t_g1_prompt_fit.py` | committed `545cfc27` |
| A2T task contract (the rendered registry) | `6823505253a741c4…` (50,291 chars) |
| `m0-direct-decode` messages | `7ffb41343267f6ca…` |
| `blend-evidence-decode-worst` messages | `6c48dd66abad4e30…` |
