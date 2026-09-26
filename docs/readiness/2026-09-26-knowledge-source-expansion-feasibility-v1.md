# Knowledge-source expansion: what this study could admissibly use, and what each would cost

Date: 2026-09-26. Branch `fable/sources`. A **feasibility and governance survey**, not an
acquisition. Nothing was downloaded, fetched, mirrored or registered; no lock file was touched; no
asset was added; no gain is claimed.

**Zero contacts.** No model, server, tokenizer, encoder, embedder, scorer, ASR or paid-API contact;
0 audio seconds; 0 GPU hours; no network of any kind. Every on-disk asset named below was opened
**read-only** under `SPEECHRL_DATA_DIR`. No utterance text, transcript, reference token, gold
filler, delivered text or knowledge body text appears anywhere in this note: every cell is a count,
a byte size, a share, a field name, a label-space cardinality, a licence string or a path.

**Ownership boundary.** This note is the **source side** only. It does not measure this study's
error mass, its coverage curves or the five-failure-mode attribution -- those belong to
`fable/coverage`, and where a coverage fact is needed here it is **cited** from
`docs/results/2026-09-24-slurp-plan-bad-case-bank.md` and
`docs/readiness/2026-08-25-slurp-intent-coverage-check.md` rather than re-derived. It does not
analyse the supply path, dedup or re-ranking (`fable/dedup`), and it does not touch
`docs/results/stage2-results-ledger.json`.

Gate run in this worktree, read-only: `bash scripts/flights/batch/main_gates_generic.sh` ->
`finite_completion_policy_check`, `results_ledger_check`, `harness_admission_check`,
`engineering_base_check`, `tool_catalog_check`, `stage3_algorithm_label_check`,
`stage3_effect_floor_check` all **exit 0**.

---

## 1. The rules every candidate is judged against, quoted

Study `CLAUDE.md`, research boundary (immutable):

> Human speech and its linguistic content only: ASR, entities, contextual biasing, spoken QA,
> meeting speech understanding.

> WAV/MP3 are carriers of the speech signal; general/environmental audio tasks are out of scope.
> FSD50K, AudioSet, and ESC-50 must never be consumed by this repository's loaders, tests, or
> configs.

> Gold labels, reference transcripts, test annotations, and future turns must never enter runtime;
> discovery and confirmatory stay isolated.

Study `CLAUDE.md`, routing:

> The single live source of dataset identity is umbrella `docs/datasets.lock.json`. Core keys are
> `earnings21-original`, `earnings22-original`, `conec`, and `qwen3-omni-30b-a3b-instruct-gguf`;
> never copy revisions or hashes out of it.

> Large bytes live under `SPEECHRL_DATA_DIR` and never enter Git.

Study `CLAUDE.md`, owner directives of 2026-09-03:

> **Carriers.** Locked to Earnings21+ConEC, SLURP, Audio2Tool until the owner expands the set.

Study `CLAUDE.md`, prohibited:

> Paid API spend (= 0, still in force).

> Committing data, weights, speech files, or raw traces; moving code in around the migration
> manifest.

Two in-repo legality tables are the operative fine grain, and they are quoted as written because
they already dispose of several candidates. `analysis/information_audit_specs.py`:

> `_SLURP_CORPUS_STRUCTURE_LEGALITY`: `"train_synthetic split": "forbidden"`,
> `"test split": "forbidden"`

> `_SLURP_FIELD_LEGALITY`: `"devel/test sentence text": "forbidden"`, `"train sentence text
> (SlurpTrainMaterial.sentence)": "construction-only-knowledge"`, `"train speaker_id":
> "construction-only-knowledge"`

> `_EARNINGS_FIELD_LEGALITY`: `"reference transcript tokens (.nlp)": "forbidden"`, `"wer_tags entity
> id -> entity_type sidecar": "gold-scoring-only"`, `"ConEC context document
> (evidence_source=conec-contexts)": "runtime-legal-input"`

**A new umbrella lock entry, for the candidates that need one, requires:** a registration in
`docs/datasets.lock.json` under an owner-dated `amendments[]` entry with
`kind: asset-registration`; identity verified live against the official source **before** any byte
is fetched (the standing register-then-fetch discipline of every prior wave); a per-file digest
recorded from the upstream authority; `status`, `license`, `license_note`/`claim_limit` and a
profile membership; bytes landed only under `SPEECHRL_DATA_DIR`; and a receipt under
`docs/checks/speech-aware-evidence-acquisition/<date>-<name>/`. The umbrella owns that file; this
study never edits it.

---

## 2. The table, cheapest admissible first

Sort key: (1) governance cost, (2) engineering work, (3) expected value as tiebreak. Rows 1-7 are
inside assets this programme already owns at a pinned identity. Rows 15-20 are refusals.

| # | Group | What it is | What knowledge it would populate | Admissible under the boundary | Governance step it needs | What it would cost to try |
| --: | --- | --- | --- | --- | --- | --- |
| 1 | 1 | SLURP `tokens[].pos` and `tokens[].lemma` -- a POS tag and a lemma on every token of every row of all four split files, inside the pinned `slurp` key | Slot-contract knowledge (which POS/lemma shapes carry which slot type); a gold-free draft-shape signal | **Yes.** Train-side linguistic annotation is "train sentence text ... construction-only-knowledge" in kind; no rule names it | **None.** Unused material inside an already-pinned asset; nothing in `src/` reads `pos` or `lemma` today | One offline read. No lock change, no decision, no new bytes |
| 2 | 1 | SLURP `recordings[].wer` and `recordings[].ent_wer` -- the release's own per-recording baseline WER and entity-WER. Present on **all 50,628** train recordings (`wer`) and **31,657** of them (`ent_wer`, the entity-bearing rows) | Sample difficulty / selection prior -- exactly the owner's "which samples". Median 0.000, mean 0.084, **2.3 %** of train recordings above 0.5; **705 / 11,514** train utterances disagree by >0.5 across their own recordings | **Yes on train rows only.** On devel/test rows the same field is computed against the reference, so it is gold-derived and falls under "Gold labels, reference transcripts, test annotations ... must never enter runtime" | **None for the read.** One row added to `_SLURP_FIELD_LEGALITY` to record the train/devel split in tier, plus a split filter in the loader | One offline read plus a fail-closed split guard |
| 3 | 1 | SLURP `metadata.json` unused fields: `sentence_original` (differs from `sentence_normalised` on **14,067 / 16,521** prompts = **85.1 %**), `userid_amt` (**691** distinct prompt authors), `nlub_id`, per-prompt `status` (4 annotation-quality values), per-recording `recid` / `ansid` / `status`. `usrid` (**174** speakers) is already consumed by `data.slurp._slurp_speaker_index` | Author-stratified construction rosters (disjointness by prompt author, not only by speaker); the pre-normalisation surface form as a second exemplar rendering; an annotation-quality filter | **Yes for the train subset.** But the file is **split-blind**: its 16,521 prompts are exactly the union of the three real splits (11,514 + 2,033 + 2,974), so it carries devel and test prompt text too | **None as a decision.** An engineering guard: the loader must filter to train `slurp_id`s or it puts "devel/test sentence text: forbidden" in reach | One offline read plus the split filter. The speaker path already proves the file parses |
| 4 | 1 | SLURP `dataset/lm/lm.txt` -- 987,933 B, 29,104 lines, **11,502 unique** sentences | **Nothing new.** It is exactly the train split's unique sentence set: 100.0 % of train's 11,502 unique sentences, and 4 / 2,032 devel and 6 / 2,973 test sentences by incidental short-utterance collision | Yes, and irrelevant | None | Recorded here so nobody spends a wave re-acquiring it |
| 5 | 1 | ConEC `earnings21/transcripts/timestamps/` -- 44 `.nlp` files, 13,826,694 B (45 entries incl. one `.gz`). Same 8-column schema as `nlp_references` (`token`, `speaker`, `ts`, `endTs`, `punctuation`, `case`, `tags`, `wer_tags`) and **identical token counts on all 44 calls**, but `ts` is populated on **245,383 / 362,747** tokens (**67.6 %**) against **0 / 362,747** (**0.0 %**) in `nlp_references` | Nothing at runtime. Offline it is a word-boundary key for OBS-side segmentation work (speaker-turn units, relisten planning), which today has no such key | **No at runtime**, by `_EARNINGS_FIELD_LEGALITY`: `"reference transcript tokens (.nlp)": "forbidden"` -- these files *are* the reference transcript. **Needs a decision** to register at `gold-scoring-only` for offline use | One legality-table row plus a reader. No lock change; the bytes are inside the pinned `conec` key | One offline read. **It also corrects a standing repo assertion**: `analysis/e21_person_harm.py` states "The Earnings-21 reference layer carries **no word timestamps**". The reference layer does not; the pinned asset ships a layer that does, and nothing reads it |
| 6 | 1 | SLURP `train_synthetic.jsonl`, **decontaminated text/label side only**. Dropping every row whose `slurp_id` **or** whose normalised sentence occurs in devel or test keeps **15,705 / 19,711 rows (79.7 %)** | **6,382** unique sentences absent from train, keyed by `scenario_action`; **446** distinct new entity fillers; fillers for **11 of the 12** train entity types that hold fewer than 10 distinct fillers; **9** `scenario_action` keys absent from train (`general_affirm`, `general_commandstop`, `general_confirm`, `general_dontcare`, `general_explain`, `general_negate`, `general_praise`, `general_repeat`, `qa_query`); `general` goes from 652 train rows over 3 keys to 5,494 rows over 11 keys | **Needs a decision.** No boundary rule forbids it, but `_SLURP_CORPUS_STRUCTURE_LEGALITY` records `"train_synthetic split": "forbidden"` -- correctly derived for the **undecontaminated** split, where **1,317 / 2,033 devel** `slurp_id`s (**64.8 %**) and **1,889 / 2,974 test** (**63.5 %**) recur verbatim (sentence-level: 70.0 % and 68.7 %). The 64.8 % is a **row** property, not a split property | One recorded change to that legality row, from "forbidden" to "construction-only-knowledge for the decontaminated slice", plus the identity-only decontamination discipline `docs/receipts/knowledge/slurp-split-identity.json` already established | One offline read plus the filter. **But read section 3.6 before spending it: the 9 new keys sit outside the evaluation label space, so this buys depth, not coverage** |
| 7 | 1 | ConEC `earnings21/contexts/pdfs/` -- **66 PDFs, 73,972,083 B**, inside the pinned `conec` key. `core/class_lists.py` says of it: "the third context artifact, `contexts/pdfs/*.pdf`, is binary, has no D1 layer and **is read by nothing in this repository**" | **Cased, structured entity surface forms** -- company, ticker, product, segment and division names -- for the Earnings pre-meeting brief and the bias list. The repo's own reason this matters: the 44 `.txt` files it does read (358,266 B in total) are "a LOWERCASED, function-word-stripped token stream ... casing, punctuation, sentence structure and the document boundary are all gone, so no class can be read off it" | **Yes.** It is the benchmark's own public pre-existing context document, the same provenance tier as `conec-contexts` ("runtime-legal-input"), and it contains no reference transcript and no gold label | A D1 layer registration, a `contracts.gate_evidence_identity` routing rule for the `pdfs/` shape (today it is deliberately fail-closed: "ConEC's own `pdfs/` -- D1-excluded exactly like `participant_names` was before this rail existed"), and a `derived_media_confinement_check` disposition for the extracted text | Moderate: a PDF-to-text pass plus three gate-side registrations. **Extraction is already possible fully offline** -- `pypdf`, `pdfminer` and `pdfplumber` are all present in the shared `~/.venvs/speechrl`, so no install is needed |
| 8 | 2 | SLUE-VoxPopuli fine-tune split -- already a `COMPLETE` pinned asset (`speech-aware-secondary`), 5,000 English utterances with `id`, `raw_text`, `normalized_text`, `speaker_id`, `raw_ner`, `normalized_ner` plus 5,000 audio files, and a dev TSV beside it | An English speech-NER exemplar and entity-type pool for the Earnings entity work | **Needs a decision.** The content fits ("entities", human speech), and the asset is already pinned, so no lock change. But it is not one of the locked carriers, and admitting a **different corpus** as a knowledge source for a locked carrier is an information-legality change, not an engineering one | Owner decision on cross-corpus knowledge supply; then a `_EARNINGS_EXTERNAL_SUPPLEMENTATION` entry | One offline read, zero new bytes. Type-inventory mismatch against ConEC's `wer_tags` classes needs verification first |
| 9 | 2 | MINDS-14 `en-AU` / `en-GB` / `en-US` -- already `COMPLETE` on disk, train split only, 14 e-banking intents | A second spoken-intent exemplar pool in a different domain | **Needs a decision**, same reasoning as row 8 | Owner decision on cross-corpus knowledge supply | One offline read, zero new bytes. Low expected value: a disjoint ontology cannot add a key the SLURP task is scored on |
| 10 | 2 | Audio2Tool `tools_registry.csv` -- 152 tool rows over `tool_id, domain, category, tool_name, signature, description, argument_defaults, argument_constraints`. For its own carrier it is already `runtime-legal-input` | For **SLURP**: nothing. The registry is a tool-call schema over a different action space; it shares no ontology with SLURP's scenario/action/slot inventory | **Needs a decision**, and the decision is not worth asking for. Technical possibility is not legitimacy: cross-carrier supply is nowhere granted by the current rulings | Owner decision | Cheap to try and expected to be empty. Recorded so the option is closed on the record rather than by silence |
| 11 | 2 | ConEC entity material for SLURP -- `earnings21/contexts/participant_names/` (45 files, 30,580 B, `Name - Role` lines) and the `wer_tags` entity-type sidecars (44 JSON files, one `entity_type` per entity id, 1,048 ids on the first call) | For **SLURP**: nothing. Earnings-call PERSON/ORG in a financial domain against SLURP's personal-assistant slot fillers | **No for the `wer_tags` half**, which is `"gold-scoring-only"` by `_EARNINGS_FIELD_LEGALITY`. **Needs a decision** for the names roster, with no expected value | Owner decision | Same as row 10: closed on the record |
| 12 | 2 | The ConEC **Earnings-22** layer -- `earnings22/contexts/pdfs/` (**100 PDFs, 252,853,574 B**) and `earnings22/transcripts/nlp_references/` (125 `.nlp`) | A second earnings-call context pool at roughly 3.4x the Earnings-21 PDF volume | **Needs an owner decision.** Earnings-22 is not in the locked set -- "Carriers. Locked to Earnings21+ConEC, SLURP, Audio2Tool until the owner expands the set" -- and `data/carriers.py` deliberately declares `evidence=None` for `earnings22-original` so that a config naming it with `evidence_source=conec-contexts` fails closed | Owner carrier expansion, then the same three gate registrations as row 7 | Larger than row 7 and behind a carrier decision. Do row 7 first and let its result decide whether to ask |
| 13 | 3 | SLUE phase-2 HVB (HarperValleyBank spoken dialog, dialog-act and entity labels), reachable through the `slue-toolkit` already pinned in the umbrella lock at revision `ed23039507c8f01b704a5c43ed89b6e808a49405` | Dialog-act and entity exemplars over English task-oriented speech | **Plausibly yes** on content (human speech, entities, spoken understanding). Licence, exact size and split layout **need verification** -- this is my own knowledge of the benchmark, not a repository fact, and no number is asserted | A new umbrella lock entry (register-then-fetch, official-source verification, receipt) **plus** an owner GO, **plus** the row-8 cross-corpus knowledge-source decision | A download wave and two decisions. The distribution channel is already governed, which is its only cost advantage |
| 14 | 3 | STOP (spoken task-oriented semantic parsing, English, multi-domain, hierarchical parses) | A second full intent/slot ontology with its own exemplar pool | **Plausibly yes** on content. Licence and size **need verification**; my own knowledge only, so no number is asserted here | New umbrella lock entry + owner GO + the cross-corpus knowledge-source decision | The most expensive admissible option, and it buys breadth where breadth is already complete (section 3.6) |
| 15 | 3 | Speech-MASSIVE -- already `COMPLETE` on disk at a pinned revision, 32,498,335,745 B, `cc-by-nc-sa-4.0`. The spoken localisation of MASSIVE, whose ontology descends from SLURP's | Would have been the ideal ontology-aligned exemplar pool | **No.** The on-disk language directories are `ar-SA de-DE es-ES fr-FR hu-HU ko-KR nl-NL pl-PL pt-PT ru-RU tr-TR vi-VN` and the card declares `ar de es fr hu ko nl pl pt ru tr vi`. **There is no English.** An English-only study cannot use it as an English knowledge source | None -- refused | Nothing. Recorded because it is the candidate a reader would expect to win |
| 16 | 1 | SLURP `experiments/predictions/*.jsonl` -- 7 baseline system prediction files inside the pinned checkout | Nothing admissible | **No.** Row counts are 2,974 (exactly the test utterance count) and 12,393 / 14,093 / 13,071 (against 13,078 test recordings): every file is over the **test** split. `"test split": "forbidden"`, and "test annotations ... must never enter runtime" | None -- refused. Usable only as published-baseline comparator numbers, which is not knowledge | Nothing |
| 17 | 1 | SLURP synthetic **audio** -- 69,257 FLAC on disk, reconciled, referenced by the rows of row 6 | Would have been extra OBS material at zero acquisition cost | **No.** It is TTS, not recorded human speech -- `docs/readiness/2026-08-25-slurp-intent-coverage-check.md` states "`train_synthetic` **is TTS audio**" -- and the boundary reads "Human speech and its linguistic content only" | None -- refused. Row 6 is the text/label side **only**; the audio side does not travel with it | Nothing. The split between the two sides is the whole point of row 6 |
| 18 | 3 | ATIS spoken / MultiATIS++ audio, and any LDC-distributed spoken-SLU corpus | Another intent/slot pool | **No.** Acquisition requires a paid licence, against "Paid API spend (= 0, still in force)" and the standing zero-cost acquisition practice every prior wave records ("Zero cost; no paid, gated or form-walled source was used") | None -- refused | Nothing |
| 19 | 3 | Fluent Speech Commands and any registration-form-walled spoken-SLU release | Small intent pool | **No on the channel, not the content.** The standing practice is "no paid, gated or form-walled source", and this survey has no network access to test a channel in any case | None -- refused | Nothing |
| 20 | -- | FSD50K, AudioSet, ESC-50 -- all three are locally `COMPLETE` under the umbrella `retained-cross-domain` profile, so they are a live temptation rather than a hypothetical | Nothing | **No, by name.** "FSD50K, AudioSet, and ESC-50 must never be consumed by this repository's loaders, tests, or configs" | None -- refused | Nothing. Listed because being on disk is not being in scope |

---

## 3. Notes on the rows that carry the survey

### 3.1 The immediate answer: rows 1, 2, 3 and 4 need no governance at all

Rows 1-4 are **unused material inside an already-pinned asset**. The `slurp` lock key is
`COMPLETE`, the label side has a governed copy at `datasets/slurp/metadata` with per-file digests,
and the pinned checkout `repos/slurp` is diff-clean against its recorded revision. Reading a field
of a file this programme already owns, already verified and already loads is not an acquisition: it
needs no lock amendment, no owner GO, no exposure row and no new bytes. The only obligation rows 2
and 3 carry is a **split filter**, because `recordings[].wer` exists on devel/test rows too and
`metadata.json` is split-blind across all 16,521 real prompts.

Row 1 is the cleanest of the four: `tokens[]` on every SLURP row carries `id`, `surface`, `lemma`
and `pos`, and nothing in `src/speech_aware_evidence_acquisition/` reads `lemma` or `pos` -- the
loader touches `tokens[]` only to recover a filler surface from a `span`.

### 3.2 Row 2 is the one the owner's question actually asked for

The owner asked which samples would let the model perform well enough. SLURP ships a per-recording
difficulty signal computed by its own authors and this study has never read it: `wer` on all 50,628
train recordings, `ent_wer` on the 31,657 entity-bearing ones. It is skewed hard (median 0.000,
69.5 % exactly zero) and its tail is the interesting part (2.3 % above 0.5), and 705 of 11,514
train utterances have recordings that disagree by more than 0.5 -- the same sentence, some
recordings easy and some hard. That is a ready-made, gold-free-at-construction-time stratifier for
a construction roster, and it costs one read.

### 3.3 Row 5 corrects a fact this repository states about itself

`analysis/e21_person_harm.py` asserts that the Earnings-21 reference layer carries no word
timestamps, and for `nlp_references` that is exactly right: **0 of 362,747** tokens have a populated
`ts`. But ConEC ships a second `.nlp` layer under `transcripts/timestamps/` with the identical
8-column schema and the identical token count on all 44 calls, in which **245,383 of the same
362,747 tokens (67.6 %) are timestamped**. Nothing reads it. It is reference-transcript bytes, so
it is forbidden at runtime and the right disposition is `gold-scoring-only`; but as an offline key
for OBS-side segmentation it is 13.8 MB of already-owned ground truth that the repository currently
believes does not exist.

### 3.4 Row 6: the 64.8 % is a row property, and the decontamination changes the verdict

The synthetic split was excluded on a measured finding, quoted from
`data.slurp.load_slurp_ontology`'s own docstring: "1,317 of 2,033 `devel.jsonl` `slurp_id`s (64.8%)
recur VERBATIM in `train_synthetic.jsonl` -- identical sentence AND identical entity set". That
verdict is correct for the split as a whole. It is a statement about **which rows** recur, not about
the file, and dropping those rows is the same identity-only decontamination discipline this
repository already runs elsewhere. After dropping every row whose `slurp_id` or normalised sentence
occurs in devel or test, **79.7 %** of the split survives and contributes 6,382 sentences, 446
entity fillers and support for 11 of the 12 thinnest entity types. I measured the test side too,
which had not been published: **1,889 of 2,974 test `slurp_id`s (63.5 %)** recur, so the filter must
run against devel **and** test, not devel alone.

### 3.5 Row 7 is the one real source-side gap

The Earnings side has a genuine, unread source. This repository reads ConEC's 44 lowercased,
function-word-stripped token streams (358 KB) and describes them in its own words as UNLABELLED
because casing, punctuation, sentence structure and document boundaries are gone. The documents
those streams were made from are sitting beside them: 66 PDFs, 74.0 MB, inside the same pinned lock
key, read by nothing. Cased entity surface forms are precisely what the Earnings entity work is
short of, and `pypdf`, `pdfminer` and `pdfplumber` are already installed in the shared environment,
so the extraction is offline and free. The cost is three gate-side registrations, not an
acquisition.

### 3.6 Why breadth is the wrong lever, stated from the source side

The SLURP evaluation label space is **60 `scenario_action` keys**, and
`docs/readiness/2026-08-25-slurp-intent-coverage-check.md` records that
`devel_scenario_action_absent_from_train` is **the empty set**. My own independent count on the
governed bytes agrees and extends it: devel holds 59 keys, test holds 59, and the number of devel or
test keys absent from train is **0 and 0**. Six of train's 60 keys hold fewer than 50 utterances,
and the decontaminated synthetic slice adds rows to all six.

The consequence for this survey is blunt. **No new corpus, owned or acquired, can add an intent key
the task is scored on**, because train already covers every key devel and test contain. Every
group-3 candidate, and rows 8, 9 and 14 in particular, would buy label-space breadth that is
already closed. What the owned material can still buy is **depth** -- more and better exemplars per
key, better fillers for thin types, and a difficulty stratifier -- which is rows 1, 2, 3 and 6.

---

## 4. What was refused, and under which rule

| Candidate | Refused under |
| --- | --- |
| SLURP synthetic **audio** (69,257 FLAC) | "Human speech and its linguistic content only" -- the split is TTS, per `docs/readiness/2026-08-25-slurp-intent-coverage-check.md` |
| SLURP `experiments/predictions/*.jsonl` (7 files) | `"test split": "forbidden"` (`_SLURP_CORPUS_STRUCTURE_LEGALITY`) and "test annotations ... must never enter runtime" -- every file's row count matches the test split |
| ConEC `timestamps/*.nlp` **at runtime** | `"reference transcript tokens (.nlp)": "forbidden"` (`_EARNINGS_FIELD_LEGALITY`) |
| ConEC `wer_tags` entity types as SLURP knowledge | `"wer_tags entity id -> entity_type sidecar": "gold-scoring-only"` |
| `metadata.json` read **wholesale** | "devel/test sentence text: forbidden" -- the file spans all three real splits |
| Speech-MASSIVE | No English on disk and none declared; the study is English-only |
| ATIS / MultiATIS++ / any LDC spoken-SLU | "Paid API spend (= 0, still in force)" and the zero-cost acquisition practice |
| Fluent Speech Commands and form-walled releases | The standing "no paid, gated or form-walled source" practice |
| FSD50K, AudioSet, ESC-50 | Named by the boundary: "must never be consumed by this repository's loaders, tests, or configs" |
| Earnings-22 ConEC layer, without a decision | "Carriers. Locked to Earnings21+ConEC, SLURP, Audio2Tool until the owner expands the set" |
| Any cross-carrier supply asserted on technical grounds | No current ruling grants it; `_SLURP_EXTERNAL_SUPPLEMENTATION` lists three sources and all three are SLURP-internal |

---

## 5. Closing: the source side is not the binding constraint

The honest answer is that **we already own more than we use, and the source side is not where this
study is stuck.**

Three facts carry that. First, the umbrella catalog holds 81 registered assets plus 28
frozen-baseline datasets, the great majority `COMPLETE` on disk, and the SLURP work draws on one
split of one of them. Second, the label space is closed: train covers every `scenario_action` key
devel and test contain, so no corpus -- owned, adjacent or acquirable -- can widen the space the
task is scored on. Third, and this is the citation rather than my own measurement,
`docs/results/2026-09-24-slurp-plan-bad-case-bank.md` attributes 12.0 % of TRAIN Fold A rows and
16.9 % of DEV-2000-ADDED rows to `INTENT-UNCOVERED`, which that note defines as "Perception's own
candidate list never contained the gold intent" -- a failure of a stage over a label space the
knowledge base already models, not a failure of the material available to model it. Buying more
corpora would not touch it.

What the survey does find on the source side is narrower and cheaper than an acquisition: four
fields we own and never open (rows 1-4), a 13.8 MB word-timestamp layer the repository asserts does
not exist (row 5), a 79.7 % usable slice of a split that was excluded on a row-level property read
as a file-level one (row 6), and 66 unread PDFs holding exactly the cased entity surface forms the
Earnings side is short of (row 7). All seven sit inside assets already pinned at a verified
identity. None needs a download, a lock amendment or an owner GO; rows 5, 6 and 7 need a recorded
legality decision and, for row 7, three gate registrations.

If the programme wants more coverage, the lever is construction and selection over material already
in hand, not a wave of new corpora. The one place where a genuinely new source would be the right
answer is a **different task surface** -- a carrier whose label space is not already covered -- and
that is a carrier decision for the owner, not a knowledge-source question, and it is outside what
this note is authorised to propose.
