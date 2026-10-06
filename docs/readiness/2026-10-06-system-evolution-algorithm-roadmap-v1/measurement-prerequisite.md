# Measurement prerequisite for the prospective algorithm contrast

Status: prospective design only; no new GPU or actor admission.

The qualified Update6 original-a seed/A/A audit observes differences even for some
matching actual-request FIT body hashes, explicit slots, temperature0 and fixed seed.
The frozen transport forwards these parameters. Do not interpret this as proof that
the task is at a local optimum, that the seed is omitted, or that cache eviction is
causal. Match the full uncertainty of the measurement to any proposed selection rule.

The inspected local llama.cpp tools/server/README.md at commit
04ccc72a2207347ca76161b93fd9d846dd0a8675 documents that cache_prompt can produce
nondeterministic results because different backend batch sizes need not produce
bit-identical logits. This is a documented possible mechanism, not a diagnosis of
our observed differences. Equal reported cached-token counts do not establish equal
KV contents or numerical paths. Preserve the current frozen requests and serving.

After completing the already registered Update6 population, review the cohort-local
A/A evidence before admitting an algorithm contrast. A point-estimate gain smaller
than observed repeatability variation may still be useful for exploration, but cannot
by itself justify formal adoption or a feedback-learning claim. Use paired complete
system outcomes and the existing registered measurement rules, with comparable rosters
and explicit uncertainty. Do not invent a new fixed threshold retrospectively.

If uncertainty prevents interpretation, prospectively register a bounded same-policy
repeatability probe. Freeze the input roster, complete system text, sampling and
output limits. Change one declared execution factor at a time, such as admitted
request concurrency or cache reuse, while recording actual body/response hashes,
slot identity, overlap and prefill/cache counters. Keep task quality and reproducibility
separate; differing text is not necessarily a different task decision. Budget the
probe separately and preserve every run. No server restart, cache flush, geometry
change, data rebuild or model contact follows from this design note.

Algorithm development can proceed model-free meanwhile, but proposed selector or
experience changes must not relabel noise as learning. Keep selection exploration
and formal incumbent adoption separate, and test feedback value with an isolated
budget-matched comparison when the measurement can support that question.
