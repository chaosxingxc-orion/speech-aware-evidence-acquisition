# Cross-modal retrieval / knowledge-plane survey (2026-08-23)

Provenance: coordinator-directed web survey (2026-08-23), commissioned under the owner's
knowledge-plane baseline directive; 29 items across three lanes, filtered for transferability
to a frozen-core, train-build / dev-tune / test-report pipeline. Items are architecture and
discipline evidence only — none is local effectiveness evidence. Mapping lines are written
against the study's Q(speech) → K(multi-dim) → V(prior-bearing payload) frame.

## Lane 1 — text

1. **kNN-LM** (Khandelwal et al., ICLR 2020). Frozen LM interpolated with a kNN distribution
   over a train-built (context-vector → next-token) datastore. Mapping: the canonical
   K=representation / V=un-embedded-label separation; K is the model's OWN representation.
2. **Why do NN LMs work?** (Xu et al., ICML 2023). Gains come from ensembling a DIFFERENT input
   representation, not memorization. Mapping: keep both the speech-native and cascade key views;
   representational diversity is the mechanism.
3. **Long-tail crisis in NN LMs** (2025, arXiv 2503.22426). kNN gains concentrate on a minority
   of tokens; retrieval actively hurts elsewhere. Mapping: selective/gated use of retrieved V;
   report per-class and per-bucket deltas on dev, never aggregate only.
4. **Efficient kNN-LM** (He et al., EMNLP 2021). Datastore pruning + adaptive retrieval (skip
   the lookup when the model is confident). Mapping: prune redundant keys at build; dev-tune a
   confidence gate for when to consult the knowledge plane at all.
5. **MassiveDS** (Shao et al., NeurIPS 2024). Trillion-token datastore scaling; size is a
   reported axis; explicit decontamination vs eval sets. Mapping: the template for the KB
   scaling curve and decontamination discipline.
6. **RETRO** (Borgeaud et al., ICML 2022). Retrieval over 2T tokens; quantifies train/test
   leakage via n-gram overlap and stratifies results by overlap. Mapping: report accuracy
   stratified by train↔eval near-duplicate overlap.
7. **In-Context RALM** (Ram et al., TACL 2023). Retrieved documents prepended to a fully frozen
   LM; LM-signal reranking adds materially. Mapping: closest architectural twin to the
   API-shaped boundary; what-to-prepend and how-often-to-retrieve are DEV knobs.
8. **REPLUG** (Shi et al., NAACL 2024). Frozen black-box LM; ensemble over independently
   prepended documents; the LM's likelihood supervises the retriever. Mapping: the frozen core
   can SCORE candidate keys — a gold-free reward signal for reranking.
9. **kNN-Prompt** (Shi et al., EMNLP 2022). kNN retrieval for zero-shot classification with
   fuzzy verbalizers. Mapping: verbalizer expansion is a cheap train-built V repairing
   label-surface mismatch; links kNN retrieval to closed-set decode.
10. **Demonstration selection**: KATE (Liu et al., 2022), EPR (Rubin et al., NAACL 2022), UDR
    (Li et al., ACL 2023), Diverse Demonstrations (Levy et al., ACL 2023), diversity-in-ICL
    (2025). Mapping: top-1 cosine is the weakest exemplar policy; select by similarity ∧
    label-coverage ∧ diversity, tuned on dev.
11. **Extreme multi-label ICL**: IReRa (D'Oosterlinck et al., 2024); LongICLBench (Li et al.,
    2024). With many classes, do not enumerate the label set in the prompt: infer free text →
    retrieve into the label space → rerank; accuracy collapses as label count grows. Mapping:
    the architecture for >100-label surfaces (Audio2Tool).
12. **Retrieve-then-rerank**: ColBERTv2 (NAACL 2022), RankGPT (Sun et al., EMNLP 2023),
    listwise rerankers (2025). Mapping: cheap multi-dim recall, then one reranker fusing
    dimensions; the frozen core itself can be the listwise reranker.
13. **Batch Calibration** (Zhou et al., ICLR 2024). Estimate and subtract the model's
    contextual/label prior; inference-only. Mapping: a principled home for prior-bearing V —
    train-estimated class priors + dev-estimated bias correction.

## Lane 2 — vision-multimodal

14. **MuRAG** (EMNLP 2022) / **RA-CM3** (ICML 2023) / **REVEAL** (CVPR 2023) / **RA-CLIP**
    (CVPR 2023). Multimodal memories; retrieval quality, not generator size, is the binding
    constraint. Mapping: K may be cross-modal pairs while V is consumed as text.
15. **Tip-Adapter** (Zhang et al., ECCV 2022). Training-free key-value cache from few-shot
    train features (K=image features, V=one-hot labels), α-blended with frozen CLIP zero-shot
    logits. Mapping: the closest analogue — fuse retrieved-label evidence with direct
    closed-set decode via a dev-tuned α-blend.
16. **RA-TTA** (ICLR 2025); **Test-Time Retrieval-Augmented Adaptation** (ICCV 2025). Per-sample
    test-time retrieval refinement of a frozen VLM, no training; the cross-modal bridge is
    TEXT descriptions. Mapping: validates training-free per-sample refinement; the field routes
    the cross-modal query through the text side.
17. **Modality gap**: Mind the Gap (Liang et al., NeurIPS 2022); I0T standardization (2024);
    mean-shift calibration for mixed-modality search (2025); Mitigate the Gap (2024/25).
    Mapping: weak audio↔text cosine is the expected cone-gap signature, not proof of missing
    information; per-modality mean-centering and score standardization are zero-cost first
    moves before declaring audio keys unusable.
18. **RICES** (Yang et al., 2022; Flamingo lineage). Image query → labeled-exemplar retrieval
    for VLM ICL. Mapping: the recipe is solved; the transfer question is only whether the
    speech query embedding is a good enough key.

## Lane 3 — speech/audio

19. **Contextual biasing**: trie-based deep biasing + shallow fusion (Le et al., 2021); TCPGen
    (Sun et al., Interspeech 2021→2023); prompt biasing (2025); zero-shot trie decoding (2025).
    Mapping: the speech field's native un-embedded V — symbolic, prefix-structured, scales to
    thousands of entities; a candidate V form for label/entity supply.
20. **kNN-CTC** (Zhou et al., ICASSP 2024); gated monolingual datastores (2024). Frame-level
    audio→text key-value pairs via CTC pseudo-labels; skip-blank pruning; gated routing among
    datastores. Mapping: the granularity answer — frame/token-level keys, not utterance
    pooling; multi-datastore routing at inference.
21. **Speaker-Smoothed kNN** (2024, arXiv 2406.04791). An x-vector dynamically sets the kNN
    interpolation weight per utterance. Mapping: the speaker dimension as a TRUST CONTROLLER
    of injection strength (λ), not merely a retrieval filter — a speech-native contribution
    with no text/vision analog.
22. **LA-RAG** (2024/ICASSP 2025). Token-level speech datastore, speech→speech retrieval,
    retrieved items consumed as in-context examples. Mapping: in-modality retrieval avoids the
    cross-modal gap entirely; the speech→retrieve→ICL loop works over an API boundary.
23. **SpeechRAG** (ICASSP 2025). Speech adapter into a frozen retriever, no ASR; beats
    high-WER cascades, loses to low-WER cascades. Mapping: end-to-end audio retrieval wins
    only when the transcript is bad; with a strong self-transcript the cascade remains the
    right key for text-side dimensions.
24. **WavRAG** (ACL 2025); **RASU** (Interspeech 2024). Unified audio+text knowledge; RASU
    retrieves transcripts + intent labels as prompts for SLU. Mapping: RASU is the Q-K-V frame
    already instantiated for SLU — the study's contribution must be multi-dimensional K, the
    dev-tuned use policy, and speech-native injection control, not the pipeline.
25. **KA2G** (Sun et al., CSL 2024). Audio-grounded generative slot filling conditioned on an
    external value list. Mapping: keep the audio path alive as a second evidence stream while
    knowledge V constrains the output space — the cascade-error mitigation pattern.
26. **VoiceBench** (Chen et al., TACL 2025). ASR→LLM pipelines beat all open E2E speech models
    by >20 points on spoken instructions; transcription acts as implicit denoising. Mapping:
    citable justification for the measured 0.89 text vs 0.13–0.28 audio asymmetry.
27. **Speech-text modality gap inside speech LLMs** (2025, arXiv 2510.12116). Speech-conditioned
    hidden states drift from text counterparts even in unified models. Mapping: the gap lives
    inside the omni model; normalize or transit through text — no external encoder swap fixes Q.
28. **Audio-text embedding granularity**: CLAP (ICASSP 2023); GLAP (2025); MGA-CLAP (2024);
    T-CLAP (2024). Global pooling destroys localization; fine-grained variants repair it; GLAP
    achieves strong speech-content retrieval. Mapping: names the register problem
    (utterance-level audio keys vs word-level text keys) the study measured independently.
29. **Audio Flamingo / AF3** (ICML 2024; 2025). Audio exemplars in prompts + RAG without
    finetuning (contrary evidence exists on audio-LLM ICL). Mapping: worth testing whether the
    frozen core consumes audio V at all, or only text V.

## Synthesis — what the speech modality changes for a Q-K-V knowledge plane

(a) **Query granularity/register**: text and vision queries are register-matched to their keys;
a pooled utterance embedding is not. MGA-CLAP, T-CLAP, and kNN-CTC independently converge on
frame/token-level keys. The speech Q should be decomposable (segments or agent intermediates)
with K at matching granularity.
(b) **Modality gap**: vision still has a cone gap after 15 years of contrastive alignment; the
speech field routes around it — in-modality retrieval (LA-RAG) or transit through the model's
own text (VoiceBench, SpeechRAG). Apply per-modality mean-centering before accepting any audio
cosine as a ceiling.
(c) **Speaker/paralinguistic keys have no text analog**: used as filters, routers, or —
highest-value — trust controllers of injection strength (Speaker-Smoothed λ).
(d) **Cascade error propagation**: mitigate without training — parallel audio-grounded
evidence (KA2G), output-space constraint via V, n-best/fuzzy retrieval, confidence-gated
lookup; transcription is also an implicit denoiser.
(e) **Construction vs tuning hygiene**: datastore size as a reported axis with decontamination
(MassiveDS); overlap-stratified results (RETRO); K/V from train only, {k, α, gate, rerank
depth} dev-tuned (Tip-Adapter/kNN-LM); retrieval policy is a dev knob (In-Context RALM); test
touched once.

## Top-5 actionable, ranked

1. Tip-Adapter-style α-blend of retrieved-label evidence with direct closed-set decode
   (α, k dev-tuned).
2. Speaker-smoothed injection strength λ — speech-native novelty candidate.
3. Multi-dim recall → frozen-core listwise rerank (IReRa/RankGPT shape, zero training).
4. Per-modality mean-centering re-analysis of the landed P-EMB-4R vectors; GLAP-style
   speech-content encoder as alternative Q.
5. MassiveDS hygiene: KB scaling curve with decontamination and dev-only knob tuning.
