# Qualified original-a sampling parameter source audit

This is a root-only supplement to the completed original-a repeatability audit.
No new model/scorer contact, active-family quality read, learner export, runtime
change or retrospective acceptance change occurred.

The qualified original-a sources were rechecked against their preserved hashes.
All116 seed and131 A/A requests carry temperature0 and seed20260913. No request
specifies n or n_cmpl in its decoding parameters. The frozen original-a transport
bytes match the inspected source: decoding parameters are copied into the rendered
body; the same renderer supplies the body serialized for POST. Actual-request FIT
hashes remain pre-send evidence, not a network packet capture.

The local serving source is llama.cpp commit
04ccc72a2207347ca76161b93fd9d846dd0a8675. Its schema binds temperature and seed to
sampling parameters. The server initializes each task sampler from those parameters.
The CPU zero-temperature implementation keeps only the highest-logit candidate;
the backend path uses argmax. These source facts do not establish identical logits,
KV state or numerical execution across requests.

The inspected child-task seed offset is conditional on n_cmpl greater than one.
The task default is1 and the audited decoding parameters do not request multiple
completions. This inspection provides no evidence for child-seed offsets as the
observed cause. It does not substitute for capturing effective server-side parameters.

The immediate conclusion is narrower than a reproducibility guarantee: omission of
temperature/seed by the inspected transport is not supported by the evidence.
The cause of equal-body response differences remains UNESTABLISHED. Do not change
current admitted serving geometry, cache state, sampling or candidate contents.
Any controlled repeatability probe needs prospective identities, source custody and
bounded contact registration after the current admitted cohort settles.

Evidence: coordination/update6-original-a-repeatability-audit-v1/sampling-source-audit-v1.json
under SPEECHRL_DATA_DIR. It binds the qualified request audit and six source hashes.
