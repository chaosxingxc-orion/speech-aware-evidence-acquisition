# Audio2Tool G4 executable-microground screen 16 v1 preregistration

Date: 2026-09-02. Status: **REGISTERED; ZERO CONTACT; MODEL CONTACT CLOSED**. Experiment:
`SAEA-A2T-G4-EXECUTABLE-MICROGROUND-SCREEN-16-V1`. Execution profile:
`bounded-discovery-probe`. Experiment config SHA-256 is
`926bbbb0c90b70df7877dfd4c72248e09c56007d85180c5b9b23ec664263c04a`; baseline config SHA-256 is
`dd7f38fe941d1c6ece607ff695f0ab700a9aea2c75fd5808674ceba8119820e5`; roster receipt SHA-256 is
`41a14ab576d7a428dd9849f26432e2c4998371b9f601189a1d558d694a12c884`.

## Objective and roster

G3 reached only 8/40 exact with the matched broad 32-card ground although its detailed cards
contained the gold tool for 37/40 rows. G4 therefore tests whether a small executable semantic
ground makes tool choice and argument realization usable before any candidate pruning, scale, or
training-free control. This is a small discovery screen, not confirmation or a paper-scale result.

The identity-only receipt derives the same two-per-tier selected16 used by the G3 deterministic
shuffled control, using namespace `a2t-g3-shuffled-control-v1` and no query text, gold, response,
score, reward, or test information. Selected16 has split/run hashes
`7590dfef54b42601c266f2bb325faee073143a575beeccd0c33cc8baf13aed45` and
`f9e3055f7eceff49405a192806be933db9bfcab150a1778bb3ddd937a8f57269`. Its fixed complement has 24
rows and split/run hashes `a369a15f8abc1c03b70d41286776d757aac7677a81c402521512c38123e2a9f4` and
`c55dad2d4050811cd5537f02a112b825112ed0cdcd6b9d85be078973895ac8cf`. The fresh 88, test, future
turns, and every TFRL evaluation surface remain closed.

## Frozen Stage-1 contrast

`C` is the sealed G3 matched result on selected16: 2/16 exact and 11/16 correct tool. It receives
zero new contact. Any further C metric is an identity-filtered read of its sealed official score
artifact, never a model recontact.

`E` makes one request for each selected row using original speech, its existing sealed task-blind
English observation, and a new deterministic semantic microground. `SE` makes one request for each
same row using original speech, a prevalidated structured dialogue state, and the identical
microground policy and corpus. This registration authorizes no structured-state generation contact.

The router queries once per active action over choose semantics, avoid/contrast semantics, role
guidance, and tool/category facets. Frozen BM25 retains the top two cards per action plus the best
sibling contrast or schema-compatible alternative, then unions two through eight registered
candidates while preserving every action's top candidate. The packet renders only those cards and
four task cards. Tier, sample identity, gold, references, reward, prior outcomes, future turns, and
synthetic example literals are forbidden query features. Fixed ties, ranks, scores, reasons,
candidate names, and packet/trace SHA-256 values must be recorded.

The three registered mechanism contrasts are E-C, SE-E, and SE-C, with paired exact/tool
wins, losses, ties, and net changes. Because there is no state-only arm, this is a staged mechanism
decomposition, not a complete two-by-two factorial; no interaction estimate may be claimed.

## Gates and extension

Each new arm passes Stage 1 only if all of these hold on its complete 16-row official score:

- parse at least 15/16, exact at least 15/16, correct tool 16/16, and slot micro-F1 at least 0.90;
- zero out-of-registry names and zero synthetic-example literal copies; and
- paired exact wins minus losses versus C is strictly positive.

The registry-name, legal-key, parse, and example-copy checks are useful structural diagnostics but
never replace the official score gate. Both new-arm manifests must seal before gold opens.

If neither arm passes, remainder24 stays closed. If exactly one passes, only it extends. If both
pass, exactly one extends by higher exact count, then higher slot micro-F1, parse count, and paired
exact net gain; a complete tie selects E as the lower-complexity arm. The same frozen method runs on
the fixed remainder24. The combined 40-row arm qualifies only at exact at least 36/40, correct tool
at least 38/40, slot micro-F1 at least 0.90, parse at least 39/40, and exact at least 4/5 in every
tier. No result may retune the router, state, prompt, threshold, or cohort.

## Execution and scoring

Freeze two model slots, at most two concurrent requests, queue depth four, state at most 4,096 ASCII
bytes, microground packet at most 16,384 ASCII bytes, prompt at most 8,192 tokens, and completion at
most 1,024 tokens. Temperature is zero and seed is 20260803. Each row gets one contact with no
repair, retry, resend, or network-jitter experiment. Stage 1 expects 32 contacts and 356.25
speech-audio seconds. A qualifying extension adds 24 contacts and 198.916375 seconds; the plan
ceiling is 56 calls, 556 audio seconds, 0.4 GPU hours, and zero paid API, embedding, or tokenizer
contact.

Official scoring consumes whole manifests only. E and SE may finalize through two outer workers;
the one possible full-40 composite is one indivisible official job. Dataset sharding, shard score
averaging, and parallel scoring within a manifest are forbidden.

Model contact remains closed until the semantic corpus and build-receipt hashes, sealed observation
and validated-state bindings, composed config and protocol hashes, prompt-fit report, structured
ExecutionPlan, clean commit, and amended pre-contact exposure binding all exist and verify. This
zero-contact registration prospectively supersedes the dormant
`SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1` full-handbook flight without rewriting its bytes or
history. Failure opens no remaining24, fresh88, test, pruning, TFRL, scale, Stage-3, or paper work.
