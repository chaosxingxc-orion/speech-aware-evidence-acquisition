# The OBS-E1b stitch decision, and its proof on sealed bytes

Exposure row `SAEA-E21-MF-OBS-E1B-SEAM-V1` (`model-free-check`), registered before the first sealed
artifact was opened. **Zero frozen-core, GPU, server, socket, tokenizer, tool, embedder, network,
audio-decode and paid-API contacts — and zero forced-alignment contacts**, which is half the reason
the protocol below was the one chosen. Runner: `scripts/e21_obs_e1b_stitch_proof.py`. Receipt:
`stitch-proof.json`.

**Nothing here flies, admits, tunes or amends anything.** OBS-E1 stays REJECTED under its own
preregistered rule. This file decides how a successor's text would be stitched and measures whether
that stitch can be trusted; it is a precondition for a preregistration, not a permission.

---

## 0. The question, and why it had to be answered before a GPU

OBS-E1b delivers each plan-v3 unit as `[left context | the turn | right context]` audio and stitches
**the turn's own transcription only**. The core transcribes what it hears, so the response covers the
context too. Something has to decide where the turn's text begins and ends, and Earnings-21 ships no
word timestamps: all **362,747** `ts`/`endTs` cells on the 44 discovery calls are empty (checked by
the PERSON harm decomposition, its §0).

The harm decomposition said this in as many words: *"A cell for (a) needs its own model-free wire
check on the discard rule before it needs a GPU."* This is that check.

## 1. Does the repository already do this? Yes — twice, and neither is free

**A delivered slice whose text is not stitched is not a new idea here.**

| existing mechanism | what it does | why OBS-E1b cannot just use it |
|---|---|---|
| `reproduction.replay_loop`'s REPLAY window | cuts `replay_context_s` seconds either side of a flagged span, transcribes the WHOLE window, then keeps only the words inside the flagged interval — the context's text is discarded. The closest precedent there is, and it works end to end. | the discard is done by `core.span_surgery.align_words` (**MMS_FA forced alignment**) against the window's own wav. That is a **tool-model contact**, one per span. OBS-E1b would need 5,122 of them — a second model in the loop, its own exposure surface, its own failure modes, and a cost the harm decomposition never priced. |
| `reproduction.repair_loop`'s window hook + `obs_delivered_text` | the general seam by which a policy declares that what it CONTRIBUTED differs from what the core SAID; `analysis.e21_window_pairing.stitched_windows_from_trace` prefers that field whenever a trace carries it, and `assert_stitch_reproduces_outputs` still binds the result. | this is the delivery **channel**, not the **decision**. OBS-E1b reuses it verbatim; it still has to decide what to put in it. |
| `rails.observe.SliceReCutter` (W2, wave 6) | folds a context margin into the cut bounds and chains the widened slice through `SliceRegistry` — `cut_span(..., pad_s=0.0)`, exactly as `replay_loop._cut_replay_window` does. | this is the **audio** half, and OBS-E1b's plan v3 uses the same arithmetic. It says nothing about text. |

So the channel exists, the audio arithmetic exists, and the only precedent for the decision costs a
tool-model contact per unit. **The decision is what this row buys.**

## 2. The decision: the delimiter-free overlap protocol, not the boundary marker

The design offered two protocols. They were not weighed on elegance; they were weighed on **which of
them can be proved without a contact**.

| | **(i) overlap alignment — CHOSEN** | (ii) boundary marker — rejected |
|---|---|---|
| what is delivered | context + turn + context, **instruction byte-identical to OBS-E1's** | 200 ms of digital silence between context and turn, **plus a new instruction line** ("transcribe only the speech between the two pauses") |
| how the turn's text is found | the neighbours transcribe the overlap too; align the two and cut at one word both agree on | the core is asked to obey a partial-transcription instruction |
| factors against OBS-E1 | one: the delivered audio | **two**: the delivered audio **and** the instruction |
| can it be proved model-free? | **yes** — §3 to §6 below, on bytes that already exist | **no.** Its correctness is entirely a claim about instruction compliance, and this repository has **no measurement** of that on this core for a partial-transcription task. Proving it requires the contact it is supposed to justify. |
| tool contacts | **zero** | zero |

Protocol (i) is `reproduction.obs_ownership`, versioned `saea-obs-context-ownership-v1`. Protocol (ii)
stays named as the fallback and is not implemented: a two-factor cell cannot answer the one-factor
question OBS-E1b exists to ask, and an unmeasurable rule cannot be preregistered.

### The safety argument, in one paragraph

Around each boundary both units received the same seconds. Find a run of consecutive words the two
responses **agree** on there, and cut both texts at one position inside it. Inside a shared run the
two texts are the same words in the same order, so `left[:anchor] + right[anchor:]` covers that audio
**once and only once** — for *every* position in the run. Where the anchor sits therefore changes
which decode supplies a word, never whether a word is supplied. Contiguity is the whole argument: a
longest-common-*subsequence* match would happily pair a "the" at one end of the overlap with a "the"
at the other and drop everything between, which is exactly the failure this rule refuses.

Four rules, each recorded per boundary: `no-overlap` (the 90 s cap left a long unit no context — the
v1/v2 behaviour, byte for byte), `anchor` (a shared run of ≥ 3 words, taking the run whose implied cut
lands **nearest the boundary**, with length only as a tie-break), `anchor-short` (≥ 2 words, only when
no longer run exists, counted separately), and `proportional` (no shared run — the one rule that can
drop or duplicate a word, and therefore the one that is gated).

## 3. P1 — the identity, which has no tolerance at all

With no context, the stitcher must reproduce the sealed OBS-E1 hypothesis exactly.

| | |
|---|---:|
| calls reproduced **byte for byte** | **44 / 44** |
| units delivering their own response unchanged | **5,122 / 5,122** |
| corpus character retention | **1.00000000** |
| cut displacement, max | **0 words** |
| boundary rules | `no-overlap` 5,078, `call-edge` 44 |

This is also the seam's own falsifier: a v1 or v2 plan carries no context bounds, so every boundary
takes the `no-overlap` branch and the policy's behaviour is unchanged, which `tests/unit/` asserts
independently of this receipt.

## 4. P2 — the round trip, at plan v3's margin and a ladder around it

Each unit is handed what OBS-E1b would have delivered, **built from the sealed texts themselves**: a
per-call word timeline (each unit's own sealed words spread uniformly over its own turn — the same
local-rate attribution the harm decomposition used), from which each unit receives the neighbours'
words that fall in its delivered span, with **its own sealed text spliced in verbatim** in the middle.
A correct decision returns that text byte for byte.

| margin | boundary rules (anchor / anchor-short / proportional / no-overlap) | calls byte-exact | **corpus character retention** | words rebuilt / sealed | displacement median / mean\|·\| / p95 |
|---:|---|---:|---:|---:|---|
| 0.0 s | 0 / 0 / 0 / 5,078 | **44 / 44** | **1.0000000** | 368,011 / 368,011 | 0 / 0.00 / 0 |
| 1.0 s | 4,994 / 49 / 28 / 7 | 30 / 44 | 0.9992394 | 367,724 / 368,011 | 0 / 0.82 / 3 |
| 2.0 s | 5,048 / 15 / 8 / 7 | 39 / 44 | 0.9995904 | 367,854 / 368,011 | 0 / 1.08 / 3 |
| 3.0 s | 5,059 / 8 / 4 / 7 | 41 / 44 | 0.9998077 | 367,940 / 368,011 | 0 / 1.36 / 4 |
| **5.0 s (plan v3)** | **5,065 / 5 / 1 / 7** | **42 / 44** | **0.9998196** | **367,944 / 368,011** | **0 / 1.87 / 5** |
| 8.0 s | 5,068 / 2 / 1 / 7 | 42 / 44 | 0.9996377 | 367,873 / 368,011 | 0 / 2.55 / 7 |
| 10.0 s | 5,069 / 1 / 1 / 7 | 42 / 44 | 0.9998148 | 367,943 / 368,011 | 0 / 2.96 / 8 |

**At plan v3's own margin the stitch keeps 367,944 of 368,011 corpus words — it loses 67, 0.018 %.**
Forty-two of the 44 calls come back byte for byte; the two that do not are named in the receipt
(`4361631`, −103 characters of 52,045; `4387383`, −244 of 22,779) and were traced to eight boundaries
on the sparsest stretches of those two calls, where the delivered text runs under one word per second
and a ten-second overlap holds three words in total.

**Read the two columns in the right order.** Byte-for-byte call identity is the strict property;
corpus retention is what a WER actually reads. A cut displaced by a word moves that word from one
unit to its neighbour and changes no corpus metric at all — which is why displacement is reported
(median **0**, mean **1.87** words, p95 **5** at the operating margin) rather than gated. **Per-unit
exactness is deliberately not a headline**: this simulation splices decodes with wildly different
local word rates, which is harder on the rate estimator than one decode of one span would be, so the
per-unit figure here is a floor and not an estimate.

## 5. P3 — how much do two decodes of the same audio actually agree?

P2 assumes the two neighbours transcribe their shared seconds the same way. The family carries a
measurement of exactly that: `SAEA-E21-FULL44-TAIL2S-V1` and the sealed comparator decoded **the same
1,593 fixed 90-second cuts of the same 44 calls**, differing only by one 2.0-second silence tail on
the delivered bytes.

| | |
|---|---:|
| word-level agreement, corpus | **98.289 %** |
| per-window agreement, median | 98.940 % |
| per-window agreement, p05 | 94.301 % |
| windows identical after normalization | **124 / 1,593 (7.8 %)** |
| word agreement in the **first and last 13 words** of a window | **88.443 %** |

Two facts matter. First, greedy decoding on this server is **not** bitwise reproducible across batch
compositions, and only 7.8 % of windows come back identical — so an overlap protocol that required
identical text would be unusable, and this one does not. Second, agreement is **much worse at the
edges** (88.4 % against 98.3 %), and an OBS-E1b overlap lives entirely at the edges of both its units.
That is the number the residual risk should be priced against, not the corpus average.

## 6. P4 — the adversarial round trip, and the honest ceiling on the risk

P2 again, with the context words taken from the **comparator's own decode** — a genuinely independent
transcription of the same audio — instead of from the cell's. This is conservative by construction:
the comparator heard those seconds inside a 90-second window, not inside a neighbouring unit, so it
disagrees more than an OBS-E1b context would, by the margin §5 measures.

| | |
|---|---:|
| calls byte-exact | 0 / 44 |
| **corpus character retention** | **0.9711** |
| corpus word agreement against the sealed hypothesis | 0.9663 |
| words rebuilt / sealed | 356,938 / 368,011 (**−11,073, −3.0 %**) |
| boundary rules | anchor 4,913 · anchor-short 36 · proportional **122** · no-overlap 7 |
| clamped boundaries | 25 |

**Under the worst pairing this repository can construct, the stitch loses 3.0 % of the corpus's
words.** That is not a small number — it would be worth about three points of deletion-driven WER —
and it is the reason the preregistration gates the flight on the *realized* rule mix rather than
assuming the P2 figure. The gap between 0.018 % (P2) and 3.0 % (P4) is the gap between two decodes
that agree the way neighbouring units would and two that agree the way a 90-second window and a
27-second unit do; §5 says the truth sits much nearer the first, and the flight's own `proportional`
and `clamped` counts will say where exactly.

## 7. What this receipt cannot conclude

* **Nothing about whether context helps.** The harm decomposition's "≤ 93.4 % addressable" is a
  ceiling on what a mechanism could reach, never a prediction; no arm has been flown with plan v3.
* **Nothing about the model's behaviour.** Every text here was produced by a sealed run under a
  different transport. The simulation says what the STITCH would do with a given set of responses;
  it cannot say what responses the core would actually give when handed context.
* **No claim that the stitch is lossless in general.** It is lossless at every anchored boundary by
  construction, and the measurements above bound what the non-anchored ones cost on this corpus.
* **Nothing paper-facing.** n = 44 calls, discovery data, and this is not an effectiveness read at
  all.
