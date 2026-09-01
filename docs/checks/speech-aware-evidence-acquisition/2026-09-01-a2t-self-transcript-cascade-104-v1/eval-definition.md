# Frozen evaluation definition

Experiment: `SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1`.
Status: frozen before implementation. The 104-contact OBS phase has flown; gold and the scorer
remain closed, and only the separately registered bounded recovery may continue.

## Evaluation questions

1. **Observation liveness:** Does the ASR-only same-core contact create a structurally valid,
   diverse English observation and a positive deterministic route for almost every sample?
2. **Information gain:** Does matched retrieval outperform both frozen one-call M0 and the
   equal-budget shuffled-evidence control?
3. **Agent gain:** Does the complete observation/retrieval/evidence/use loop improve the official
   task outcome over a single frozen-core call?
4. **Training-free contribution:** Does the preregistered cross-fitted controller improve over M0,
   match or exceed always-use gain, and use fewer final contacts without any harmful selection?
5. **Measurement integrity:** Is the claimed gain larger than byte-identical resend variation, and
   do concurrent whole-manifest scorer jobs preserve authoritative identities and metrics?

## Evals that implementation must pass before contact

| ID | Capability or regression | Required behavior |
|---|---|---|
| E01 | ASR prompt isolation | The observation request contains the frozen English ASR-only instruction, original speech, and no registry, knowledge, M0 output, task-answer schema, reference transcript, label, or score. |
| E02 | English context gate | Accept only the frozen one-line ASCII/English-like grammar; reject empty, non-ASCII, JSON, fenced code, role-prefixed, tool-call, commentary, refusal, and overlength outputs; rejected bytes cannot be rendered into a later context. |
| E03 | Phase barrier | USE launch hard-fails unless all 104 observation rows are sealed and every conjunctive label-free liveness threshold passes; no gold or score field is accepted by the gate. |
| E04 | Deterministic BM25 | Byte-identical query/snapshot inputs yield identical positive rankings under `k1=1.5`, `b=0.75`; source order and ASCII whitespace changes preserve the canonical result. |
| E05 | Evidence budget | Rendering is limited to five facets, six values, and five distinct targets and contains only the frozen knowledge snapshot and registry identities. |
| E06 | Shuffled control | Assignment is tier-local, total, deterministic, bijective, and a derangement; final AgentState always contains the recipient transcript while only retrieval uses the donor transcript. |
| E07 | Runtime state safety | State contains only frozen structural buckets and no literal transcript/token/tool/facet/value/domain/category/sample/tier/donor/fold/gold/reward/response data. |
| E08 | Grouped cross-fitting | Every query group belongs to one fold; each decision reads returns from other folds only; a cell needs support four, saves two, harms zero; unmatched cells stop at M0. |
| E09 | Contact accounting | Observation, matched, shuffled, resend, and canary contacts cannot exceed 104, 104, 104, 16, and 6 respectively or 334 cumulatively; liveness failure permits no later contact. |
| E10 | Exact replay | Every resend payload hash equals its matched source payload hash while the new attempt retains separate trace and accounting identities. |
| E11 | Complete composites | Matched, shuffled, resend, and policy artifacts each contain exactly the frozen 104 unique sample ids; unavailable rows cite frozen M0 and no output is invented. |
| E12 | Outer parallel scoring | Wave 1 has exactly three unique complete manifests and three workers; each job invokes the unchanged scorer once in one process; shard manifests and shard-metric averaging are rejected. |
| E13 | Score equivalence | Each concurrent result is verified, binds the expected full-manifest identity, and is byte-equivalent to the authoritative single-job result for the same manifest after nonsemantic timing fields are excluded. |
| E13a | Model-free derivative scoring | Wave 2 scores one complete 104-row policy derivative after wave-1 finalization; it reuses the finalized matched-attempt identity without reopening or mutating an attempt. |
| E14 | Promotion conjunction | A report cannot pass unless every liveness, matched-information, agent-gain, training-free, fold, secondary-metric, resend, and state-liveness gate in the machine contract passes. |
| E15 | Terminal scope | Failure authorizes no support or scale; success authorizes only a separately registered approximately-104 support proposal; no test, approximately-1,000, Stage-3, or paper-scale execution starts here. |
| E16 | OBS abort recovery | Recovery accepts only the fixed 104-call `ABORTED` OBS source, verifies output-to-trace hashes and absence of sibling spend, performs zero new OBS contacts, closes the authoritative trace before the fallback trace, and preserves the cumulative 334-call ceiling. |
| E17 | USE abort recovery | Recovery accepts only the fixed complete matched and shuffled bundles and their 104-call `ABORTED` records, creates zero-call source-bound complete derivatives, ignores non-request rows while extracting the exact 16 resend payloads, performs no repeated USE contact, and leaves three whole-manifest outer-parallel finalization jobs. |

## Coverage and execution rule

Write these tests before implementation, observe their relevant failures, then implement the
smallest code that passes them. Targeted branch coverage over the new observation, retrieval,
barrier, derangement, policy, bundle, and scoring-plan modules must be at least 80%. Run the full
repository suite and lint checks before committing the implementation.

No statistical result may be opened while repairing a failed capability test. A protocol-changing
repair requires a new preregistered hash and a fresh one-shot attempt identity.
