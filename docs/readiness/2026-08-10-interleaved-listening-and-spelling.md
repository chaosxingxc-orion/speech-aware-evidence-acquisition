# Interleaved listening and spelling as a training-free agent policy (2026-08-10)

Owner's proposal, in his own framing: not a switch to streaming ASR, but a
**different agent policy** — carry a text history, read a small audio step,
decode conditioned on history + step, append the result to the history, repeat.
The carried state is text, and in an agent system that history is a **mutable
object that can be compacted**, not a passively accumulating buffer.

## Where it sits in this study's frame

| construct | in this policy |
|---|---|
| OBS | how much audio per step, and how much context around it |
| ORG | how the history is organised and compacted |
| SUPPLY | which part of that history is fed back into the next decode |
| USE | the decode itself |

This makes it a **P3 item in the study's own sense**: there are trained methods
with this shape, and the research contribution is building the training-free
analogue on a frozen core.

- **RNN-T** is literally this, trained: the prediction network is a language
  model over previously emitted tokens, the encoder is causal or chunked, and
  the joint network emits frame-synchronously.
- **Chunk-based streaming encoders** (Emformer and relatives) carry a left
  memory bank plus a small right lookahead.
- **Qwen2.5-Omni's Thinker–Talker with TMRoPE**, and **VITA-Audio's interleaved
  cross-modal token generation**, do the interleaving inside the model.

The decisive difference for us: all of those carry **encoder state**. An
API-only frozen core cannot. We can carry only **text**, and lean on prompt
caching to avoid re-prefilling it.

## What it removes by construction — this is the strong argument

Two of the three deletion mechanisms this study has measured exist only because
the current design produces independent chunks and then reconciles them:

- **The stitch.** 10,693 excess-removed words, 86 % of all deletions, r = 0.847
  per sample. It exists because overlapping chunks must be deduplicated. In a
  continue-the-text policy there is no merge step at all.
- **The model-declared boundary.** 1,648 s advanced past untranscribed, and the
  mechanism the chaptering literature indicts directly
  (`2026-08-10-segmentation-who-decides-the-cut.md`). A fixed small step needs
  no timestamp from the model.

Removing both by construction, rather than by tuning, is a stronger claim than
anything the current substrate ablations can offer.

## What it costs — and the cost is dominated by one ratio

Two measurements from today set the frontier.

**1. Decode slows superlinearly with context.** Same config, same request shape:

| prompt context | decode per slot |
|---|---|
| 816 tokens | **13.07 tok/s** |
| ~4,700 tokens | **3.07–4.40 tok/s** |

5.8× the context, 3.8× slower decode. So an **unbounded** text history is
self-defeating: the policy would get slower the longer it listened. Compaction
is not an optimisation here, it is what makes the policy have a bounded cost at
all — the owner's point, and the measurement backs it.

**2. The audio cost multiplier is `window ÷ step`.** Audio is a hard linear cost
at 12.87 prompt tokens per second and must be re-encoded every call; only the
text prefix is cacheable. If a step commits `S` seconds but shows the model `W`
seconds (left context + commit + lookahead), the corpus's audio is re-encoded
`W/S` times:

| policy | window ÷ step | calls over the 30,408 s split | audio prompt tokens |
|---|---|---|---|
| current (60 s window, ~50 s advance) | 1.2× | 608 | 470 k |
| 30 s step, 40 s window | 1.33× | 1,014 | 521 k |
| 10 s step, 20 s window | 2× | 3,041 | 783 k |
| 5 s step, 15 s window | 3× | 6,082 | 1.17 M |
| **1 s step, 8 s window** | **8×** | **30,408** | **3.13 M** |

Fine stepping is not expensive because of the text history — that is cacheable
and compactable. It is expensive because **every second of context around the
commit window is re-encoded on every step**. That ratio, not the step size, is
the knob.

## The compaction design space — this is the actual research content

The history is not one thing, and its parts compress at very different rates:

1. **Verbatim tail** — the last few hundred characters, for seam continuity and
   coreference. Small, high fidelity, rolling. (Already implemented:
   `obs_condition_tail_chars: 400`.)
2. **Entity / terminology glossary** — speaker names, tickers, product names,
   recurring figures. This *is* contextual biasing, it is append-mostly, and it
   never needs to be verbatim. Directly connects this policy to the W-B track.
3. **Discourse state** — who is speaking now, what section of the call
   (prepared remarks vs Q&A), which analyst asked what. Low update rate.

Compaction triggers are themselves a control decision: token threshold, topic
change, or a quality signal. Choosing what to keep under a budget is exactly
the study's reward-guided-control thesis applied to its own substrate.

## The caveat that must not be lost

Streaming architectures trade right-context for latency, and typically pay
5–15 % relative WER for it. **This study has no latency requirement** — it is
offline batch transcription. Adopting streaming naively means paying that cost
and collecting none of the benefit.

So the policy must keep right context: show the model `[left context | commit
window | right lookahead]` and commit only the middle — Emformer's structure at
the prompt level. That is precisely what makes `W/S > 1`, and why the table
above is the real design frontier rather than a nuisance.

## What to measure before building any of it

1. **Per-call wall-clock floor** (HTTP, slot scheduling, mtmd invocation, cache
   restore) as a function of audio duration — under way. It sets the smallest
   affordable step regardless of token accounting.
2. **The audio window at which this frozen core's verbatim accuracy peaks** —
   this is A-2a, and under this framing its purpose sharpens from "tune a
   buffer" to "find the commit-window size the policy should use".
3. **Whether a compacted history beats a verbatim tail at equal token budget** —
   the ORG/SUPPLY question, and the one with no published answer for a frozen
   core.
