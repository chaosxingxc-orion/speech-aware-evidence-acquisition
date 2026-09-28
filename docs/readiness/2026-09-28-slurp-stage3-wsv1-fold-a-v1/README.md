# W-SV-1 (TRAIN Fold A, same-flight supply-variant KNOB cell) -- registration BLOCKED

Status: BLOCKED_ON_PROGRAM_FRAGMENT (2026-09-28). Nothing registered, no configs, no plans,
no ledger rows, no model contact. This note records the finding the coordinator ruling (owner
decision 172) asked for before any registration work.

## Question

The cell's base is the AGREE arm bytes
(`configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json`), whose program is
`phase-native-candidates-review-revise-v1` (`max_contacts` 11; the Solver phase declares
`response_format_id: null`, i.e. UNCITED). Adding a Solver `supply_variants` group with
`arm_visits: "first"` and K arms raises the bounded graph ceiling to 11 + (K - 1)
(`rails/native_episode_config.py`, item E42b), and the loader refuses any program whose
`max_contacts` differs from that ceiling (`program contact ceiling must equal the bounded
native graph ceiling`; `allow_subceiling` is set only by `rails/system_policy_catalog.py`,
never on the flight path). So the cell needs an UNCITED program with `max_contacts` 13
(A + B + twin T) or 12 (A + B, twin dropped).

## Finding (from the code at e0e1ed28)

| program id | max_contacts | Solver response_format_id | usable for W-SV-1 |
|---|---|---|---|
| `phase-native-candidates-review-revise-v1` (base) | 11 | null | no arm group |
| `phase-native-candidates-review-revise-cited-variants2first-v1` | 12 | `saea-solver-cited-answer-v1` | no: cited |
| `phase-native-candidates-review-revise-cited-variants3first-v1` | 13 | `saea-solver-cited-answer-v1` | no: cited |
| `phase-native-candidates-review-revise-variants4-v1` | 17 | null | no: equals the "every" ceiling for K = 4 (1 + 2 x (4 + 3 + 1)); under "first" K = 4 gives 14 != 17 |

Both "first" fragments differ from the base fragment ONLY in `program_id`, `max_contacts` and the
Solver phase's `response_format_id` (verified by a key-sorted JSON diff). Using either would change
the Solver's answer contract (cited envelope plus a cited-answer normaliser), which is not an
`phase_supply.<phase>.{k, fuse_coverage.*}` / `candidate_supply.<phase>.max_candidates` knob and
would break the AGREE-bytes base. No branch ahead of master carries an uncited "first" fragment.

## Engineering item needed (owned by another agent)

1. `configs/policy/phase-native-candidates-review-revise-variants3first-v1.json` -- a byte copy of
   `phase-native-candidates-review-revise-v1.json` with `program_id` renamed and
   `max_contacts: 13` (Solver `response_format_id` stays null).
2. Optionally `...-variants2first-v1.json` the same way with `max_contacts: 12`.
3. In `src/speech_aware_evidence_acquisition/rails/controllers.py`: a `PHASE_PROGRAM_FILES`-style
   map entry beside the `cited-variants{2,3}first` entries (around line 1520), plus the matching
   `AGENT_CONTROLLERS.register(...)` block beside lines 1816-1832, and a `core.base` policy
   registry entry if the policy registry is keyed separately (engineering_base_check requires every
   `policy` value in `configs/` to resolve).

Once item 1 lands on master, W-SV-1 registers as ruled: three arms under "first" (A = base Solver
train-exemplar supply k 20, B = train-exemplars k 30 per the VAR-1 `exk30` construction, T =
`replicate_of: A`), ceiling 13.
