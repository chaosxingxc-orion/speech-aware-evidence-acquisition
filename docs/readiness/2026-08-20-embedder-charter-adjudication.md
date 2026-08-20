# Owner adjudication — embedding models enter under the retriever clause, encode-only enforced

Date: 2026-08-20. Authority: owner decision ("好，认可", same day), on the selection ticket's
charter question (`2026-08-20-omni-embedding-selection.md`).

## The ruling

1. Dedicated embedding models — including models DERIVED from generative thinkers that
   retain generation capacity (e.g., LCO-Embedding-Omni) — enter this study under the
   charter's **frozen tool-level retriever clause** (pinned + per-contact logged), NOT as a
   second answering LLM.
2. Binding condition: the integration must **structurally forbid generation** — the wrapper
   exposes `encode()`-style calls only, enforced by a machine check (fail-closed test that
   no generation-capable endpoint/params are reachable through the integration surface),
   never by convention. Final answer authority stays with the frozen core, always.
3. The owner also approved the **P-EMB-3M multi-model routing comparison** design (one
   registration comparing the local dedicated embedders {LCO-3B primary, GLAP, CLSP,
   omni-embed-nemotron control — arms confirmed by the E-1 identity check} on the P-EMB-1
   surface, plus a CASCADE arm: core T0 self-transcription → local text embedder
   (qwen3-embedding class) → text-text label matching). Registration follows the E-1
   feasibility/identity report and the P-EMB-3L read.
