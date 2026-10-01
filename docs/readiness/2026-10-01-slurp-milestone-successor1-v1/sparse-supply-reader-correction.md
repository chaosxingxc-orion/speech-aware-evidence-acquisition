# Sparse prepared supply: reader correction

The registered successor1 analysis stopped at its final-report delivery extension
after producing the registered aggregate statistics. Preserve that partial analysis
directory and every source artifact. Do not repeat generation, official scoring,
bootstrap resampling or gold stratification.

The new reader incorrectly required a dense prepared value map. The frozen runtime
`FlightRuntime._load_phase_supply_seed` accepts a subset of roster rows, and the
runner uses an empty bootstrap tuple for each omitted row. The COMP1B preparation
contains 3,009 explicit rows for its 3,010-row roster. The missing row means empty
supply, not unknown supply. This is a reader compatibility defect, not a generation
or preparation defect.

The corrected reader still checks the preparation hash, confines its path, rejects
extra rows, malformed or duplicate values and other phases, and compares every flown
boundary set. It reports the number of omitted rows. An omitted row with a nonempty
flown set remains a mismatch. Synthetic cases cover both outcomes.

A gold-free diagnostic checked both complete phase artifacts against their seal
pins and each arm's own prepared artifact: PLAN 3,010/3,010 equal, COMP1B
3,010/3,010 equal, zero mismatches. The diagnostic did not open scores, task answers
or gold. Its external receipt is
`coordination/milestone-successor1-read-v1/sparse-supply-verification-v1.json`,
SHA-256 `c38d354a482c291747fd6e95a309628566a315ece330df8a9900dac966e5e9b8`.
It also pins every preserved partial-analysis file.

Root will complete only the missing delivery, cost-frontier and report extensions
under the existing countersigned READ identity. Copy the existing aggregate files
byte-for-byte into a separate completion directory, verify their recorded hashes,
and record provenance. Revalidate the original allowance and complete-family
qualification first. This is completion of the original registered analysis,
not another comparison or new statistical draw. Do not interpret partial results
or supply this independent milestone to the optimizer.

The same compatibility audit found an unrelated all-off proof defect for Audio2Tool
and Earnings21: an old declaration omits newly catalogued components, which the
compiler correctly treats as off. The proof now compares compiled policies while
retaining literal-declaration inequality and omitted component names as diagnostics.
Baseline composition hashes and all existing policy/config comparisons remain
mandatory. No carrier profile, held cell, runtime policy or immutable config changes.

Validation: 270 related tests pass; two data-dependent sealed-pool tests skip when
no data environment is supplied. Reader statement coverage is 90%; module proof
coverage is 93%. Engineering-base and whitespace checks pass. The three warnings
are existing third-party deprecations. All validation is model-free.
