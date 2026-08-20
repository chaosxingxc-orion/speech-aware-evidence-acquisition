# P-EMB-3L — LOCAL omni embedding construction sweep — REGISTERED

Date: 2026-08-20. Status: **REGISTERED — flyable once the machinery delta lands** (owner
order: try the LOCAL omni model first, before the external-embedder survey concludes).
Profile: `bounded-discovery-probe`. Parent: P-EMB-1 (EMB-WEAK, `6ebcaba`) refuted ONE
construction — whole-sequence mean pooling, no instruction — on the local core. This probe
sweeps the remaining training-free constructions the pinned llama.cpp already supports,
before any external model is adopted.

## 1. Question

Does ANY training-free embedding construction on the LOCAL frozen omni core form a usable
audio↔text semantic space — or is the local representation exhausted?

## 2. Constructions (3 arms; the P-EMB-1 surface reused verbatim: the frozen 60 SLURP
devel audio + the 18 canonical scenario labels; argmax cosine; scoring-side gold)

| Arm | Pooling | Instruction prefix (BOTH sides, common-mode) | Contacts |
|---|---|---|---|
| L1 last-bare | `--pooling last` | none | 78 |
| L2 last-instruct | `--pooling last` | "Represent this utterance for intent retrieval: " (audio side) / "Represent this intent label for retrieval: " (text side) — GritLM-style, exact strings frozen in the binding config with sha256 | 78 |
| L3 mean-instruct | `--pooling mean` | same prefixes | 78 |

234 embedding contacts, zero generation. (Mean-bare is CITED from the consumed P-EMB-1 —
0.0500, below chance.) Server recipe per E-0/P-EMB: pinned q4km + mmproj, `--embedding`,
own port, LLAMA_MEDIA_MARKER pinned, one server session per pooling mode (two sessions).

## 3. Verdicts (per the arc's calibration discipline; chance = 1/18 = 0.0556)

- **LOCAL-SPACE-EXISTS**: any arm's accuracy ≥ 0.30 — a usable space exists training-free;
  the winning construction advances (next steps: the audio-span-only pooling patch E-0
  described, then the A2T tool surface) and the external-embedder adoption is deferred.
- **LOCAL-EXHAUSTED**: every arm ≤ 0.15 — the local core's training-free constructions are
  exhausted; the external dedicated-embedder path (selection survey in flight) becomes the
  routing-tier's representation instrument.
- Otherwise **INCONCLUSIVE-EMB3L** (report per-arm accuracies, attractor structure, and
  the prefix common-mode effect L3-vs-cited-mean-bare).

## 4. Cost (registered ceilings)

234 contacts; ≤260 calls; ≤600 metered audio-seconds; ≤0.3 GPU-h. Wave-2 (interruptible
filler by its own registration) yields via its stop-file for the ~10-minute window.

## 5. Discipline

One-shot read; pinned suite extension (`analysis/pemb_read.py` gains the three-arm sweep
evaluator; the cosine matcher and manifest discipline reused verbatim) built and
coordinator-reviewed BEFORE the read; exposure row `SAEA-PROBE-pemb3l-234` at registration
(consumed=no); vectors on the data root, hashed manifests only in Git; gold scoring-side
only; SLURP CC BY-NC 4.0 carried.

## 6. Pre-read instrument amendment (2026-08-20, appended AFTER the flight landed and
## BEFORE any result read; precedent: pkey §7, ptrap §6)

Structural facts from the fly archive (`2026-08-20-pemb3l-flight/`, byte-identity checks
only — no vector values compared, no accuracy computed):

1. **On this build, `--pooling` changes only TEXT-side vectors.** Keyed on contact id,
   L2-vs-L3 share all 60/60 audio vectors byte-for-byte while sharing 0/18 text vectors;
   L1-vs-L2 and L1-vs-L3 share nothing (the prefix axis works on both sides). The server
   line `embeddings required but some input tokens were not marked as outputs -> overriding`
   fires exactly once per AUDIO contact and never for text (the consumed P-EMB-1 logged the
   same rate), consistent with the build overriding audio-side pooling.
2. **Interpretation scope, fixed before reading:** (a) the registered L2-vs-L3 contrast
   identifies TEXT-side pooling sensitivity only; (b) §3's L3-vs-cited-mean-bare
   common-mode comparison inherits the same text-side-only scope; (c) by the same
   mechanism, L1's audio side is predicted byte-identical to the consumed P-EMB-1 audio
   side (both bare; they differ only in pooling flag) — the read SHALL report this
   structural check; if confirmed, the "mean vs last" audio contrast does not exist on
   this build at all, and audio-side construction variation here spans ONLY the
   instruction-prefix axis (L1 vs L2).
3. **Verdict criteria in §3 are UNCHANGED** (absolute per-arm accuracy thresholds,
   computable regardless). A LOCAL-EXHAUSTED verdict, if reached, is scoped to "the
   constructions this build can actually express": audio ∈ {effective-pool bare,
   effective-pool instructed} × text ∈ {last, mean} × {bare, instructed}.
4. Launcher-side repair during the flight (machinery `rails/probes/pemb3l_flight.py` flew
   unmodified): zombie-state PID liveness misread caused a fail-closed inter-session abort;
   repaired with waitpid reaping + arm-level idempotence; proof in the archive
   (`abort-repair-proof.log`). 234/234 contacts durably spent across the two attempts on
   one plan (one config hash, one protocol hash); no contact re-flown.
