# `content_facet_target` — a narrow correctness audit

**Exposure row** `SAEA-SN-MF-CONTENT-FACET-TARGET-AUDIT` (`model-free-check`), registered at commit
`6dec5ee6` **before any input was opened**.
**Contacts: 0.** `analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first
input and recorded **0 outbound connection attempts against zero targets**. The resident
llama-server (pid 38623, port 8090) was not started, stopped, probed, reconfigured or contacted.
**This row DIAGNOSES and does not repair.** No knob changed; nothing under `rails/`, `core/` or
`configs/` was written; no snapshot rebuilt, no receipt displaced, no arm re-flown, no new sample
touched, no gold surface opened. **No repair design is proposed here.**

**Module** `src/speech_aware_evidence_acquisition/analysis/content_facet_target_audit.py` ·
**receipt** `docs/checks/speech-aware-evidence-acquisition/2026-08-25-content-facet-target-audit/audit-report.json`
(sha256 `ff4311fab3b61719dc5d59b6e30a2eeada899b3d34ba7f7e20b5ac891886dcd5`) ·
**tests** `tests/unit/test_content_facet_target_audit.py` (5) · wall 3.1 s.

---

## 1. The finding, restated exactly

`analysis.contrast_fewshot_preanalysis.SnapshotBundle.content_facet_target`
(`contrast_fewshot_preanalysis.py:256-263`, file sha256
`de299600e0ca57bc83507a2b74db2d6a1a9a62bd184856e3ebde6468109cbabb`) is built by iterating every
`ValueBundle` carrying a non-`None` `task_target` and calling `setdefault(facet_id, task_target)`
over that value's **entire** `associated_facet_ids` tuple. `associated_facet_ids` spans every
KB-BUILD dimension the value touches. **The name asserts a restriction to content facets that the
code does not apply.** Four other places build the identical mapping the identical way
(`dev100_damage_channel_analysis.py:205-210`, `a2t_admission_scale_sweep.py:854-861`,
`dev500_confirmatory_read.py:693-698`, and both hash-pinned frozen launchers).

`analysis.a2t_lexical_ceiling.content_facet_targets` (`a2t_lexical_ceiling.py:149`, sha256
`6dde697bb7fa00a73b3acca50fd29cd2510e3f64851d0e9c40bb10b72cbef0bd`) builds the same mapping and
**then filters it to `facet.dimension == "content"`**. That function is this audit's
content-restricted reference, so the two readings come from two independent pieces of landed code
rather than from one idea written twice.

---

## 2. Q1 — the mapping's actual keys, measured on both pinned snapshots

Keys resolved against each facet's own declared `KeyFacet.dimension`. Every key is a declared facet
on both carriers (0 dangling).

| | **SLURP** `e27b2745…a51b57` | **Audio2Tool** `ec2f9ec4…3baf9fb2` |
|---|---|---|
| facets in snapshot | 11,863 | 12,936 |
| — by dimension | content 11,514 · label 138 · prior 60 · speaker 151 | content 12,601 · label 184 · prior 151 |
| values (all carry a `task_target`) | 11,514 | 12,601 |
| **`content_facet_target` keys, total** | **11,785** | **12,903** |
| — **content facets** | **11,514** | **12,601** |
| — **non-content facets** | **271** (label 60 · prior 60 · speaker 151) | **302** (label 151 · prior 151) |
| content-restricted reference count | 11,514 (agrees) | 12,601 (agrees) |
| content-facet NPZ ids | 11,514, **all content** | 12,601, **all content** |
| non-content keys inside the NPZ | **0** | **0** |
| content keys outside the NPZ | **0** | **0** |

**The finding is confirmed on both carriers.** The mapping is keyed by label, prior and (on SLURP)
speaker facets. Two further set facts, measured over every facet in each snapshot, decide most of
the call-site table: **the landed content-facet NPZ contains content facets only**, and **every
content facet carrying a task target is inside it**.

### 2.1 The set fact that decides every admitted-set call site

`contrast_fewshot_preanalysis._facet_vector_lookup` is the callable both carriers hand to
`kb_policy.multidim_recall`. Probed on **all 11,863 SLURP and all 12,936 A2T facets**, it returns a
vector for exactly the NPZ ids and `{}` for every other facet (349 SLURP, 335 A2T), and the only
dimension it ever returns is `content` — which is **not** in `kb_policy.PRIOR_MASS_DIMENSIONS`
(`{"label", "prior"}`). A facet it answers with `{}` therefore receives no cosine-family dimension
at all, so `dev100_damage_channel_analysis._max_cosine` returns `0.0` for it and the admission test
`>= tau` (τ = 0.65, `kb_policy.py` sha256 `2a1c3d75…1019af`) refuses it. **Every
`admitted_facet_ids` set is a subset of the NPZ id set, and the NPZ id set contains no non-content
facet.** This is exhaustive over the facet population and holds for every sample of every
population without replaying one.

---

## 3. Q2 — every call site, classified

A site is called SAFE only where the restriction is **exhibited in the code that passes the set**.

### Producers (build the mapping)

| # | site | note |
|---|---|---|
| P1 | `analysis/contrast_fewshot_preanalysis.py:256-263` | the named subject (SLURP `SnapshotBundle`) |
| P2 | `analysis/dev100_damage_channel_analysis.py:205-210` | `LandedInputs`, same construction |
| P3 | `analysis/a2t_admission_scale_sweep.py:854-861` | A2T `cf.SnapshotBundle`, same construction |
| P4 | `analysis/dev500_confirmatory_read.py:693-698` | local dict, same construction |
| P5 | `docs/checks/…/2026-08-25-dev100-retain-override/launcher/…:807-813` | **hash-pinned, untouched** |
| P6 | `docs/checks/…/2026-08-25-dev1000-baseline-lock/launcher/…:649-655` | **hash-pinned, untouched** |

### Consumers (read the mapping)

| # | site | facet set passed | class | reason |
|---|---|---|---|---|
| C1 | `contrast_fewshot_preanalysis.py:717` | `supply.admitted_facet_ids` | **SAFE** | admitted ⊆ NPZ (§2.1); additionally guarded by `recall_scores[…]["content"] is None → continue` |
| C2 | `contrast_fewshot_preanalysis.py:742` | `bundle.facet_ids[index]` | **SAFE** | NPZ ids by construction |
| C3 | `a2t_admission_scale_sweep.py:1582` | `supply.admitted_facet_ids` | **SAFE** | admitted ⊆ NPZ (§2.1) |
| C4 | `a2t_gold_absence_diagnosis.py:246` | `bundle.facet_ids[index]` | **SAFE** | NPZ ids by construction |
| C5 | `a2t_gold_absence_diagnosis.py:284` | `bundle.facet_ids[index]` (τ-passing) | **SAFE** | NPZ ids by construction |
| **C6** | `a2t_gold_absence_diagnosis.py:314-318` | **every key** → `kb_facets_for_gold` | **UNSAFE** | unrestricted `.items()` scan; the reported field is named for content facets |
| **C7** | `a2t_gold_absence_diagnosis.py:340` | **every key** → `kb_shape.content_facets_with_a_task_target` | **UNSAFE** | `len()` of the whole mapping, reported under a content name |
| C8 | `a2t_gold_absence_diagnosis.py:383` | `result.candidates` (**rank candidates**) | **SAFE** | conjunct `"content" in recall_scores.get(facet_id, {})` applies the restriction |
| C9 | `a2t_oracle_query_bound.py:409` | `bundle.facet_ids[index]` | **SAFE** | NPZ ids by construction |
| C10 | `a2t_oracle_query_bound.py:415` | `supply.admitted_facet_ids` | **SAFE** | admitted ⊆ NPZ (§2.1) |
| C11 | `a2t_oracle_query_bound.py:424` | `bundle.facet_ids[index]` (τ-passing) | **SAFE** | NPZ ids by construction |
| C12 | `cross_carrier_ceiling_decomposition.py:638` | `supply.admitted_facet_ids` | **SAFE** | admitted ⊆ NPZ (§2.1) |
| C13 | `dev100_damage_channel_analysis.py:694` | `inputs.facet_vector_ids[index]` | **SAFE** | NPZ ids by construction |
| C14 | `dev100_damage_channel_analysis.py:709` | `recalled_content` | **SAFE** | set is built as `if "content" in scores` |
| C15 | `dev100_damage_channel_analysis.py:712` | `replay.admitted_facet_ids` | **SAFE** | admitted ⊆ NPZ (§2.1) |
| **C16** | `dev100_damage_channel_analysis.py:1106` | `replay.rank_result.candidates[:8]` (**rank candidates**) | **NEEDS-MEASUREMENT** | rank candidates are **not** content-restricted; see §4.3 |
| C17 | `fusion_form_offline_gate.py:512` | `rank_result.candidates` (**rank candidates**) | **SAFE** | explicit `facet_id in content_facet_ids and …` intersection — the repair that found this defect |
| C18 | `fusion_form_offline_gate.py:1413` | `bundle.facet_ids[index]` | **SAFE** | NPZ ids by construction |
| C19 | `k1_hybrid_ranking_gate.py:642` | `bundle.facet_ids[lexical_top1]` | **SAFE** | NPZ ids by construction |
| C20 | `dev500_confirmatory_read.py:709` | `facet_ids` (NPZ order) | **SAFE** | NPZ ids by construction |
| C21 | `contrast_fewshot_preanalysis.py:266-272`, `a2t_admission_scale_sweep.py:864-870` | derived `facet_indices_by_target` | **SAFE** | restricted by `facet_index.get(facet_id) is not None` |
| C22 | frozen launcher `…retain-override…:933`, `…dev1000-baseline-lock…:775` | `top_m` ids | **SAFE** | guarded by `content_score = dim_scores.get("content")`, `if … content_score is None: continue`. **hash-pinned, untouched** |
| C23 | frozen launcher `…retain-override…:815`, `…dev1000-baseline-lock…:657` | derived `facets_by_target` | **SAFE** | restricted by `facet_id in facet_vector_table`. **hash-pinned, untouched** |
| **C24** | frozen launcher `…retain-override…:2697`, `…dev1000-baseline-lock…:2558` | `len()` of the whole mapping in a **log line** reading "*N* content facets carrying a task target" | **UNSAFE (cosmetic)** | mis-states the count in stdout only; §4.4. **hash-pinned, untouched** |

`a2t_lexical_ceiling.content_facet_targets` and its test
(`tests/unit/test_knowledge_build_a2t.py:22,369`) are a **different, correctly restricted**
function and are not defects.

**Three call sites pass rank candidates** — C8, C16, C17. Two of them (C8, C17) apply an explicit
content restriction at the passing site. C16 does not, and is measured below.

---

## 4. Q3 — the measured consequence, both ways

### 4.1 Every admitted-set and NPZ-indexed site: **NIL. Stated plainly.**

**20 of the 24 consumer entries are SAFE.** Nineteen of them (C1–C5, C9–C15, C18–C23) read only
facet ids that are already inside the content-facet NPZ — by construction, by the admitted-set
subset relation of §2.1, or by a `"content" in recall_scores` guard — and §2.1 measures **0**
non-content facets in that set on either carrier. The remaining two (C8, C17) pass unrestricted rank
candidates but apply the content restriction **at the passing site**, by intersection with the
landed content-facet id set or with the content recall scores. **The all-facet reading and the
content-facet-only reading are exact identities at every one of those 20 sites, on every sample of
every population. Nothing changes. That is the whole result at those sites and it is a good one.**

### 4.2 C7 — `kb_shape.content_facets_with_a_task_target`: **the number changes by 302**

| reading | value |
|---|---|
| all-facet (as landed) | **12,903** |
| content-facet-only (correct for the name) | **12,601** |
| difference | **302** (151 label + 151 prior facets) |

The landed 12,903 was reproduced exactly by the all-facet reading before either number was read, so
the two are the same computation under two readings and not two different computations.

### 4.3 C6 — `kb_facets_for_gold` on the 11 case-B rows: **each row changes by exactly 2**

| sample | gold tool | landed (all-facet) | content-only | Δ | landed `kb_vectored_facets_for_gold` |
|---|---|---|---|---|---|
| `tier1_direct:000167` | `setColor` | 167 | 165 | 2 | 165 |
| `tier1_direct:001631` | `setWaterValve` | 177 | 175 | 2 | 175 |
| `tier2_parametric:004826` | `setGroupLightState` | 187 | 185 | 2 | 185 |
| `tier4_implicit:000655` | `setLockState` | 166 | 164 | 2 | 164 |
| `tier4_implicit:000900` | `setGarageDoor` | 152 | 150 | 2 | 150 |
| `tier4_implicit:001148` | `castContent` | 185 | 183 | 2 | 183 |
| `tier4_implicit:001389` | `setApplianceMode` | 146 | 144 | 2 | 144 |
| `tier4_implicit:001409` | `setApplianceMode` | 146 | 144 | 2 | 144 |
| `tier4_implicit:003312` | `startWorkout` | 188 | 186 | 2 | 186 |
| `tier7_multiturn:000214` | `setTargetTemperature` | 191 | 189 | 2 | 189 |
| `tier7_multiturn:001516` | `activateRoutine` | 188 | 186 | 2 | 186 |

Landed range **146–191**; content-only range **144–189**; the difference is **exactly 2 on every
row** — the one label and one prior facet each A2T tool carries. **On all 11 rows the content-only
reading equals the landed `kb_vectored_facets_for_gold` exactly**, which is the independent
corroboration that the 2 removed facets are precisely the two unvectored non-content ones.

**No verdict moves.** `a2t_gold_absence_diagnosis.py:685` classifies BUILD versus RANKING on
`kb_values_for_gold == 0 or kb_vectored_facets_for_gold == 0` and **never reads
`kb_facets_for_gold`**; the population-coverage context (`:727,:730`) reads the same two fields.
The 0 / 11 split, the dominating sub-cause, the 4 / 11 gold-coverage block and every downstream
number are untouched. `kb_facets_for_gold` and `content_facets_with_a_task_target` are descriptive
shape reports and gate nothing.

### 4.4 C16 and C24 — **no landed number exists to change**

C16 (`dev100_damage_channel_analysis.py:1106`) puts `content_facet_target.get(candidate.facet_id)`
into a per-candidate `ranked_candidates` dump under the field name `task_target`. The set is genuinely
unrestricted, so a prior-mass or label candidate inside the top 8 would be given a task target here.
**The dissection report that carries it was never committed** — no file under `docs/` contains
`ranked_candidates`, `dissection` or `reweight_addressable` — and no readiness document quotes a
rank candidate's `task_target`. **Consequence on landed data: none, because nothing landed.** The
field is also not named for content, so it is a latent hazard rather than a mis-statement.

C24 is a **stdout log line** in the two hash-pinned launchers. No committed file carries its
sentence; `logs/` is untracked. **Consequence on landed data: none.**

**Not verified:** whether any *uncommitted* local artifact ever carried C16's or C24's number. Those
bytes are not addressable and no claim is made about them.

---

## 5. Q4 — the landed numbers that change, and the successor correction

Two landed readiness documents state the C7 number. **Neither is edited by this row**, which owns
only its own paths; the correction is landed here as an explicit English successor.

| document | sentence as landed | corrected value |
|---|---|---|
| `docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §1.4, lines 98–99 | "**KB shape** (`kb_shape`): 12,601 values, 12,601 vectored content facets, **12,903 content facets carrying a task target**, 151 distinct value targets against a 151-entry label vocabulary." | **12,601** content facets carry a task target. 12,903 is the count of **all facets of any dimension** carrying one (12,601 content + 151 label + 151 prior). |
| `docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §2, line 125 | "Per-tool KB depth for the 11 … : **144–189 values**, **146–191 content facets** and **144–189 of those facets vectored**" | **144–189 content facets**, all of them vectored. 146–191 counts each tool's label and prior facet as well. |
| `docs/readiness/2026-08-25-a2t-oracle-query-bound.md` §1.5, line 123 | "**KB shape:** 12,601 values, 12,601 vectored content facets, **12,903 content facets carrying a task target**, 151 distinct value targets against a 151-entry label vocabulary." | **12,601**, as above. |

The two sealed receipts carrying the same field —
`docs/checks/…/2026-08-25-a2t-gold-absence/diagnosis-report.json` (sha256
`64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14`) and
`docs/checks/…/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json` (sha256
`b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723`) — are **hash-pinned and are not
touched**. This section is their English successor.

**Who should carry the in-document correction:** the rows that own those two documents,
`SAEA-SN-MF-A2T-GOLD-ABSENCE-DIAGNOSIS` and `SAEA-SN-MF-A2T-ORACLE-QUERY-BOUND`. Neither correction
changes a verdict, a split, an effect size or a recommendation in either document (§4.3).

**No SLURP-side landed number changes.** No committed document or receipt reports
`len(content_facet_target)` for the SLURP carrier; its 11,785-against-11,514 split is measured here
for the first time. Nothing computed here revises, re-tunes or restates **the lock**, which stands
exactly as landed at `d9fef537`; anything read over the SLURP unexposed 500 is a **secondary
reading** on the locked baseline's own population.

---

## 6. What this row did NOT do

- **No repair, and no repair design.** The name/behaviour mismatch at P1–P6 stands as found. A fix
  is a separately registered step.
- **No docstring correction.** No *mutable* docstring was proven wrong: `SnapshotBundle` and
  `LandedInputs` document the bundle, not the field, and carry no claim about the field's keys;
  `SampleGeometry.gold_facet_position`'s comment is accurate; `a2t_lexical_ceiling.content_facet_targets`'s
  docstring is accurate because that function does filter. The one docstring that *is* wrong —
  `DeltaSignalTable`'s "`content_facet_target` maps a content facet id to …" — exists only inside the
  two **hash-pinned** frozen launchers and must not be rewritten in place. This paragraph is its
  successor.
- **No knob, no `rails/`, `core/` or `configs/` write, no snapshot rebuild, no receipt displacement,
  no re-flight, no new sample, no gold surface.**
- **No conclusion beyond what was measured.** In particular: the audit measures the mapping's keys
  and the sets each call site passes; it does not claim anything about carriers, snapshots or
  populations other than the two pinned snapshots named above.
