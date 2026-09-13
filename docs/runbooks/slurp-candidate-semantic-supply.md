# SLURP candidate-conditioned semantic supply

The shared named-store path can supply explanatory slot cards from a model's
ranked SLURP intent hypotheses. The source phase must seal
`saea-slurp-intent-hypotheses-v1` state. The shared controller then selects the
released cards before dispatching the later solver phase; the solver receives
them as ordinary traced knowledge on its `QueryState`. This path grants no
analytical tool authority.

Use this store declaration under the experiment configuration. The numbers
shown are an example bounded dose; the experiment registration must set and
pin its chosen per-candidate and total limits.

```json
{
  "knowledge_stores": {
    "slot-contracts": {
      "store_role": "slot-contracts",
      "snapshot": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v1/snapshot.json",
        "sha256": "11c246e4b815a4f966e8cf8785f06b70515755eca71658862c6f98e9914044e6"
      },
      "release": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v1/release.json",
        "sha256": "8a29c48bfc5aed2eb27ce38073252d3fc608c9102aa8b8095a072667289b4f3e"
      },
      "candidate_supply": {
        "solve": {
          "provider": "slurp-candidate-semantic-v1",
          "rank_policy": "saea-ranked-candidate-round-robin-v1",
          "fuse_policy": "saea-candidate-semantic-passthrough-v1",
          "candidate_state_phase": "hypotheses",
          "max_candidates": 3,
          "max_values_per_candidate": 2,
          "max_total_values": 6
        }
      }
    }
  }
}
```

The snapshot pin is its semantic SHA-256. The snapshot file bytes have SHA-256
`0de5418caaf8642bfabc402a64d228d77ae76d57b23c0d23caf24164fcf0d37a`.
The release owns and pins the authored source at
`prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json`
with SHA-256
`34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5`.
Runtime re-hashes that source, rebuilds the complete 54-card snapshot, and
requires exact semantic equality with the released snapshot before it derives
the candidate index. No separately configured index or unbound text is read.

Selection follows model rank. Values are ordered by their released IDs within
each candidate, then selected one per candidate per round. A card shared by
several candidates is emitted once and attributed to the first ranked
candidate that reaches it. `max_values_per_candidate` bounds each candidate;
`max_total_values` bounds the whole solver dose. The latter cannot exceed
`max_candidates * max_values_per_candidate`. These rules are deterministic
and prevent a 54-card catalog dump.

Candidate validity comes from the SLURP adapter's authoritative task-contract
provider. The complete legal label and slot-type inventory remains in the task
contract. The slot-card source contributes explanatory values and observed
intent bindings only as lookup keys. A missing or sparse binding never marks a
slot required, optional, forbidden, or illegal.

The runtime records the source state identity and hash, ordered candidate IDs,
each candidate's mapped, selected, and ignored value IDs, explicit absent
mappings, cap-related omission reasons, qualified store IDs, the store source,
snapshot, release, and composite hashes, and a selection hash. It preserves
one or two candidates as one or two; it never fills the list to three. It
refuses duplicate, unknown, malformed, or more-than-configured candidates,
missing or ambiguous source-phase state, a non-later/non-supplied target
phase, unknown configuration fields, changed release content, and index IDs
outside the authoritative legal inventory or released snapshot.

An all-absent mapping records the decision and supplies no card. The solver
still retains the full task contract. The mechanism does not decide the
intent, infer slot values, enforce slot presence, or introduce a fallback
candidate. It performs no preparation release, model contact, scoring, or
experiment execution.

## Native compact state and repeated Solver visits

Set `compact_source_phase` to the same phase as `candidate_state_phase` only
when the source is the native compact `{candidates}` response. The omitted
default still requires a canonical document with its sample identity. Compact
consumption verifies the raw response hash, phase kind, and shared-sealer
phase/sample state ID before using the existing canonicalizer. It never repairs
IDs, fills missing candidates, removes duplicates, or rewrites sealed bytes.

Record each supply decision by target phase, sample, and exact query-state hash.
A Solver revision that already sees the entire selected card set retains it
with an `already-visible` receipt and no new acquisition. Refuse partial overlap;
do not refill from later cards on each revision. This preserves the configured
knowledge dose across the bounded episode.

Keep the common task instruction role-neutral. Use the role's own output
contract; in particular, Perception emits complete scenario_action candidate
IDs and only Solver emits final scenario/action/entity JSON. Do not attach a
Perception-only state fill to a Solver's immediate predecessor: on revision,
that predecessor is Planner. Candidate supply selects the configured Perception
source from the source-bound trajectory instead.

## Matched withheld control

Set candidate_supply.<phase>.supply_mode to withhold to validate the same
source-bound candidates and compute the same card selection without making an
acquisition. Keep the same released store and other limits in the control and
supplied arms. The selection receipt records withheld; selected IDs are audit
metadata and are not added to the query state. Refuse a control whose selected
cards are already visible. Omitted mode retains provide and the historical
receipt shape. This switch isolates model-facing knowledge availability while
preserving source validation and selection failure behavior.


## Bounded candidate projection

Opt into `projection_policy: bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`
only in a prospectively registered compact-source experiment. Validate every original
candidate object and its source phase/sample/hash before projecting. Accept one
through three raw candidates; retain the first occurrence of each legal intent in
original order without padding. Preserve original model responses and record the
projected content hash, policy hash and every raw position in the selection receipt.
Actual width is descriptive, not confidence. The historical fixed-three policy
and strict default parser retain their identities and behavior.

Use the same projection policy in a supplied arm and its withheld control. This
projection changes only the knowledge lookup view; the original Perception message
remains in native framework history. Do not manufacture a replacement source state.
