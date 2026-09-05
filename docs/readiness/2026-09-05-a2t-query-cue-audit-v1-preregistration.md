# A2T query-cue audit (model-free, zero contacts), v1 preregistration (DRAFT, not registered)

Status: drafted 2026-09-05 as step 2 of the owner-confirmed mechanism order. A2T-ORG-1 (domain-grouped registry) has
since landed HARMFUL (-3.23 pp, CI90 -4.15 to -2.33): the domain cue removed cross-domain twin misses (621 -> 521) but
created more same-domain ones (898 -> 1,118), so ORG-2 is registered against the official-protocol baseline and this
audit's TARGET list is the same-domain twins first. Not registered until the owner's GO.

## 1. Question

A2T-ORG-2 proposes to roll out contrastive descriptions for the same-domain functional twins
(`rebootDevice` / `restartDevice`, `setSecurityMode` / `armSecuritySystem`, `activateScene` / `activateRoutine`,
`getApplianceState` / `getApplianceStatus`, `setLighting` / `setLightState`, `getAirQuality` / `getAirQuality_diag`)
and the cross-domain twins (`setColor` / `setColorTemperature` / `setLighting` vs `setAmbientLighting`,
`setFanMode` vs `setFanSpeed`, `getLockState` vs `getLockStatus`, `setVolume` vs `setAudioVolume`,
`controlPlayback_home` vs `controlPlayback`). A rolled-out description can only help if the spoken queries of the
two tools carry a cue that separates them. This audit measures that ceiling before any rollout is spent, and
names the pairs that are label noise from the model's point of view.

## 2. Population and legality

Construction pool = every public Audio2Tool row of tiers 1 to 8 whose identity is NOT in any evaluation roster
(the frozen 400, the 4,000 official-population rows, the tier-1 remainder roster, the 608 earlier probe identities,
and every other id listed in `docs/receipts/probe-samples/`). Identity-only decontamination is proven in the
receipt with the overlap count (must be 0). The audit reads the `query` text and the gold `tool_name` of
construction rows only, offline, under one `model-free-check` ledger row registered before the first read. No
model contact; no evaluation-roster text is read.

## 3. Measurements, per twin pair (and pooled)

1. Query separability ceiling: a cross-validated (5-fold, grouped by query_idx) linear bag-of-words classifier
   between the two tools' construction queries, reported as accuracy and as the two per-token log-odds lists
   (top 15 tokens each side). This is the best any query-only discriminator can do with lexical cues.
2. Description-cue coverage: for each tool, the share of its construction queries containing at least one
   content token of its own registry description or signature, versus the share containing a token of the twin's
   description; the pair is "description-separable" if the two shares differ by at least 20 points.
3. Domain-cue coverage (cross-domain pairs): the share of queries naming a device or context word of the gold
   domain (home / room / appliance names vs car / cabin / seat / vehicle vs watch / wrist / workout), from a
   fixed word list stated in the receipt.
4. Sealed-error cross-check (zero contact, reading sealed outputs and roster gold only, already covered by the
   flight rows): for each pair, how many of the sealed official-protocol misses on the evaluation rosters go
   in each direction, so that the ceiling is stated against the actual error mass.

## 4. Decision (fixed before the read)

- A pair is an ORG-2 TARGET if its query separability ceiling is at least 0.80 and the description-cue coverage
  differs by at least 20 points (the cue exists in speech and the current description does not carry it).
- A pair is DOMAIN-ONLY if it is cross-domain, separability is at least 0.80 and the domain-cue coverage is at
  least 0.60: ORG-1's grouping is expected to cover it; ORG-2 adds nothing.
- A pair is LABEL NOISE if separability is below 0.65: no description can recover it; its error mass is reported
  as the floor of any Audio2Tool mechanism and excluded from ORG-2's expected gain.
- Pairs in between are listed as UNCERTAIN and handled by ORG-2 only if capacity allows.
ORG-2's preregistration will cite this audit's TARGET list and the summed error mass it can address.

## 5. Deliverables

`docs/readiness/2026-09-05-a2t-query-cue-audit-v1.md` (this note, completed with results),
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-query-cue-audit/` (summary.json, per-pair tables,
the decontamination receipt, MANIFEST.sha256), one ledger row opened before and closed after.
