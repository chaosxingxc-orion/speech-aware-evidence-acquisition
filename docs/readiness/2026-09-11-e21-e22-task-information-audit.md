# Earnings21 and Earnings22 task-information audit

This is a model-free design audit. It reads local dataset identity, loaders, protocol definitions, and already sealed information audits. It does not create a task, admit a run, or authorize a value/memory artifact.

## Scope and evidence boundary

The two Earnings carriers are ASR carriers. Their runtime contract is to transcribe English call speech word for word; it contains no tool registry, ontology, or fixed evidence text ([`rails/adapters/earnings.py`](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L80-L86)). Reference text is scorer-side only and does not travel in a runtime sample ([`earnings.py`](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L90-L101)). The sealed direct and repair studies therefore support ASR and contextual-ASR evidence only. They do not define a meeting-summary or minutes label, output format, or native minutes metric.

The common hard boundary remains: evaluation reference transcripts, annotations, gold labels, and future turns cannot enter runtime. A prospective artifact may use train/construction material only where the registered carrier contract permits it; it must name the split, provenance, and the time/state available when it is consumed.

## Earnings21

### Native task and useful information

| Stage | Native information relationship | Supported source and limitation |
| --- | --- | --- |
| Input | One MP3 call, its stable ID, duration, and sample rate. | `earnings21-original` defines media plus `file_id`, `audio_length`, and `sample_rate` ([`data/carriers.py`](../../src/speech_aware_evidence_acquisition/data/carriers.py#L353-L364)). |
| Inference | Produce the spoken-English transcript. | The task contract is ASR, not structured extraction ([`rails/adapters/earnings.py`](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L80-L86)). |
| Native output/metric | Transcript hypothesis; WER is the primary native outcome. | The reference and Whisper-normalized WER path remain scorer-only. The ConEC per-entity calculation is a contextual-ASR diagnostic, not an entity-F1 task: its paper definition reports WER overall and by entity type ([`reproduction/conec_entity_scoring.py`](../../src/speech_aware_evidence_acquisition/reproduction/conec_entity_scoring.py#L5-L23)). |
| Contextual opportunity | The current call’s ConEC context, participant names, and bias list can support recognition of call-specific names and terms. | The sealed E21 audit marks precisely those three as runtime-legal, one document per call; other-call documents are forbidden ([`2026-09-03 E21/ConEC audit`](../checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/README.md#L7-L28), [L149-L154](../checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/README.md#L149-L154)). |

ConEC is a separate evidence carrier, not hidden adapter state: the adapter receives a runner-built `SupplyPacket` and never opens ConEC itself ([`rails/adapters/earnings.py`](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L49-L57)). This is a useful separation for an eventual value artifact: source binding and supply/use traces can remain explicit.

### What is available, and what is not established

E21’s locked layers include media metadata, NLP references, WER tags, and normalizations ([`data/identity.py`](../../src/speech_aware_evidence_acquisition/data/identity.py#L230-L247)). Those reference/tag layers are scorer material, not runtime inputs. The E21-side ConEC package also has contexts, NLP references, timestamp files, and WER tags ([`data/identity.py`](../../src/speech_aware_evidence_acquisition/data/identity.py#L268-L288)); the existing information audit authorizes only contexts, names, and bias lists at runtime. It does **not** establish a runtime speaker-turn annotation, a diarization output, or timestamp-bearing transcript as legal current evidence. A future design must bind any such signal separately instead of inferring permission from its on-disk presence.

The present ConEC value is not wholly unstructured. `conec-names` already supplies a source-bound, per-call roster verbatim with a stable evidence ID, source URI, and source hash ([`core/evidence.py`](../../src/speech_aware_evidence_acquisition/core/evidence.py#L390-L449)). KC-E1 and KC-E1f additionally render participant/role, organization/division, company/ticker, product/segment, and residual-term classes from the same call-local sources (`configs/experiment/e21-kc-e1-brief-44-v1.json`, lines 7-11 and 46-57). Its key is still the current call ID, and the documented reachability result does not make it a general corpus retriever: own-context membership was 30.17% versus 16.50% for a random other call ([`E21/ConEC audit`](../checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/README.md#L106-L139)).

**Genuine value gaps:** the current roster preserves person names and roles, and the existing class lists preserve useful term classes, but neither gives a runtime span-to-candidate relation, a confidence/applicability relation for a current audio span, a typed authority relation between a participant role and an organization mention, or a policy proven to select a fact only for an uncertain span. There is no currently admitted cross-call corrective-memory supplier. These are representation and decision gaps, not evidence that a new value design improves WER.

### E21 task items and value fields

| Item | Existing support | Useful task-knowledge fields, if prospectively defined | Current limit |
| --- | --- | --- | --- |
| Ordinary words | Audio and the ordinary ASR contract. | No external value is needed; an explicit `audio-grounding-required` constraint is already a baseline safety condition. | It is not learned memory. |
| PERSON and participant names | Per-call roster and KC-E1f participant/role rendering. | surface form, normalized form, participant role, source section, call ID, and source hash. | No registered claim links a particular observed span to a candidate. |
| Organizations, products, and other proper names | Class-list brief carries organization/division, company/ticker, product/segment, and residual terms. | canonical surface/normalized form, class, source section, call ID, and source hash. | No typed entity-to-role/organization authority graph or span applicability score. |
| Numbers, units, and negation | They remain speech-recognition content; references/tags are scorer-only. | A future legal source could declare a unit/format only when it is in the same call-local evidence. | No runtime numeric/negation gold or correction table may be derived from references. |
| Window-boundary continuity | Existing fixed windows and repair plans retain source-window and selected-span lineage. | current call ID, window ordinal/time bounds, predecessor terminal request ID, and a no-future-state rule. | No approved cross-window linguistic memory or speaker-turn state is established by ConEC timestamps. |

The latest closed E21 direct-to-KC-E1f comparison records PERSON WER 23.14021 to 19.74631 and corpus WER 8.12086 to 8.07499, with five additional insertions. These figures motivate preserving exact-audio and no-insertion constraints; they do not authorize a summary task or establish a learned correction rule.

**Hypothetical useful task knowledge:** a call-local, source-bound compact relation table can build on the already structured roster/class lists by retaining source section and class/role fields and adding only auditable applicability metadata. It must not incorporate `wer_tags`, reference spans, or reference transcript text.

**Hypothetical corrective memory:** a memory candidate requires a validated, sealed symptom-to-action relationship that changes a later policy, for example a specific observed ambiguity pattern plus a bounded correction action and its evaluation lineage. “Only use a listed word when the audio supports it” is a standing grounding constraint, not a new memory item. No such E21 corrective-memory relation is validated here.

## Earnings22

### Native task and useful information

| Stage | Native information relationship | Supported source and limitation |
| --- | --- | --- |
| Input | One MP3 call or an explicitly registered speech segment, with stable ID, duration, and sample rate. | `earnings22-original` declares `File ID`, `File Length (seconds)`, and `Sampling Rate (Hz)` ([`data/carriers.py`](../../src/speech_aware_evidence_acquisition/data/carriers.py#L387-L398)). |
| Inference | Produce a spoken-English transcript. | The shared Earnings adapter’s task contract applies to E21 and E22 ([`rails/adapters/earnings.py`](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L35-L47), [L80-L86](../../src/speech_aware_evidence_acquisition/rails/adapters/earnings.py#L80-L86)). |
| Native output/metric | Transcript hypothesis scored with ASR WER on the registered evaluation view. | E22 has NLP and force-aligned NLP reference layers for scoring ([`data/identity.py`](../../src/speech_aware_evidence_acquisition/data/identity.py#L250-L265)); these do not authorize runtime use. |
| Contextual opportunity | An existing E22 pre-meeting brief can use only the call’s own metadata row. | The metadata renderer permits ticker, country, UN region, major dialect family, and language-family/area; it explicitly excludes external company lookup and every reference, speaker, segment, and annotation layer ([`core/metadata_brief.py`](../../src/speech_aware_evidence_acquisition/core/metadata_brief.py#L13-L39)). The unrelated ConEC PDF packets remain unsupported and `conec-contexts` fails closed ([`data/carriers.py`](../../src/speech_aware_evidence_acquisition/data/carriers.py#L399-L407)). |

E22’s verified accent-related facts are limited to the metadata row’s `Major Dialect Family` and `Language Family + Area Based`, plus country/UN region and ticker ([`core/metadata_brief.py`](../../src/speech_aware_evidence_acquisition/core/metadata_brief.py#L15-L30)). No speaker identity/list, topic, summary, minutes, dialogue-state annotation, or segment table is established as a runtime field. The force-aligned reference layer is an evaluation artifact. HALAS, where present, is an annotation overlay rather than an E22 task definition and cannot be treated as runtime knowledge without a separately authorized contract.

### E22 task items and value fields

| Item | Existing support | Useful task-knowledge fields, if prospectively defined | Current limit |
| --- | --- | --- | --- |
| Ordinary words, numbers, units, and negation | Audio-only ASR. | No derived correction value; preserve exact-audio grounding. | References/alignments remain scorer-only. |
| Proper names and ticker-related terms | Ticker only, from the call’s own metadata row. | ticker, source-row hash, call ID, and a call-local applicability marker. | No company-name lookup or external terminology source is allowed. |
| Accent/dialect | Major dialect family and language-family/area are existing metadata facts. | dialect-family, language-family/area, country/region, row hash. | They are call metadata, not speaker identity or a transcript correction label. |
| Speaker, boundary, or continuity | No approved runtime source. | None until a source-bound observation contract exists. | No speaker list, segment table, or dialogue state may be inferred from force alignment. |

**Current value gap:** E22 has a narrow, already admitted metadata-value provider, not a ConEC-style contextual lexicon. A future value design must remain within the row’s ticker/country/region/dialect fields or register another legal carrier-specific source; copying E21 contexts or treating the PDF collection as per-sample text would violate the fail-closed declaration.

**Hypothetical corrective memory:** a post-seal ASR correction rule could be represented and assessed only after a prospective training/evaluation split and legal source are defined. It must encode a validated symptom-to-action policy change, not merely restate audio grounding. There is no existing native E22 minutes/summary metric against which such a memory could be justified.

## Cross-carrier design implications

1. Treat E21/E22 as transcript-quality tasks. A value representation should target recognition decisions such as contextual spelling or permitted call-local terminology, then be evaluated by the registered WER path. Do not recast either as a minutes task.
2. Keep task knowledge and corrective memory separate. Task knowledge is a stable, pre-contact, source-bound artifact allowed by the carrier. Corrective memory is a post-seal derived rule with a declared applicability test and a held-out evaluation path.
3. Keep E21 call-local. Its established ConEC organization is self-supplied rather than cross-call retrieval; foreign-call supplementation is explicitly a contamination risk ([`E21/ConEC audit`](../checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/README.md#L149-L154)).
4. Do not infer availability from files. E21 timestamps and E22 force alignment are present in locked layers, but the existing runtime contracts do not authorize them as evidence. Speaker/topic continuity requires a new, source-bound observation/tool contract before it can be a value key.
5. The SLURP finding is informative only at the architecture level: its native task has structured intent and slots, whereas Earnings has ASR output. A compact typed value frame can be designed per carrier, but its labels, estimator, and legality must remain carrier-specific.
