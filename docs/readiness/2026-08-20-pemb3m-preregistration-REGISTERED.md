# P-EMB-3M — dedicated-embedder multi-model routing comparison — REGISTERED

Date: 2026-08-20. Status: **REGISTERED — flyable once the machinery lands.** Profile:
`bounded-discovery-probe`. Authority chain: owner approval of the design
(`2026-08-20-embedder-charter-adjudication.md` §3, "好，认可" recorded 2026-08-20) +
P-EMB-3L verdict **LOCAL-EXHAUSTED** (`2026-08-20-pemb3l-verdict.md`), which triggers the
registered branch "the external dedicated-embedder path becomes the routing-tier's
representation instrument". Identity/feasibility basis:
`2026-08-20-e1-local-embedder-identity.md`. Charter basis: dedicated embedders enter under
the frozen tool-level retriever clause, pinned + per-contact logged, with **structural
encode-only enforcement** (machine check, fail-closed) — final answer authority stays with
the frozen core.

## 1. Question

Does a DEDICATED semantically-aligned embedding model form a usable audio↔text routing
space on the P-EMB-1 surface where the chat core's free embeddings are refuted 3/3 — and
does a text-only cascade (core self-transcript → text embedder) reach the same tier
without any audio embedding at all?

## 2. Arms (the frozen P-EMB-1 surface reused verbatim: 60 SLURP devel audio, split
identity `fc9de436…5ee5`, + the 18 canonical scenario labels; argmax cosine;
scoring-side gold)

| Arm | Model (all pinned, local) | Sides | Contacts |
|---|---|---|---|
| M1 PRIMARY | `lco-embedding-omni-3b-gguf` on the pinned llama.cpp (E-1 Mission-B recipe: `--embedding --pooling last`, mmproj, `LLAMA_MEDIA_MARKER` pinned, `-ngl 999`) | 60 audio + 18 text | 78 |
| M2 CONTROL (audio-TYPE space) | `glap` via transformers in the shared venv (no new installs) | 60 audio + 18 text | 78 |
| M3 CONTROL (speaking-STYLE space) | `clsp` via transformers in the shared venv (no new installs) | 60 audio + 18 text | 78 |
| M4 CASCADE | consumed pkey2-338 T0 self-transcripts (cited artifacts; hashes pinned in the binding config) → `qwen3-embedding-0.6b-gguf` text-text (umbrella `0d4865b`; `--pooling last`) | 60 transcript + 18 text | 78 |

The controls are adversarial by design: GLAP embeds audio-event TYPE and CLSP embeds
speaking STYLE — if either matches or beats a content-aligned model on content routing,
the "content semantics" claim is confounded and that is a named finding (§4).
`omni-embed-nemotron-3b` is NOT in this registration (NC license + separate transformers
branch); it is a pre-authorized ESCALATION requiring its own registration.

## 3. Pre-flight gates (binding, fail-closed, inside this registration's ceilings)

1. **POOLING-DIFFER gate (mandated by the pemb3l verdict):** before any scored M1 contact,
   embed one identical audio file under `--pooling last` and `--pooling mean` (two server
   boots). If the two vectors DIFFER → gate passes clean. If BYTE-IDENTICAL → record
   `POOLING-OVERRIDE-PRESENT` and proceed; §4 then substitutes the scoped verdict names.
2. **Control import feasibility:** GLAP/CLSP must import and produce one sanity embedding
   with the shared venv AS-IS. Any missing dependency → that arm is DROPPED-DEPS
   (disclosed, never pip-installed). A dropped control never blocks M1/M4.
3. **Cascade source check:** the frozen 60's T0 self-transcripts must exist among the
   consumed `SAEA-PROBE-pkey2-338` artifacts with verifiable hashes. If absent/partial,
   the pre-registered supplement `CASCADE-T0` flies first: ≤66 generation contacts on the
   frozen core (T0 transcription construction reused verbatim from the consumed P-KEY
   machinery), logged before any cascade embedding.
4. **Encode-only machine check (charter):** the embedding integration surface must pass
   the structural fail-closed test that no generation-capable endpoint or sampling
   parameter is reachable through it (adjudication §2). The flight refuses to take off on
   a red check.

## 4. Verdicts (chance = 1/18 = 0.0556; CITED comparators: closed-set decode routing
0.7833 A1'r / 0.8167 FS-NONE; chat-core embeddings 0.0500, refuted 3/3)

- **M1 EMB-ROUTES**: LCO accuracy ≥ 0.65 — a dedicated embedder is a viable routing tier
  at a fraction of decode cost; construction advances toward the A2T tool surface.
- **M1 EMB-WEAK** (or **EMB-WEAK-SCOPED** if `POOLING-OVERRIDE-PRESENT`): ≤ 0.30 — the
  dedicated-embedder hypothesis fails on this stack (scoped to the llama.cpp construction
  if the override fired; model-level refutation only with a clean pooling gate).
- **M4 CASCADE-ROUTES / CASCADE-WEAK**: same 0.65/0.30 bands — decides whether the
  routing tier even needs audio embeddings or the ~89%-text-side pattern (P-KEY) extends
  to representation matching.
- **CONTROL-ANOMALY** (named finding, any verdict): max(M2, M3) ≥ max(M1, M4) AND ≥ 0.30.
- Otherwise **INCONCLUSIVE-3M**: per-arm accuracies, confusion/attractor tables,
  cross-arm agreement structure, and cosine-sign profiles (the chat core's 400/400
  negative-cosine signature is the reference pathology).

## 5. Cost (registered ceilings)

312 planned embedding contacts + ≤66 CASCADE-T0 contingency + ≤10 gate contacts.
Ceilings: **≤440 calls; ≤900 metered audio-seconds; ≤0.5 GPU-h.** Embedding contacts are
tool contacts (pinned tools, per-contact logged); CASCADE-T0 contacts (if any) are
frozen-core contacts. GPU is ready-first shared; no generation flight coexists with an
embedding server on the same GPU.

## 6. Discipline

One-shot read; pinned suite extension (`analysis/pemb3m_read.py`: per-arm cosine matcher,
verdict evaluators, confusion + cross-arm agreement tables) built and coordinator-reviewed
BEFORE the read; exposure row `SAEA-PROBE-pemb3m-388` at registration (consumed=no);
vectors on the data root, hashed manifests only in Git; gold scoring-side only; SLURP
CC BY-NC 4.0 carried; qwen3-emb CUDA non-bit-exact jitter (cosine ≥ 0.9999 on repeat,
E-1 Mission C) declared as read-suite tolerance — argmax verdicts unaffected at that
magnitude; a repeat-call determinism sample per server session is recorded in the flight
receipt.
