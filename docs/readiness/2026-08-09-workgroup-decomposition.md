# Work-group decomposition of the ablation programme (owner directive, 2026-08-09)

Supersedes the linear A0–A5 ladder in
`2026-08-09-positioning-and-ablation-ladder.md` §3, which was too coarse and
falsely implied sequencing. The programme decomposes into **four parallel
work groups** matching the study's four constructs, plus a set of technical
exploration directions that cut across them.

Notation per item: **[axis]** · *precedent* (from the R0.1 mechanism map:
`bucket1` = shown-and-reachable, `bucket2` = shown-but-unreachable,
`bucket3` = never-tried-and-reachable) · carrier · what is measured.

---

## W-A · Agent-system construction （智能体系统搭建）

The substrate itself. Every other group's results are conditional on this, so
W-A owns the "same-substrate" guarantee: when a W-A item changes, the A0
baseline is re-run.

| id | knob / variant | axis | precedent | carrier | measured |
|---|---|---|---|---|---|
| A-1 | **Segmentation policy**: fixed window vs model-guided boundary vs VAD-driven vs hybrid (current = model+VAD hybrid) | OBS | Whisper 30 s fixed = bucket1; model-guided = bucket3 | e21/e22 | WER, boundary-tier distribution, slices/call |
| A-2 | **Buffer & advance geometry**: `obs_buffer_seconds` (30/60/90), advance clamp, overlap ratio | OBS | bucket1 (Whisper overlap) | e21 | WER vs cost (slices/call), truncation rate |
| A-3 | **Preprocessing chain**: VAD trim on/off, loudness norm on/off, denoise as *static* front-end | OBS | bucket2-adjacent (static denoise documented to hurt clean audio) | e21 | WER, trimmed-seconds, per-slice SNR |
| A-4 | **Pass structure**: single-pass vs self-cascade (transcribe → re-read own transcript to answer) vs multi-pass refine | OBS→USE | bucket1 (cascade-vs-direct: BBA 66→92, AIR-Bench 77.8→87.7) | bba, slurp, e21 | task metric per pass count, cost |
| A-5 | **State isolation & resumability**: per-call state, checkpoint/resume, batch determinism | — | engineering | all | determinism (byte-identical re-runs), failure recovery |
| A-6 | **Serving strategy**: GPU/CPU split of the projector, KV placement/precision, concurrency | — | engineering | all | s/slice, VRAM stability, WER-vs-f16 agreement |

*Status*: A-1/A-2/A-3 partially built (hybrid boundary + VAD trim + optional
loudness norm exist as config knobs, never ablated). A-4 designed, not built.
A-5 built (batch determinism proven). A-6 measured 2026-08-09.

---

## W-B · Knowledge construction （知识构建）

Building the evidence store, independent of any single query. This is where
the "multimodal knowledge base" belongs.

| id | variant | axis | precedent | carrier | measured |
|---|---|---|---|---|---|
| B-1 | **External static block**: the call's own ConEC context materials, injected whole (current R4 matched arm) | ORG | bucket1 (Siskos dose-response) | conec/e21 | WER, entity-class WER |
| B-2 | **External structured lists**: E-21 ships `bias_lists/oracle_list.txt` + `distractor_list.txt`; participant rosters from ConEC | ORG | bucket2 as used (decoder-level); prompt-level = bucket3 | e21 | WER, bias-phrase recall |
| B-3 | **Derived confusable sets**: deterministic phonetic keying (metaphone-class) over entity lists → "heard form → candidate" map | ORG | RECOVER/DeRAGEC class = bucket2 (trained); deterministic prompt-level = bucket3 | e21 | entity-class WER, correction precision |
| B-4 | **Self-generated glossary**: rolling entity/number/term list extracted from the agent's own accepted spans | ORG | bucket3 (no published inference-time precedent on any held carrier) | e21/e22 | WER, glossary growth curve, self-vs-external contrast |
| B-5 | **Cross-slice inconsistency detection**: same entity spelled differently across slices → confusable candidate without any external source | ORG | bucket3 | e21 | number of detections, downstream correction gain |
| B-6 | **Indexed / vectorized KB**: chunking granularity, index over text and/or audio, **local generative embedding model as a pinned tool** (owner-sanctioned) | ORG | bucket2 for trained speech retrievers (SpeechDPR/SpeechRAG); pinned-embedding prompt-level = bucket3 | spoken-squad, slue-sqa-5, e21 | retrieval top-k accuracy, downstream task metric |
| B-7 | **State compression**: deterministic extraction vs model-made rolling summary vs framework compressors | ORG | openJiuwen context_engine exists but is LLM-driven (deliberately unused in v1) | e21 | state size vs downstream metric |

*Status*: B-1 in flight (R4). B-2 data on disk, unused. B-3…B-7 designed only.

---

## W-C · Knowledge consumption （知识消费）

How constructed knowledge reaches the frozen core and changes its output.

| id | variant | axis | precedent | carrier | measured |
|---|---|---|---|---|---|
| C-1 | **Injection form**: whole block vs retrieved top-k vs structured slots (entity table) | SUPPLY | bucket1 (block); top-k/structured = bucket3 | e21, spoken-squad | task metric vs evidence tokens |
| C-2 | **Injection timing**: every slice / first slice only / on-demand when a trigger fires | SUPPLY | bucket3 | e21 | metric vs cost; prefix-cache hit rate |
| C-3 | **Dose & ordering**: evidence volume ladder (none → k=1 → k=5 → whole), ordering, truncation policy | SUPPLY | bucket1 (Siskos dose-response is exactly this) | e21 | monotonicity of metric in dose |
| C-4 | **Retrieval query construction**: from the audio directly, from the prior transcript tail, or hybrid | SUPPLY | bucket2 (trained speech retrievers); prompt-level = bucket3 | slue-sqa-5, spoken-squad | retrieval accuracy → task metric |
| C-5 | **Correction use**: in-context biasing (before) vs post-hoc entity correction (after) vs both | USE | bucket1-ish (RECOVER = after; Siskos = before) — head-to-head never published | e21 | entity-class WER by strategy |
| C-6 | **Negative controls**: mismatched evidence (rotation), distractor lists, oracle upper bound (scorer-side only) | SUPPLY | bucket1 (our R4 mismatched arm) | e21 | that gains are content-driven, not prompt-length artefacts |

*Status*: C-3 and C-6 in flight (the R4 three arms are dose points
none/matched/mismatched). C-1/C-2/C-4/C-5 designed only.

---

## W-D · System optimization （系统优化）

Closing the loop: use signals the agent can actually observe (no logits) to
choose its own policy. This is construct 4 and the study's contribution core.

| id | variant | axis | precedent | carrier | measured |
|---|---|---|---|---|---|
| D-1 | **Observation-quality signals**: transcript-length ÷ VAD-speech-seconds, char-loop rate, OOV density, acoustic SNR/clipping | OBS | bucket3; the whole-call collapse handed us the first such signal | all | signal-vs-error correlation (does the trigger predict badness?) |
| D-2 | **Selective re-observation**: badness trigger → pinned denoiser → re-ask → deterministic keep rule | OBS+USE | bucket3 | e21/e22 | fraction re-asked, WER change on re-asked slices only |
| D-3 | **Condition-aware routing**: choose direct vs mediated (self-cascade) per input, from D-1 signals | OBS | bucket3; motivated by FDB-v3's reversal (cascade collapses on self-corrections) | bba, e21, fdb-v3 | metric vs a fixed-policy baseline |
| D-4 | **Cost-aware evidence policy**: spend evidence tokens only where predicted useful | SUPPLY | bucket3 | e21 | metric per evidence token |
| D-5 | **Self-consistency / sampled n-best**: multiple samples, agreement-based selection or uncertainty surfacing in the prompt | USE | bucket1 off-carrier (WCN-ICL closed 81 % of the 1-best→oracle gap) | slurp, heysquad | metric vs sample count (cost multiplier) |
| D-6 | **Joint policy**: a single controller over W-A/W-B/W-C knobs, evaluated end to end | all | bucket3 | e21 + one non-ASR carrier | end-to-end metric, ablation of each input signal |

*Status*: all designed only. D-1 has one free signal already (the
length-ratio detector that would have caught the whole-call collapse).

---

## Technical exploration directions (cut across the groups)

1. **Speech-native retrieval** — query the KB with audio rather than a
   transcript (B-6 + C-4). Published work needs a trained bi-encoder
   (SpeechDPR); doing it with a pinned local embedding model over
   core-produced transcripts is the reachable analog, and the gap between the
   two is itself a result.
2. **Multi-task on one substrate** — the positioning claim requires evidence:
   run the same agent, unchanged, on transcription (e21), SLU (slurp), spoken
   QA (spoken-squad/slue-sqa-5) and tool calling (audio2tool/voiceagentbench),
   reporting distance-to-best-single-task-baseline for each. This is the
   headline experiment for the "one core, many tasks" claim.
3. **Streaming / incremental operation** — the loop is already incremental;
   making it truly streaming (emit as you go, revise on later evidence)
   connects to full-duplex work and to FDB-v3's disfluency findings.
4. **Cross-lingual** — speech-massive (12 locales), minds14 (14), VAB Indic.
   Whether evidence supply helps *more* where the core is weaker is a sharp,
   cheap test of the whole thesis.
5. **Paralinguistic evidence** — speaker turns, emotion, prosody as ORG
   content rather than as a task; relevant to meeting carriers (AMI) and to
   VoiceAssistant-Eval's speaking subtasks.
6. **Failure taxonomy as a deliverable** — with no logits, our error analysis
   is behavioural; a reusable taxonomy of frozen-core failure modes (collapse,
   loop, drop, hallucinated entity, format break) with detectors is a
   contribution in its own right and feeds D-1.

---

## Parallelism and dependencies

- **W-A gates everything**: a substrate change invalidates cross-group
  comparisons, so W-A items are batched and the A0 baseline re-run after.
- **W-B and W-C are tightly coupled** (a store exists to be consumed) but can
  progress with a stub on the other side: B items measured by an oracle
  consumer, C items measured with a fixed store.
- **W-D depends on W-A/B/C existing**, but D-1 (signals) can be built and
  validated on data we already have — the E-001 traces contain the
  length-ratio signal today.
- Suggested first parallel wave, after R4 lands: **A-4** (self-cascade, the
  strongest precedent we have), **B-2** (bias lists, data already on disk),
  **D-1** (signals from existing traces — no model touches at all).
