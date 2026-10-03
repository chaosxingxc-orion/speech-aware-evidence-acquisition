# Optional native node prefix affinity: flight binding

Status: model-free engineering verified; no GPU admission or performance claim.
Authority: the owner's explicit node-prefix request and bounded engineering decision 227.

The existing FlightRuntime now accepts `native_prefix_slots` as a separately
versioned execution factor. It binds the actual native phase identifiers to
distinct slots, validates them against the serving geometry before preparation,
and publishes the same mapping in its dispatch receipt. Every contact still uses
the shared request composer, capacity gate, OpenJiuwen graph and frozen Omni
answer authority. This is not a new inference stack or an optimizer-editable
policy field.

Example for a four-role program (use its actual phase identifiers):

```json
{
  "native_prefix_slots": {
    "schema": "saea-native-prefix-slots-v1",
    "role_slots": {
      "perception": 0,
      "solver": 1,
      "reviewer": 2,
      "planner": 3
    }
  }
}
```

The map covers every model-contact role. A model-free acquisition needs no
model slot; a model-backed acquisition does. A declared post-delivery relisten
requires its own slot. Missing roles, extra roles, slot aliases, invalid types
and out-of-geometry values are refused before contact. Whole-policy selection
must preserve this envelope and each selected policy must remain compatible.
Tool continuations retain the invoking role's slot; separately scheduled CPU
tools retain their existing bounded executor.

Context cleaning is currently refused when this factor is armed. Its existing
model call runs during input construction outside the contact scheduler. It was
protected by trajectory slot ownership, which does not protect a role-owned
slot. Do not bypass the refusal; registering support requires moving that
contact through the same scheduler and proving its prefix identity separately.

Absence of the key retains trajectory affinity and omits the new receipt key.
The immutable native policy dataclass is unchanged, so an absent factor does not
alter historical whole-policy hashes. Armed scheduling changes request slot
fields and therefore their hashes; it does not change the request's model-visible
messages, tools or output authority in the synthetic comparisons.

## Verification

- Tests were introduced failing before implementation. The relevant 179-test
  suite passes, covering actual FlightRuntime/native/OpenJiuwen composition,
  revisions, tools, legacy dispatch, cancellation, whole-policy selection and
  existing Audio2Tool/Earnings integration fixtures. The final whole-policy
  compatibility refinement additionally passes six focused tests.
- All 30 new binding tests pass. The scheduling configuration module has 100%
  statement coverage (77 statements); this is not a whole-runtime coverage claim.
- Engineering-base, harness-admission, changed-file lint and diff checks pass.
- Zero real model, tokenizer, proposal or scorer contacts. Tests use scripted
  transport responses and do not contact the resident model service.

## Remaining experiment

No committed experiment configuration enables this factor. Keep active/frozen
workers and the four-slot serving geometry unchanged. First prospectively
register exact capacity and structural proofs; then compare identical frozen
policy content under trajectory and role affinity, using complete families and
their proper read authority. Report per-role reused/evaluated tokens, queue wait,
prefill/generation time, full trajectory completion and wall time. Retain A/A and
the existing measurement rules for any scientific quality conclusion.

Role affinity does not guarantee a prefix cache hit. Audio, tools, role text and
template serialization can still change the exact prefix. Across-role reuse may
fall even if each node's own prefix persists longer. The preceding qualified
round5 cache audit is descriptive, not evidence that this schedule is faster.
Do not promote the factor or mix its cost effect into the next proposer protocol
without its own registered comparison.

The SLURP heartbeat stays PAUSED. Independent ten-second telemetry remains
unchanged. Root reviews each bounded stage and returns to the human before 8x400.
