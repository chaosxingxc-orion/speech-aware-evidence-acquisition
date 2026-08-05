# Innovation-candidate ledger (append-only)

Every entry is a falsifiable delta claim with evidence pointers. Entries are
never edited or deleted; corrections append a new entry referencing the old
one. Sources (design spec §6): (1) reproduction failure modes from probe gap
memos, (2) the contract's three capability gaps (accessibility,
currency/proper-name, verifiability), (3) structural boundary gaps
(NOT_READY lines from the readiness memo).

Entry format:

## IC-<nnn> <short title> (<YYYY-MM-DD>)

- source: failure-mode | capability-gap | boundary-gap
- axis: OBS | ORG | SUPPLY | USE
- claim: "prior P has failure mode F under our boundary; axis control C removes F"
  (or the capability/boundary-gap analogue)
- null hypothesis: what result would falsify the claim
- evidence: receipt / ledger-row / memo paths
- status: OPEN | PROMOTED_TO_2B | RETIRED

---

(no entries yet)
