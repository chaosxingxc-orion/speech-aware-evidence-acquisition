# Native candidate request rejection: root-cause repair

Date: 2026-09-14.

The bounded-evidence TRAIN A campaign stopped after 202 generation contacts. A
Reviewer requested an unknown legal candidate ID. The candidate dispatcher
raised an input error before creating its source-bound tool observation.
OpenJiuwen continued with a tool error message, but the shared speech bridge
still held the original pending call and refused the next request. Root reproduced
this exact failure through the actual framework using synthetic responses.

Keep input validation. For a source-valid, schema-valid candidate request whose
IDs are outside the legal catalog, count the analytical invocation and return
source-bound rejection feedback before any candidate lookup. Preserve the
original assistant response and exact arguments. Keep the existing role/contact
limits, legal catalog, candidate width, knowledge, model, prompts and final-answer
authority. Do not catch source, schema, custody, or execution failures as usable
evidence. Historical non-episode rejection behavior stays unchanged.

The post-seal reader verifies this feedback using the same source authority and
request-history projection as successful tool results. Report rejection exposure
separately; never count it as successful evidence supply.

Root verification: 208 focused tests passed, with three existing third-party
deprecation warnings. Ruff, engineering-base and diff checks passed. Tests cover
the actual native loop, exact history, legacy behavior, finite outcomes, CPU
scheduling, post-seal diagnostics and provisional materialization. All proof
responses were synthetic; no real model, fit, ASR or GPU contact occurred.

Proof: DATA/coordination/native-tool-error-observation-v1/root-proof-v1.json.

The engineering fix does not resume the failed attempt. Any sole recovery must
receive a new root registration, source freeze, prepared-supply verification,
service/lease validation and event observer. A second failure closes this flight.
Do not reopen either older candidate-refresh/tools attempt, read partial task
quality, splice incomplete outputs, or contact Fold B.
