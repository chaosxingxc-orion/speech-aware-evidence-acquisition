# G6 fixed16 post-seal result analysis

## Decision

G6 fails the fixed16 ground gate. Keep the disjoint 40, 100, 1,000, fresh88,
test, pruning, and training-free reward-guided control surfaces closed. Do not
recontact these rows.

The immediate observed failure is before final evidence use: the sealed SCAN
surface contains no applicable report and no nomination, so no contract reaches
RESOLVE. The raw traces show that this is a mixture of strict-schema rejection
and semantic abstention, not 448 empty model responses. A construction-only
successor should replace the ambiguous free-form SCAN report with a
contract-identity-anchored, mechanically renderable report and improve
candidate-local contrast descriptions. It must use a new identity-only roster
and a new preregistration. A parser-only successor is not sufficient because
the diagnostic name-recovery ceiling covers only 10/16 rows, below the 15/16
exact gate even before argument realization.

## Score result

The unchanged official scorer was run once outside this analysis after the
complete seal. Its reported aggregate is exactly reproduced by the
official-equivalent in-process parser and item-score reconstruction in
[`analysis.json`](./analysis.json). This analysis did not launch the official
scorer, contact a model, contact a service, read audio, or mutate any sealed
artifact.

| System | Tool correct | Exact | Slot P / R / F1 | Parsed JSON |
|---|---:|---:|---:|---:|
| G6 exhaustive family sweep | 0/16 | 0/16 | 0.0000 / 0.0000 / 0.0000 | 16/16 |
| Frozen G1 M0, same 16 IDs | 6/16 | 3/16 | 0.2286 / 0.3810 / 0.2857 | 15/16 |

G6 has 0 exact wins, 3 exact losses, and 13 exact ties against same-roster M0.
For tool accuracy it has 0 wins, 6 losses, and 10 ties. For row-level slot F1
it has 0 wins, 6 losses, and 10 ties. G6 predicts zero calls and therefore zero
predicted slots against 21 expected slots.

Every tier has 0/2 G6 tool accuracy and 0/2 exact match. The same-roster M0
successes are concentrated as follows: tier3 has 1/2 tool correct, tier4 has
1/2 tool correct, tier5 has 2/2 tool correct and 2/2 exact, tier6 has 1/2 tool
correct, and tier7 has 1/2 tool correct and 1/2 exact. The remaining M0 tier
tool and exact counts are zero. Tier8 contains M0's only parse failure.

G5 is not a paired comparator because its fixed16 identity roster differs from
G6. As a descriptive cross-roster reference only, G5 obtained 4/16 tool
correct, 3/16 exact, and 0.1702 slot micro-F1. G6 therefore does not preserve
the earlier G5 ground signal, but the different identities prohibit a paired
progression claim.

## Sealed funnel

The official runtime funnel is:

1. All 448 planned SCAN contacts and all 16 planned RESOLVE contacts have
   nonempty recorded response text.
2. The strict SCAN parser accepts 314/448 reports and seals 134/448 as
   `INVALID_EMPTY`.
3. Every one of the 314 accepted reports is an abstention. Official counts are
   0 applicable reports and 0 candidate nominations.
4. At least one gold-family report is invalid on 12/16 rows. All gold-family
   reports are valid on the other 4/16 rows, but each is a valid abstention.
   Gold-family applicability coverage is therefore 0/16.
5. Selected-contract coverage is 0/16, and the selected contract list is empty
   on every row.
6. Every raw RESOLVE response is a nonempty JSON call array: 20 raw calls over
   16 rows. None of the 20 raw names is an exact registered tool name. More
   decisively, no name can satisfy the runtime candidate constraint because no
   SCAN nomination exists. All 16 resolutions are invalid and seal to the
   canonical `[]` fallback.
7. The scorer correctly treats each final `[]` as parsed JSON, but it contains
   no predicted calls. Parse 16/16 is therefore not evidence of resolver or
   registry validity.

Under the fixed bottleneck precedence, 12 rows are classified as
`scan-invalid-gold-family` and 4 as `scan-missed-gold-family`. No row reaches a
meaningful selected-contract or evidence-bound resolver test. The zero score
must not be attributed to argument realization or treated as evidence that a
resolver supplied with correct contracts would fail.

## Raw-response shape diagnostic

The two immutable transport traces contain exactly 1,392 records: one request,
one nonempty response, and one cost record for each of 464 contacts. The
read-only diagnostic preserves the official invalid/empty fallback decisions.
It does not repair or rescore G6.

| Raw SCAN outcome or rejected shape | Count |
|---|---:|
| Accepted abstention | 314 |
| `ordering_evidence` is an object rather than a list | 67 |
| Candidate key set differs from the literal schema | 41 |
| JSON code fence | 17 |
| JSON syntax or top-level object invalid | 7 |
| Another evidence field has the wrong type | 2 |
| **Total** | **448** |

The candidate-key failures include the model following the prompt's prose
phrase “ordered speech_spans” as a key, while the frozen parser requires the
literal key `speech_spans`. This is construction-interface evidence, not a
license to retroactively relax G6.

Across the rejected raw reports, 46 family reports say they are applicable and
contain 65 candidate rows. Sixty of those candidate names are exact registered
tools belonging to the supplied family; five are not. If analysis extracts
only exact registered family-local names while ignoring every other invalid
field, all gold families are marked applicable and every gold tool is named on
10/16 rows. Those ten rows are:

- `tier1_direct:004159`
- `tier2_parametric:001004`
- `tier2_parametric:002653`
- `tier3_multi_intent:003058`
- `tier4_implicit:001010`
- `tier5_needle:001458`
- `tier5_needle:004242`
- `tier6_correction:001764`
- `tier6_correction:002430`
- `tier7_multiturn:000440`

This 10/16 result is a nomination-only diagnostic ceiling. It does not show
that the malformed evidence bindings are usable, that RESOLVE would retain the
tools, or that any row would score exact. The remaining 6/16 rows lack complete
gold nomination even under this permissive name extraction, which separates a
semantic recognition deficit from the strict-schema loss.

## Successor recommendation

Use one new construction-only successor, not a G6 retry. Preserve the frozen
core, exhaustive family access, corpus identity, zero training, and final
answer authority. Change the SCAN interface so the controller renders the
allowed contract identities and literal field skeleton mechanically, and the
model supplies only bounded applicability and speech-evidence values. Avoid
free-form re-emission of key names and tool names. Keep task values
speech-bound and keep unselected contracts out of RESOLVE.

The successor must also strengthen candidate-local semantic contrast inside a
family. A pure tolerance change could recover at most the observed 10/16
complete gold nominations and cannot meet the 15/16 fixed16 exact requirement.
After the new scan representation is frozen, test it on a new identity-only
bounded discovery roster. Evaluate RESOLVE only if at least one nominated
contract actually reaches it. Do not infer a resolver repair requirement from
G6's empty-supply executions.

## Audit inputs and identities

The external seal binds 464 already-consumed model contacts and records zero
new contacts during sealing. The analysis binds these immutable inputs:

| Input | SHA-256 |
|---|---|
| External complete manifest | `191a182598832bcd99ede7e3121b2285f0e3c5340ee0e18b16fc3c879b4780b3` |
| G6 final outputs | `8ecbcb785e12a26d690a448f4c897d4e01a0c5d048c0a0a7295f6548979b4c6e` |
| G6 SCAN states | `6183aa501650525a2b4ee3f1c68ff3ac33d791f3b26c77bae2dbcf9cee6e2d01` |
| First transport trace, 8 contacts | `99f6b74b8eac96b540a0a8cf8e2db5d9ebd66ccd86e6c601769e3eb5ae11e81e` |
| Second transport trace, 456 contacts | `23f5eb29502e1a76ae9242536350e35cf2b9a362a9a982ea5f4b64dc8050b807` |
| Frozen same-roster G1 M0 outputs | `dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467` |
| Frozen G5 family corpus | `92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5` |
| Frozen scorer semantics | `a2b1380f408a29af0a31cb3a0d8d0730fa8ec07e64ec45d14a7e258595ac70a0` |
| Frozen gold parser | `29e0f2d56a28ce975508ed2e0cfbf2eade7c64907c60d0027909ebcb74da1209` |

The full paths and hashes are recorded in `analysis.json`. The analyzer is
[`analyze.py`](./analyze.py), and its synthetic unit coverage is
[`test_a2t_g6_result_analysis.py`](../../../../tests/unit/test_a2t_g6_result_analysis.py).

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed `g6-seal` outputs.jsonl (16/16 rows) and the shared
`A2T-G1-104` M0 baseline (filtered to these same 16 sample ids), v1 identity confirmed to 4 decimals
overall, under the registered `a2t-scorer-v2` (`analysis.a2t_v2_rescore`,
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| System | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| g6 (g6-seal) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| m0 (same 16 ids) | 0.1875 | 0.3750 | 0.2500 | 0.3750 | 0.3750 | -- | -- | -- |

Paired contrast, g6 vs. m0 (same 16 ids; v1 and v2, CI90, 10,000 replicates, tier-stratified):

| metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|
| v1 exact | -0.1875 | 0 | 3 | 13 | [-0.2500, -0.1250] |
| v2 exact | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v1 tool | -0.3750 | 0 | 6 | 10 | [-0.5000, -0.2500] |
| v2 tool (multiset) | -0.3750 | 0 | 6 | 10 | [-0.5000, -0.2500] |

g6 itself scores 0/16 on every metric under BOTH v1 and v2 (no predicted call this scorer version
change resolves), so its deficit versus m0 is unchanged in direction and CI-exclusion-of-zero either
way. This is a mechanism diagnostic, not a promotion decision; the reading that g6's family-sweep
approach fails to produce any correct call on this roster holds under v2 as well.
