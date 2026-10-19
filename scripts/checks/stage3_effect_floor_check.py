#!/usr/bin/env python3
"""Model-free gate: a Stage-3 cell's design must be able to SEE its effect.

The measurement instrument note
``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``
(section 2d, the floor table; section 3, the six rules; section 6, this gate)
is binding for every Stage-3 claim from 2026-09-26. Its finding: two
request-identical flights of the SAME 625 rows differ by +1.87 pp SLU with a
CI95 that excludes zero while intent moves -1.28 pp, so a cross-flight
contrast at n = 625 cannot see an effect below about 3 pp, and the only
0.67 pp instrument the rig has is an offline read over one sealed sample pool.

This script refuses a preregistration whose DECLARED design cannot see its
DECLARED effect, before the GPU hours are spent rather than after.

**The declaration block.** A Stage-3 cell declares three facts in a top-level
``stage3_measurement`` object::

    "stage3_measurement": {
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "expected_effect_pp": 3.2,
      "rows": 625,
      "primary_metric": "official SLURP pooled SLU-F1 (micro)",
      "claims_benefit": true,
      "replicate_run_id": "SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1",
      "note": "one sentence naming what the cell expects and why"
    }

* ``measurement_design`` -- one of :data:`DESIGNS`: ``offline-sealed-pool``,
  ``same-flight-paired``, ``same-flight-supply-variant``,
  ``cross-flight-with-in-chain-replicate``, ``cross-flight-no-replicate``,
  ``form-proof``, ``material-source`` (a collection column read offline as material: no floor, no benefit claim, any n; 2026-10-11).
  ``same-flight-supply-variant`` is the supply-variant column
  read (owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-
  supply-variant-instrument-design.md): a Solver-local effect from
  ``supply_variants`` arms read against their in-flight twin; it may claim
  only ``"nominated"`` in ``flight_registration_check.py``, never
  ``"admitted"``.
* ``same-flight-node-column`` (NX programme E1/E2, 2026-10-09) is the NODE-TEMPLATE
  column read: K instruction-template arms at ONE node over the same sealed
  predecessor state, paired per row against the delivering (locked-template) arm
  inside one flight (``rails.supply_variants.parse_template_variants``,
  docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-
  design.md). A cell of this design must carry a ``template_variants`` summary
  beside ``measurement_design`` -- ``{"node": "solver"|"perception", "candidate_arms": 1..6,
  "twin": true|false}`` -- which this gate checks for shape only (the arm group
  itself is parsed, and refused by name, by the rails at config load). Its floor
  is the same-flight CONTRAST floor, borrowed from ``same-flight-supply-variant``
  (the same estimand width: a per-row paired contrast inside one flight, n =
  1,080) until a node-column cell has flown and measured its own twin null.
* ``expected_effect_pp`` -- a number: the effect, in percentage points on the
  cell's primary metric, the cell is registered to LOOK FOR. Not a hope and
  not a bound; the size the mechanism is believed to produce.
* ``rows`` -- the population count. Optional: it falls back to the experiment
  fragment's ``population.count``, which is where the harness reads it.
* ``primary_metric_key`` -- closed set ``intent`` | ``slu`` | ``present``: WHICH
  of the cell's metrics ``expected_effect_pp`` is about. Owner decision 190
  (2026-09-29) put a DIFFERENT floor on each metric for ``same-flight-supply-
  variant``, ``same-flight-perception-variant`` and ``same-flight-shadow-
  relisten`` (:data:`FLOOR_TABLE` row ``sampling_by_metric``), so a cell of one
  of those designs that claims a benefit must say which metric it means;
  omitting it is finding ``primary-metric-key-missing``. ``present`` (gold-on-
  list, e.g. P-SV-2's level-1 read) carries no numeric floor at all -- finding
  ``primary-metric-key-present``, always advisory, never blocking.
* ``primary_metric``, ``note`` -- free text, reported, never enforced.
* ``claims_benefit`` -- optional, default ``true``. ``false`` says the cell
  proves FORM, not benefit, and is the only legal value for ``form-proof``
  and for a cell under :data:`MIN_BENEFIT_ROWS` rows.
* ``admission`` -- optional, default ``benefit``. ``benefit`` is owner decision
  115's rule: the CI95 lower bound above zero. ``no-harm`` is owner decision
  127's ENGINEERING-BASE mode -- sound logic, a stated ceiling, and a reading
  that the primary metric did not fall below a preregistered margin. A
  ``no-harm`` cell claims no benefit, may never be reported as one, and must
  carry ``harm_margin_pp``.
* ``harm_margin_pp`` -- required by ``admission`` ``no-harm``: the positive
  number of percentage points the primary metric may not fall below. It may not
  be TIGHTER than the measured floor of its own design, because a margin the
  design cannot see is not a bound on harm -- it is a bound the cell will appear
  to satisfy whatever happens. For a no-harm reading that floor is the design's
  SAMPLING half-width alone -- owner decision 127 names them: 0.67 pp offline
  over a sealed pool, 0.735 same-flight paired, 1.2485 cross-flight at Fold A
  1,080, 1.2525 at DEV 1,000 -- because the rule-3 admission bar is a BENEFIT
  bar (the delta a cross-flight arm must EXCEED over its replicate's offset to
  claim a gain) and a no-harm cell claims none; ``floor_for(...,
  purpose="harm")`` is that arithmetic.
* ``replicate_run_id`` -- required by
  ``cross-flight-with-in-chain-replicate``: the run id of the
  request-identical replicate that flies in the SAME chain (rule 3).
* ``tuning_roster``, ``read_roster`` -- item D3 (docs/results/2026-09-27-
  verdict-reclassification.md: the AGREE agreement term was tuned and read on
  the SAME TRAIN Fold A roster, a circular read). ``tuning_roster`` is the
  roster id or sealed-pool id -- or a list of them -- that any weight,
  threshold, cap, template or knowledge selection of this cell was chosen on;
  the literal string ``"none"`` when nothing was tuned. ``read_roster`` is the
  roster the cell is read on. Every Stage-3 cell declares both, whatever its
  ``measurement_design``. This script does not itself enforce them; the
  registration and the tuning/read overlap check live in
  ``flight_registration_check.py`` (findings ``tuning-roster-missing``,
  ``tuning-roster-unverified``, ``tuning-read-overlap``), which reads the same
  block through this file's ``_declaration_files`` / ``_block_for``.

**Where the block may live**, in this precedence:

1. ``docs/readiness/<package>/registered-facts-v*.json``, top level -- the
   file that already holds every number a cell registers before contact;
2. a ``docs/readiness/*preregistration*.md``, inside a fenced ``json`` block
   whose object carries ``stage3_measurement`` at its top level;
3. the experiment fragment itself
   (``configs/experiment/<fragment>.json``, top level) -- legal, and the
   natural place for a cell minted after this gate landed, but an edit to a
   fragment moves the composed hash its readiness package pinned, so an
   ALREADY pinned cell declares in (1) or (2) instead.

A file in (1) or (2) applies to a cell when its text names that cell's
``run_id`` (preferred) or ``cell_id``; one package therefore registers a whole
family. When several cells of a family want different numbers, the block may
be a mapping of run id -> block instead of one block.

**The floor table** (:data:`FLOOR_TABLE`, sourced from
:data:`INSTRUMENT_NOTE` section 2d -- change the note and this table is the
one line that follows):

===================================== ======================================
design                                floor at n rows (CI95 half-width, pp)
===================================== ======================================
``offline-sealed-pool``               ``0.67 * sqrt(625 / rows)``
``same-flight-paired``                ``0.735 * sqrt(200 / rows)`` (unchanged)
``same-flight-supply-variant``        per metric (owner decision 190): intent
                                       ``0.65 * sqrt(1080 / rows)``, slu
                                       ``1.49 * sqrt(1080 / rows)``
``same-flight-node-column``           per metric: borrowed from the row above
                                       until a node-column cell measures its null
``same-flight-perception-variant``    per metric (owner decision 190): same
                                       two anchors as same-flight-supply-variant
``same-flight-shadow-relisten``       slu only (owner decision 190):
                                       ``1.49 * sqrt(1080 / rows)``; intent is
                                       identical by construction, no floor
``cross-flight-with-in-chain-replicate`` ``max(sampling, admission bar)``
``cross-flight-no-replicate``         refused outright (rule 4)
``form-proof``                        none; must claim no benefit (rule 5)
===================================== ======================================

The cross-flight sampling half-width and the rule-3 admission bar are each
anchored at the n the note measured them at (sampling 1.474 at 625, 1.2525 at
1,000, 1.2485 at 1,080; bar about 3 pp at 625 and 2.5 pp at 1,080) and scaled
to the cell's own n by ``anchor * sqrt(anchor_n / rows)`` from the anchor
NEAREST in log n, so an anchored n reproduces the note's own number exactly
instead of being re-derived from a neighbour.

**Owner decision 190 (2026-09-29, "好" = approved).** The three per-metric rows
above replace the single provisional SLU anchor (0.735 at n = 200, scaling to
0.3163 at n = 1,080) that every same-flight design but ``same-flight-paired``
carried until this decision. The new anchors are the LARGER of the two
measured same-flight CONTRAST half-widths at n = 1,080: cell W-SV-1 (intent
0.5093, SLU 1.4866 --
``docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md``) and cell W4-SV
(intent 0.65, SLU 1.25 --
``docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md``), so intent 0.65
and SLU 1.49 (see
``docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md`` for the
full derivation). ``same-flight-paired`` and every other design are
unchanged. A design carrying a per-metric floor refuses a metric-blind
``floor_for`` call (:func:`floor_for`) rather than guessing, and a same-flight
cell that claims a benefit under such a design must declare
``primary_metric_key``.

**Scope.** A cell is in scope when all three hold: its experiment fragment is
a Stage-3 fragment by exactly the test
``scripts/checks/stage3_algorithm_label_check.py`` applies
(``is_stage3_fragment``: the ``stage3`` token in the stem or the
``experiment_id``, a named Stage-3 spec, or that gate's explicit list); its
``readiness.state`` is live (:data:`LIVE_READINESS_STATES`); and its run id has
a row in ``docs/exposure-ledger.md``. Everything else is out of scope and
counted in the summary: a cell with no ledger row has no registration to
enforce against, and a retired / superseded / preparation-pending cell will
never fly in that form.

An in-scope cell whose ledger row says it is CONSUMED is reported and never a
finding: those bytes already flew and this repository does not rewrite them.

**Advisory or blocking** (section 6: "advisory for cells already flown and
blocking for new ones"). A finding is BLOCKING when the cell's registration
date is on or after :data:`STRICT_FROM_DEFAULT` (2026-09-27), and ADVISORY
otherwise. Every cell registered on 2026-09-26 predates the note by hours --
the note and this gate landed that day -- so the law's own day is advisory and
the gate blocks from the next day. The registration date is the cell's
exposure-ledger ``date``, else its fragment's ``date``, else the date prefix of
its readiness package; a date none of those yield leaves the cell advisory and
says so. ``--strict-from`` moves the boundary for a caller that wants to see
what the law would refuse.

**Findings**, one printed line each; each is a FAIL when blocking:

``missing-declaration``
    No ``stage3_measurement`` anywhere this gate looks. An undeclared cell of
    fewer than :data:`MIN_BENEFIT_ROWS` rows is NOT a finding: under rule 5 a
    batch that small is a form proof by size and declares nothing.
``unparsable-declaration``
    A block exists and is not readable: an unknown design, a non-numeric
    ``expected_effect_pp``, an unresolvable or non-positive ``rows``, a
    non-boolean ``claims_benefit``, or a JSON fence carrying the key that does
    not parse.
``cross-flight-no-replicate``
    Rule 4: never claim from a single cross-flight contrast against an older
    sealed comparator with no in-chain replicate. Refused outright.
``missing-in-chain-replicate``
    ``cross-flight-with-in-chain-replicate`` naming no ``replicate_run_id``:
    the design's whole content is that the replicate flies too.
``underpowered-benefit-claim``
    Rule 5: fewer than :data:`MIN_BENEFIT_ROWS` rows together with a benefit
    claim.
``form-proof-claims-benefit``
    ``form-proof`` with ``claims_benefit`` true -- the floor table's own
    condition on that row.
``effect-below-floor``
    ``expected_effect_pp`` below the design's floor at the cell's own n. The
    printed line carries the arithmetic.
``primary-metric-key-missing``
    Owner decision 190: a cell of a design that carries a per-metric floor
    (``sampling_by_metric`` non-empty) claims a benefit but declares no
    ``primary_metric_key``, so the gate cannot resolve which floor applies;
    the effect-vs-floor comparison is skipped, never guessed. Grandfathered
    like the note's own law date (:data:`DECISION_190_DATE`): a cell
    registered on or before 2026-09-29 could not have declared a field this
    gate did not yet require, so it is always advisory; a cell registered
    from 2026-09-30 (:data:`STRICT_FROM_190_DEFAULT`) blocks as usual.
``primary-metric-key-present``
    Always advisory, never blocking: ``primary_metric_key`` is ``present``
    (gold-on-list), which carries no numeric floor by design; the declared
    effect is reported, not checked against a bound.

Exit 0 when no blocking finding remains (advisory lines are still printed);
exit 1 on a blocking finding or an unreadable tree. ``--explain CELL`` prints
the floor table and one cell's arithmetic and never changes the exit code of a
gate run, so a registering agent can see the bar BEFORE writing the
preregistration.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--ledger``, ``--json``, ``--explain [CELL]``,
``--strict-from YYYY-MM-DD``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

EXPOSURE_LEDGER = Path("docs/exposure-ledger.md")
EXPERIMENT_DIR = Path("configs/experiment")
READINESS = Path("docs/readiness")

#: The note whose section 2d IS the floor table below.
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"

#: The key of the declaration block, wherever it is carried.
MEASUREMENT_KEY = "stage3_measurement"

#: Rule 5: a batch under this many rows is a form proof, never evidence.
MIN_BENEFIT_ROWS = 200

#: The law landed 2026-09-26; a cell registered that day predates it by hours.
LAW_DATE = dt.date(2026, 9, 26)
STRICT_FROM_DEFAULT = LAW_DATE + dt.timedelta(days=1)

#: Owner decision 190 landed 2026-09-29 and added ``primary_metric_key`` to the declaration
#: block. A cell registered on or before that day could not have declared a field the gate did
#: not yet require, so its ``primary-metric-key-missing`` finding is grandfathered advisory
#: exactly like :data:`LAW_DATE` above; a cell registered from the next day blocks as usual.
#: This threshold is fixed (not a CLI flag, unlike ``--strict-from``): it dates one specific
#: field, not the whole declaration.
DECISION_190_DATE = dt.date(2026, 9, 29)
STRICT_FROM_190_DEFAULT = DECISION_190_DATE + dt.timedelta(days=1)

#: The readiness states of a cell that is still on the queue -- the same two
#: words ``finite_completion_policy_check.py`` enforces against.
LIVE_READINESS_STATES = ("ready", "held")
NO_READINESS_STATE = "<no readiness block>"

RUN_COLUMN = "run/experiment id"
CONSUMED_COLUMN = "consumed"
DATE_COLUMN = "date"

DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
JSON_FENCE = re.compile(r"```(?:json)?[^\n]*\n(.*?)\n```", re.DOTALL)
RUN_ID_SHAPE = re.compile(r"^SAEA[-A-Z0-9]*$")


@dataclass(frozen=True)
class Floor:
    """One row of the note's floor table.

    ``sampling`` and ``bar`` are ``(n, half-width in pp)`` anchors measured at
    that n; the floor at another n scales each by ``sqrt(anchor_n / rows)``
    from the anchor nearest in log n and takes the larger of the two families.

    ``sampling_by_metric`` (owner decision 190, 2026-09-29) is the per-metric
    form of ``sampling``: a mapping of metric name (``"intent"`` or ``"slu"``)
    to its own anchors. When it is non-empty it REPLACES ``sampling`` for this
    design entirely -- :func:`floor_for` refuses a metric-blind call for such
    a design rather than silently falling back to one metric's anchor for
    another's declaration. A design may omit a metric from the mapping (e.g.
    ``same-flight-shadow-relisten`` carries no ``"intent"`` entry because
    intent is identical by construction there); asking for that metric is
    also refused, never treated as "no floor".
    """

    source: str
    sampling: tuple[tuple[int, float], ...] = ()
    sampling_by_metric: dict[str, tuple[tuple[int, float], ...]] = field(default_factory=dict)
    bar: tuple[tuple[int, float], ...] = ()
    refused: str | None = None
    requires_replicate: bool = False
    forbids_benefit: bool = False


#: Section 2d of :data:`INSTRUMENT_NOTE`, verbatim in numbers.
FLOOR_TABLE: dict[str, Floor] = {
    "offline-sealed-pool": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2c/2d row 1: the F1 aggregation read over the "
            "sealed ROLL-1 samples, medoid rule +0.03 pp CI95 [-0.63, +0.71] at n = 625"
        ),
        sampling=((625, 0.67),),
    ),
    "same-flight-paired": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2a/2d row 2: cell ROLL-AA, two passes inside one "
            "flight, h_within 0.735 SLU / 0.000 intent at n = 200"
        ),
        sampling=((200, 0.735),),
    ),
    "same-flight-supply-variant": Floor(
        source=(
            "owner decision 190 (2026-09-29, \"好\" = approved): per-metric anchors, the "
            "LARGER of the two measured same-flight CONTRAST half-widths at n = 1,080 -- "
            "cell W-SV-1 (intent 0.5093, SLU 1.4866; "
            "docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md) and cell W4-SV "
            "(intent 0.65, SLU 1.25; "
            "docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md, section "
            "'Instrument note'), so intent 0.65 and SLU 1.49 -- full derivation in "
            "docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md. "
            "Supersedes the provisional ROLL-AA anchor (0.735 SLU / 0.000 intent at "
            "n = 200, scaling to 0.3163 at n = 1,080; docs/superpowers/specs/2026-09-27-"
            "same-flight-supply-variant-instrument-design.md section 4, owner decision "
            "172 Q2), which sat below BOTH measured contrast half-widths (1.61x short "
            "on intent, 4.70x short on SLU). The estimand (Solver-local, non-delivering "
            "arms never reach Reviewer/Planner) and the claim ceiling (nominated only, "
            "never admitted) are unchanged by this recalibration"
        ),
        sampling_by_metric={"intent": ((1080, 0.65),), "slu": ((1080, 1.49),)},
    ),
    # NX programme E1/E2 (2026-10-09): the node-template column read -- K
    # instruction-template arms at one node over the SAME sealed predecessor
    # state in one flight, paired per row against the delivering arm. The
    # estimand is the node-local answer under each template (not the delivered
    # full-system answer), exactly as ``same-flight-supply-variant``'s is, and
    # the contrast width at n = 1,080 is the same paired-contrast width, so the
    # floor is that design's, borrowed and labelled as such until a node-column
    # cell has flown and measured its own twin/contrast null.
    "same-flight-node-column": Floor(
        source=(
            "NX programme E1 (2026-10-09, docs/readiness/2026-10-09-slurp-nx-node-"
            "extreme-programme-v1.md section C0.2/C1): borrowed from "
            "same-flight-supply-variant (owner decision 190): intent 0.65, SLU 1.49 at "
            "n = 1,080, the larger of the two measured same-flight CONTRAST half-widths "
            "(cell W-SV-1 and cell W4-SV; docs/results/2026-09-29-slurp-same-flight-"
            "floor-recalibration.md). PROVISIONAL: replaced by the first node-column "
            "cell's own twin null on its node-local estimand"
        ),
        sampling_by_metric={"intent": ((1080, 0.65),), "slu": ((1080, 1.49),)},
    ),
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md): the Perception-branch episode-level fork, read against its
    # required A/A twin (T). NOTE: the design document's own section 4 names
    # this value ``same-flight-perception-branch``; it is registered here as
    # ``same-flight-perception-variant`` to match the coordinator's naming for
    # this gate, and the discrepancy is flagged for reconciliation at the
    # design's next revision (no phase-2 cell has registered under either
    # spelling yet).
    "same-flight-perception-variant": Floor(
        source=(
            "owner decision 190 (2026-09-29): the same per-metric anchors as "
            "same-flight-supply-variant -- intent 0.65, SLU 1.49 at n = 1,080, the "
            "larger of the two measured same-flight CONTRAST half-widths (cell W-SV-1 "
            "and cell W4-SV; docs/results/2026-09-29-slurp-same-flight-floor-"
            "recalibration.md and docs/results/2026-09-29-slurp-w4sv-fold-a-column-"
            "read.md) -- borrowed until a phase-2 cell (P-SV-1, level 2 intent, or "
            "P-SV-2, level 1 presence) has flown and measured its own twin/contrast "
            "null on the Perception-branch estimand (design section 4, 'A/A = twin'). "
            "Supersedes the provisional ROLL-AA anchor (0.735 SLU / 0.000 intent at "
            "n = 200; design docs/superpowers/specs/2026-09-28-same-flight-instrument-"
            "phase2-perception-variants-design.md section 4, extending phase 1's Q3 "
            "ruling). The estimand (an episode-level Perception fork with its own "
            "twin, not a Solver-local arm sharing the row's own QueryState) and the "
            "claim ceiling (level 1 nominates only into level 2, design section 8 O1) "
            "are unchanged by this recalibration. ``primary_metric_key`` 'present' "
            "(P-SV-2's level-1 gold-on-list read) carries no floor in either table"
        ),
        sampling_by_metric={"intent": ((1080, 0.65),), "slu": ((1080, 1.49),)},
    ),
    # Item E4 (2026-09-28, owner decision 185, "core-native targeted re-
    # listen"; design docs/superpowers/specs/2026-09-28-e4-core-native-
    # targeted-relisten-design.md section 4, extended by the section 8
    # coordinator rulings, ruling 7): a shadow-delivery column read against
    # the SAME flight's delivered column, built by a pure ``bind()`` over
    # already-sealed bytes -- structurally ``same-flight-paired``'s own
    # shape. The design's own floor is the shadow column's twin/shadow null
    # (the paired-difference null on the UNCHANGED rows of the pair); until
    # an E4 cell has flown and measured that null, the provisional floor is
    # owner decision 190's SLU anchor (below) -- kept as its own design value
    # because the estimand (two POST-HOC derived columns from one flight's
    # sealed relisten receipts, never a second contact stream) and the claim
    # ceiling (nominated only, never admitted -- ``flight_registration_
    # check.py``) both differ from the Solver-arm estimand
    # ``same-flight-supply-variant`` reads. Intent is identical by
    # construction on this design's two derived columns (ruling 7), so it
    # carries NO floor at all -- not zero, not borrowed, absent from
    # ``sampling_by_metric``, and ``floor_for(..., metric="intent")`` refuses.
    "same-flight-shadow-relisten": Floor(
        source=(
            "owner decision 190 (2026-09-29): the SLU anchor only, intent carries no "
            "floor. SLU 1.49 at n = 1,080, the larger of the two measured same-flight "
            "CONTRAST half-widths (cell W-SV-1 and cell W4-SV; "
            "docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md and "
            "docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md), borrowed until "
            "an E4 cell has flown and measured its own shadow contrast. Supersedes the "
            "provisional ROLL-AA anchor (0.735 SLU at n = 200); design "
            "docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-"
            "design.md section 4 ('same-flight-paired, shadow delivery') and section 8 "
            "ruling 7 ('the bar is the twin/shadow null'; intent identical by "
            "construction)"
        ),
        sampling_by_metric={"slu": ((1080, 1.49),)},
    ),
    "cross-flight-with-in-chain-replicate": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2b/2d rows 3-5 (sampling half-widths 1.474 at 625, "
            "1.2525 at 1,000, 1.2485 at 1,080) and section 3 rule 3 (the admission bar: "
            "about 3 pp at 625, 2.5 pp at 1,080)"
        ),
        sampling=((625, 1.474), (1000, 1.2525), (1080, 1.2485)),
        bar=((625, 3.0), (1080, 2.5)),
        requires_replicate=True,
    ),
    "cross-flight-no-replicate": Floor(
        source=f"{INSTRUMENT_NOTE} section 3 rule 4",
        refused=(
            "rule 4: never claim from a single cross-flight contrast against an older "
            "sealed comparator with no in-chain replicate -- a pure A/A pair at n = 625 "
            "read +1.87 pp with a CI95 that excludes zero"
        ),
    ),
    "form-proof": Floor(
        source=f"{INSTRUMENT_NOTE} section 3 rule 5 and section 2d row 6",
        forbids_benefit=True,
    ),
    # 2026-10-11 (coordinator resolution to owner decision 263-A): a column flown to be READ OFFLINE as the proposer / reflector MATERIAL
    # SOURCE of the typed loop (docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/). It is a measurement-free rollout on the
    # construction roster: it carries no contrast, no twin and no numeric floor, and like ``form-proof`` it may not claim a benefit -- but
    # it is not a four-row structural proof, so it keeps its own name and is legal at any row count.
    "material-source": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 3 rule 5 by analogy (no benefit claim, no numeric floor), applied to a collection column "
            "read as proposer material; docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/README.md"
        ),
        forbids_benefit=True,
    ),
}

DESIGNS = tuple(FLOOR_TABLE)


class Stage3EffectFloorCheckError(RuntimeError):
    """The gate could not read something it must read."""


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------


def _nearest_anchor(
    anchors: tuple[tuple[int, float], ...], rows: int
) -> tuple[int, float]:
    """The anchor nearest ``rows`` in log n -- exact at an anchored n."""

    return min(anchors, key=lambda anchor: abs(math.log(anchor[0] / rows)))


def _scaled(
    anchors: tuple[tuple[int, float], ...], rows: int
) -> tuple[float, str]:
    anchor_n, anchor_h = _nearest_anchor(anchors, rows)
    value = anchor_h * math.sqrt(anchor_n / rows)
    return value, (
        f"{anchor_h:g} * sqrt({anchor_n} / {rows}) = {value:.4f} pp"
        if anchor_n != rows
        else f"{anchor_h:g} pp, measured at n = {rows}"
    )


def floor_for(
    design: str, rows: int, *, purpose: str = "benefit", metric: str | None = None
) -> tuple[float | None, list[str]]:
    """``(floor in pp, the arithmetic as lines)``.

    ``None`` means the design carries no numeric floor (``form-proof``);
    ``math.inf`` means the design is refused outright. ``purpose`` is
    ``"benefit"`` (the default: the smallest effect the design can SEE, the
    larger of the sampling half-width and the rule-3 admission bar) or
    ``"harm"`` (owner decision 127: the sampling half-width alone -- the rule-3
    bar is what a gain must exceed, and a no-harm cell claims no gain).

    ``metric`` (owner decision 190, 2026-09-29) selects one of a design's
    ``sampling_by_metric`` anchors (``"intent"`` or ``"slu"``). A design that
    declares ``sampling_by_metric`` carries NO metric-blind floor: calling
    this function for such a design without ``metric``, or with a ``metric``
    it does not anchor (e.g. ``"intent"`` on ``same-flight-shadow-relisten``,
    which has none by construction), is a caller error and raises -- this
    never silently falls back to another metric's anchor. A design with no
    ``sampling_by_metric`` ignores ``metric`` entirely: it has one floor for
    every metric, as before decision 190.
    """

    if purpose not in ("benefit", "harm"):
        raise ValueError(f"purpose must be 'benefit' or 'harm', not {purpose!r}")
    rule = FLOOR_TABLE[design]
    if rule.refused is not None:
        return math.inf, [f"refused outright -- {rule.refused}"]
    lines: list[str] = []
    parts: list[float] = []
    if rule.sampling_by_metric:
        if metric is None:
            raise ValueError(
                f"design {design!r} declares per-metric floors "
                f"({sorted(rule.sampling_by_metric)}, owner decision 190); floor_for(...) "
                "requires metric='intent' or metric='slu' and refuses to guess"
            )
        if metric not in rule.sampling_by_metric:
            raise ValueError(
                f"design {design!r} declares a floor only for "
                f"{sorted(rule.sampling_by_metric)}, not metric {metric!r}"
            )
        value, shown = _scaled(rule.sampling_by_metric[metric], rows)
        lines.append(f"sampling half-width ({metric}): {shown}")
        parts.append(value)
    elif rule.sampling:
        value, shown = _scaled(rule.sampling, rows)
        lines.append(f"sampling half-width: {shown}")
        parts.append(value)
    if rule.bar and purpose == "harm":
        lines.append(
            "rule-3 admission bar not applied: a no-harm reading claims no benefit, "
            "so its floor is the sampling half-width alone (owner decision 127)"
        )
    elif rule.bar:
        value, shown = _scaled(rule.bar, rows)
        lines.append(f"rule-3 admission bar: {shown}")
        parts.append(value)
    if not parts:
        lines.append("no numeric floor: this design may not claim a benefit at all")
        return None, lines
    floor = max(parts)
    if len(parts) > 1:
        lines.append(f"floor = max of the two = {floor:.4f} pp")
    else:
        lines.append(f"floor = {floor:.4f} pp")
    return floor, lines


# --------------------------------------------------------------------------
# reading the tree
# --------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3EffectFloorCheckError(f"cannot read {label}: {error}") from error


def _parse_ledger(repo_root: Path, ledger: Path) -> dict[str, dict[str, str]]:
    """``{run id: row}`` with the repository's own exposure-ledger parser."""

    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            _parse_ledger_tables,
        )
    except Exception as error:  # pragma: no cover - import environment problem
        raise Stage3EffectFloorCheckError(
            f"cannot import the repository's exposure-ledger parser from {src}: {error}"
        ) from error
    path = repo_root / ledger
    if not path.is_file():
        raise Stage3EffectFloorCheckError(f"missing {ledger.as_posix()}")
    try:
        parsed = _parse_ledger_tables(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as error:
        raise Stage3EffectFloorCheckError(
            f"cannot parse {ledger.as_posix()}: {error}"
        ) from error
    rows: dict[str, dict[str, str]] = {}
    for row in parsed:
        run_id = str(row.get(RUN_COLUMN, "")).strip()
        if run_id:
            rows.setdefault(run_id, dict(row))
    return rows


def _stage3_predicate(repo_root: Path):
    """``is_stage3_fragment`` of the algorithm-label gate, so scope agrees."""

    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import stage3_algorithm_label_check as label_gate  # noqa: PLC0415
    except Exception as error:  # pragma: no cover - import environment problem
        raise Stage3EffectFloorCheckError(
            f"cannot import stage3_algorithm_label_check from {here}: {error}"
        ) from error
    return label_gate.is_stage3_fragment


def _consumed(row: dict[str, str]) -> str:
    """The ``consumed`` cell reduced to its leading verdict word."""

    cell = str(row.get(CONSUMED_COLUMN, "")).replace("*", "").strip().lower()
    return cell.split(";")[0].split("(")[0].strip()


def _date_in(text: Any) -> dt.date | None:
    match = DATE_PREFIX.search(str(text or ""))
    if match is None:
        return None
    try:
        return dt.date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def _readiness_state(cell: dict[str, Any]) -> str:
    readiness = cell.get("readiness")
    if not isinstance(readiness, dict):
        return NO_READINESS_STATE
    state = readiness.get("state")
    return state if isinstance(state, str) and state.strip() else NO_READINESS_STATE


@dataclass
class DeclarationFile:
    """One file that may carry a declaration, read once."""

    relpath: str
    kind: str
    text: str
    blocks: Any = None
    parse_error: str | None = None


def _blocks_from_json_document(document: Any) -> Any:
    if isinstance(document, dict) and MEASUREMENT_KEY in document:
        return document[MEASUREMENT_KEY]
    return None


@functools.lru_cache(maxsize=None)
def _declaration_files(repo_root: Path) -> list[DeclarationFile]:
    """Every readiness file that carries a ``stage3_measurement``, in order.

    ``registered-facts`` JSON first, preregistration markdown second: the
    precedence the docstring promises.

    Memoised per ``repo_root`` for the life of the process: this glob-and-parse over every
    ``docs/readiness/*/`` package (roughly a thousand directories in the real tree) is expensive,
    and its result cannot change within one gate run (no writer touches ``docs/readiness/`` while
    a gate reads it). Before this cache existed, ``flight_registration_check.py`` called this
    function twice per cell (once for the supply-variant check, once for the item D3 roster-split
    check) with zero reuse, turning a tree-mode ``--include-held`` run into hundreds of redundant
    full-tree rescans -- the 2026-09-28 performance regression this cache fixes. A test that
    mutates ``docs/readiness/`` and then re-evaluates the SAME ``repo_root`` within one process
    must call ``_declaration_files.cache_clear()`` first.
    """

    files: list[DeclarationFile] = []
    root = repo_root / READINESS
    if not root.is_dir():
        return files
    for path in sorted(root.glob("*/registered-facts*.json")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if MEASUREMENT_KEY not in text:
            continue
        entry = DeclarationFile(
            relpath=path.relative_to(repo_root).as_posix(), kind="registered-facts", text=text
        )
        try:
            entry.blocks = _blocks_from_json_document(json.loads(text))
        except json.JSONDecodeError as error:
            entry.parse_error = f"not readable JSON: {error}"
        if entry.blocks is None and entry.parse_error is None:
            entry.parse_error = (
                f"names {MEASUREMENT_KEY!r} but carries no such key at its top level"
            )
        files.append(entry)
    for path in sorted(root.glob("*preregistration*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if MEASUREMENT_KEY not in text:
            continue
        entry = DeclarationFile(
            relpath=path.relative_to(repo_root).as_posix(), kind="preregistration", text=text
        )
        errors: list[str] = []
        for fence in JSON_FENCE.findall(text):
            if MEASUREMENT_KEY not in fence:
                continue
            try:
                blocks = _blocks_from_json_document(json.loads(fence))
            except json.JSONDecodeError as error:
                errors.append(f"a fenced json block carrying the key does not parse: {error}")
                continue
            if blocks is not None:
                entry.blocks = blocks
                break
        if entry.blocks is None:
            entry.parse_error = (
                "; ".join(errors)
                if errors
                else (
                    f"names {MEASUREMENT_KEY!r} but no fenced json block carries it at "
                    "top level"
                )
            )
        files.append(entry)
    return files


def _block_for(blocks: Any, run_id: str | None, cell_id: str | None) -> Any:
    """One cell's block out of a file's ``stage3_measurement`` value.

    A block is either the object itself or a mapping of run / cell id ->
    object, which is how one package registers a family whose cells want
    different numbers.
    """

    if not isinstance(blocks, dict):
        return blocks
    if "measurement_design" in blocks or "expected_effect_pp" in blocks:
        return blocks
    for key in (run_id, cell_id):
        if key and key in blocks:
            return blocks[key]
    if all(isinstance(value, dict) for value in blocks.values()) and blocks:
        return None  # a keyed mapping that does not name this cell
    return blocks


#: How a cell asks to be admitted. ``benefit`` is decision 115's rule -- the CI95 lower bound
#: above zero -- and is the default when nothing says otherwise. ``no-harm`` is owner decision
#: 127's ENGINEERING-BASE mode: sound logic, a stated ceiling and a reading that the primary metric
#: did not fall below a preregistered margin. A no-harm cell claims no benefit and may never be
#: reported as one, and its margin may not be tighter than what its design can actually see.
_ADMISSIONS: frozenset[str] = frozenset({"benefit", "no-harm"})

#: NX programme E1: the design a node-template column read declares, the nodes a template
#: group may sit at (mirrors ``rails.supply_variants.TEMPLATE_VARIANT_NODES``, which a unit test
#: compares) and the candidate-arm bound (mirrors ``MAX_TEMPLATE_CANDIDATE_ARMS``). This gate
#: reads no package source, so it restates them.
NODE_COLUMN_DESIGN = "same-flight-node-column"
TEMPLATE_VARIANT_NODES: tuple[str, ...] = ("solver", "perception")
MIN_TEMPLATE_CANDIDATE_ARMS, MAX_TEMPLATE_CANDIDATE_ARMS = 1, 6

#: The closed set of ``variant_kind`` values a node-column cell may declare (the axis its arms vary). The last two are decision
#: 338's SAMPLING column (``rails.supply_variants.SAMPLING_VARIANT_KINDS``, which a unit test compares). A sampling column
#: requires its in-flight A/A twin: its estimand is read against the twin's offset.
VARIANT_KINDS: tuple[str, ...] = (
    "solver-template", "solver-decoding", "thinking-budget", "thinking-policy",
    "perception-sampling", "solver-sampling",
)
SAMPLING_VARIANT_KINDS: tuple[str, ...] = ("perception-sampling", "solver-sampling")

#: Owner decision 190 (2026-09-29): the closed set ``primary_metric_key`` may name. ``intent``
#: and ``slu`` each resolve a design's own ``sampling_by_metric`` anchor (:data:`FLOOR_TABLE`);
#: ``present`` (gold-on-list, e.g. P-SV-2's level-1 read) carries no numeric floor at all.
_PRIMARY_METRIC_KEYS: frozenset[str] = frozenset({"intent", "slu", "present"})


@dataclass
class Declaration:
    """One cell's parsed declaration, or the reason it is not one."""

    source: str | None = None
    design: str | None = None
    effect_pp: float | None = None
    rows: int | None = None
    rows_source: str | None = None
    claims_benefit: bool = True
    admission: str | None = None
    harm_margin_pp: float | None = None
    replicate_run_id: str | None = None
    primary_metric: str | None = None
    primary_metric_key: str | None = None
    note: str | None = None
    #: NX programme E1: the node-template summary a ``same-flight-node-column``
    #: cell declares (``node``, ``candidate_arms``, ``twin``); ``None`` otherwise.
    template_variants: dict[str, Any] | None = None
    #: The axis a node-column cell's arms vary (:data:`VARIANT_KINDS`), or ``None`` when undeclared.
    variant_kind: str | None = None
    problems: list[str] = field(default_factory=list)


def _parse_declaration(
    block: Any, source: str, fragment_rows: int | None
) -> Declaration:
    parsed = Declaration(source=source)
    if not isinstance(block, dict):
        parsed.problems.append(f"{MEASUREMENT_KEY} must be a JSON object, not {type(block).__name__}")
        return parsed

    design = block.get("measurement_design")
    if design in DESIGNS:
        parsed.design = design
    else:
        parsed.problems.append(
            f"measurement_design is {design!r}; the designs are {', '.join(DESIGNS)}"
        )

    effect = block.get("expected_effect_pp")
    if isinstance(effect, bool) or not isinstance(effect, (int, float)):
        parsed.problems.append(
            f"expected_effect_pp is {effect!r}; it must be a number of percentage points"
        )
    else:
        parsed.effect_pp = float(effect)

    declared_rows = block.get("rows")
    if declared_rows is None:
        if isinstance(fragment_rows, int) and fragment_rows > 0:
            parsed.rows = fragment_rows
            parsed.rows_source = "the fragment's population.count"
        else:
            parsed.problems.append(
                "rows is absent and the experiment fragment declares no positive "
                "population.count, so no floor can be computed"
            )
    elif isinstance(declared_rows, bool) or not isinstance(declared_rows, int) or declared_rows <= 0:
        parsed.problems.append(f"rows is {declared_rows!r}; it must be a positive integer")
    else:
        parsed.rows = declared_rows
        parsed.rows_source = "the declaration"

    admission = block.get("admission")
    if admission is not None:
        if not isinstance(admission, str) or admission not in _ADMISSIONS:
            parsed.problems.append(
                f"admission is {admission!r}; it must be one of {sorted(_ADMISSIONS)}"
            )
        else:
            parsed.admission = admission
    margin = block.get("harm_margin_pp")
    if margin is not None:
        if isinstance(margin, bool) or not isinstance(margin, (int, float)):
            parsed.problems.append(f"harm_margin_pp is {margin!r}; it must be a number")
        elif float(margin) <= 0.0:
            parsed.problems.append(
                f"harm_margin_pp is {float(margin):g}; a harm margin is a positive number of "
                "percentage points, because it bounds how much loss the design could still see"
            )
        else:
            parsed.harm_margin_pp = float(margin)
    claims = block.get("claims_benefit", True)
    if not isinstance(claims, bool):
        parsed.problems.append(f"claims_benefit is {claims!r}; it must be true or false")
    else:
        parsed.claims_benefit = claims

    replicate = block.get("replicate_run_id")
    if replicate is not None and not isinstance(replicate, str):
        parsed.problems.append(f"replicate_run_id is {replicate!r}; it must be a run id string")
    elif isinstance(replicate, str) and replicate.strip():
        parsed.replicate_run_id = replicate.strip()

    primary_metric_key = block.get("primary_metric_key")
    if primary_metric_key is not None:
        if not isinstance(primary_metric_key, str) or primary_metric_key not in _PRIMARY_METRIC_KEYS:
            parsed.problems.append(
                f"primary_metric_key is {primary_metric_key!r}; it must be one of "
                f"{sorted(_PRIMARY_METRIC_KEYS)}"
            )
        else:
            parsed.primary_metric_key = primary_metric_key

    template_variants = block.get("template_variants")
    if parsed.design == NODE_COLUMN_DESIGN and template_variants is None:
        parsed.problems.append(
            f"measurement_design {NODE_COLUMN_DESIGN!r} requires a template_variants block "
            '({"node", "candidate_arms", "twin"}) naming the node, the number of candidate '
            "template arms and whether an A/A twin flies"
        )
    elif template_variants is not None and parsed.design != NODE_COLUMN_DESIGN:
        parsed.problems.append(
            f"template_variants is declared but measurement_design is {parsed.design!r}; a "
            f"node-template column read declares {NODE_COLUMN_DESIGN!r}"
        )
    elif template_variants is not None:
        parsed.template_variants = _parse_template_variants_summary(template_variants, parsed)

    variant_kind = block.get("variant_kind")
    if variant_kind is not None:
        if not isinstance(variant_kind, str) or variant_kind not in VARIANT_KINDS:
            parsed.problems.append(
                f"variant_kind is {variant_kind!r}; it must be one of {list(VARIANT_KINDS)}"
            )
        elif parsed.design != NODE_COLUMN_DESIGN:
            parsed.problems.append(
                f"variant_kind is declared but measurement_design is {parsed.design!r}; a variant kind belongs to "
                f"a {NODE_COLUMN_DESIGN!r} cell"
            )
        else:
            parsed.variant_kind = variant_kind
            if variant_kind in SAMPLING_VARIANT_KINDS and not (
                isinstance(parsed.template_variants, dict) and parsed.template_variants.get("twin") is True
            ):
                parsed.problems.append(
                    f"variant_kind {variant_kind!r} requires template_variants.twin true: a sampling column is read "
                    "against its in-flight A/A twin"
                )

    for key in ("primary_metric", "note"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            setattr(parsed, key, value.strip())
    return parsed


def _parse_template_variants_summary(block: Any, parsed: Declaration) -> dict[str, Any] | None:
    """Shape of the ``template_variants`` summary; each defect is a problem of
    ``parsed``. The arm group itself is the rails' to parse."""

    if not isinstance(block, dict) or set(block) != {"node", "candidate_arms", "twin"}:
        parsed.problems.append(
            'template_variants must be exactly {"node", "candidate_arms", "twin"}'
        )
        return None
    ok = True
    if block["node"] not in TEMPLATE_VARIANT_NODES:
        parsed.problems.append(
            f"template_variants.node is {block['node']!r}; a template group may sit only at "
            f"{list(TEMPLATE_VARIANT_NODES)}"
        )
        ok = False
    arms = block["candidate_arms"]
    if (
        isinstance(arms, bool) or not isinstance(arms, int)
        or not MIN_TEMPLATE_CANDIDATE_ARMS <= arms <= MAX_TEMPLATE_CANDIDATE_ARMS
    ):
        parsed.problems.append(
            f"template_variants.candidate_arms is {arms!r}; it must be an integer from "
            f"{MIN_TEMPLATE_CANDIDATE_ARMS} to {MAX_TEMPLATE_CANDIDATE_ARMS}"
        )
        ok = False
    if not isinstance(block["twin"], bool):
        parsed.problems.append(f"template_variants.twin is {block['twin']!r}; it must be true or false")
        ok = False
    return dict(block) if ok else None


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------


def _find_declaration(
    files: list[DeclarationFile],
    run_id: str | None,
    cell_id: str | None,
    fragment: dict[str, Any],
    fragment_relpath: str,
    fragment_rows: int | None,
) -> Declaration | None:
    """The cell's declaration, in the docstring's precedence, or ``None``."""

    for entry in files:
        names_it = bool(run_id and run_id in entry.text) or bool(
            cell_id and cell_id in entry.text
        )
        if not names_it:
            continue
        if entry.parse_error is not None:
            parsed = Declaration(source=entry.relpath)
            parsed.problems.append(entry.parse_error)
            return parsed
        block = _block_for(entry.blocks, run_id, cell_id)
        if block is None:
            continue
        return _parse_declaration(block, entry.relpath, fragment_rows)
    if MEASUREMENT_KEY in fragment:
        block = _block_for(fragment[MEASUREMENT_KEY], run_id, cell_id)
        if block is not None:
            return _parse_declaration(block, fragment_relpath, fragment_rows)
    return None


def _resolve_floor(
    design: str,
    rule: Floor,
    rows: int,
    parsed: Declaration,
    *,
    purpose: str = "benefit",
    emit_findings: bool = True,
) -> tuple[float | None, list[str], list[dict[str, Any]]]:
    """The numeric floor for one declaration, honouring ``primary_metric_key``.

    Owner decision 190 (2026-09-29): a design that carries ``sampling_by_metric``
    has no metric-blind floor any more, so this wraps :func:`floor_for` with the
    declaration's own ``primary_metric_key`` and turns the three new outcomes
    (missing, ``"present"``, or a metric the design does not anchor) into
    findings instead of a crash. Returns ``(floor, arithmetic, extra_findings)``;
    ``extra_findings`` carry no ``cell``/``severity``/``run_id`` -- the caller
    merges those in, as it does for every other finding in ``_findings_for``.

    ``emit_findings=False`` is for the no-harm harm-floor call in
    ``_findings_for``, which reuses this resolution but must not double-report
    a declaration defect the benefit-floor call already reported for the same
    cell.
    """

    extra: list[dict[str, Any]] = []
    metric = parsed.primary_metric_key

    if metric == "present":
        if emit_findings:
            extra.append(
                {
                    "kind": "primary-metric-key-present",
                    "severity": "advisory",
                    "message": (
                        "primary_metric_key 'present' (gold-on-list) carries no numeric "
                        "floor by design; the expected effect is reported, not checked "
                        "against a bound"
                    ),
                }
            )
        return None, ["primary_metric_key 'present' has no numeric floor by design"], extra

    if rule.sampling_by_metric:
        if metric is None:
            if emit_findings and parsed.claims_benefit:
                extra.append(
                    {
                        "kind": "primary-metric-key-missing",
                        "message": (
                            f"measurement_design {design!r} claims a benefit but declares no "
                            "primary_metric_key ('intent', 'slu' or 'present'); owner "
                            "decision 190 (2026-09-29) put a different floor on each metric "
                            "of this design and the gate cannot check the effect without "
                            "knowing which one the cell means"
                        ),
                    }
                )
            return (
                None,
                [
                    "floor not computed: design declares per-metric floors and no "
                    "primary_metric_key was given"
                ],
                extra,
            )
        if metric not in rule.sampling_by_metric:
            if emit_findings:
                extra.append(
                    {
                        "kind": "unparsable-declaration",
                        "message": (
                            f"primary_metric_key {metric!r} has no floor in {design!r} (it "
                            f"declares a floor only for {sorted(rule.sampling_by_metric)})"
                        ),
                    }
                )
            return None, [], extra
        floor, arithmetic = floor_for(design, rows, purpose=purpose, metric=metric)
        return floor, arithmetic, extra

    floor, arithmetic = floor_for(design, rows, purpose=purpose)
    return floor, arithmetic, extra


def _findings_for(record: dict[str, Any], parsed: Declaration | None) -> list[dict[str, Any]]:
    """Every rule, applied to one in-scope unconsumed cell."""

    cell = record["cell_id"]
    rows = record["rows"]
    findings: list[dict[str, Any]] = []

    if parsed is None:
        if isinstance(rows, int) and rows < MIN_BENEFIT_ROWS:
            return []
        findings.append(
            {
                "kind": "missing-declaration",
                "message": (
                    f"{cell}: no {MEASUREMENT_KEY} block in its readiness package, its "
                    f"preregistration or its fragment "
                    f"({record['fragment_relpath']}); a live Stage-3 cell of "
                    f"{rows if rows is not None else 'an undeclared number of'} row(s) must "
                    f"declare measurement_design, expected_effect_pp and rows "
                    f"(see {INSTRUMENT_NOTE} section 2d)"
                ),
            }
        )
        return findings

    if parsed.problems:
        for problem in parsed.problems:
            findings.append(
                {
                    "kind": "unparsable-declaration",
                    "message": (
                        f"{cell}: {MEASUREMENT_KEY} in {parsed.source} is not readable: "
                        f"{problem}"
                    ),
                }
            )
        return findings

    design = parsed.design
    rule = FLOOR_TABLE[str(design)]
    rows = parsed.rows or rows

    if rule.refused is not None:
        findings.append(
            {
                "kind": "cross-flight-no-replicate",
                "message": (
                    f"{cell}: measurement_design {design!r} is refused outright -- "
                    f"{rule.refused}. Fly a request-identical replicate in the same chain "
                    f"and declare cross-flight-with-in-chain-replicate, or read the action "
                    f"offline over a sealed sample pool."
                ),
            }
        )
        return findings

    if rule.forbids_benefit and parsed.claims_benefit:
        findings.append(
            {
                "kind": "form-proof-claims-benefit",
                "message": (
                    f"{cell}: measurement_design {design!r} may prove form only, but the "
                    f"declaration claims a benefit (claims_benefit true, "
                    f"expected_effect_pp {parsed.effect_pp:g}); set claims_benefit false or "
                    f"declare the design that can see the effect"
                ),
            }
        )

    if rule.requires_replicate and parsed.replicate_run_id is None:
        findings.append(
            {
                "kind": "missing-in-chain-replicate",
                "message": (
                    f"{cell}: measurement_design {design!r} names no replicate_run_id; "
                    f"rule 3 admits a cross-flight arm only when a request-identical "
                    f"replicate flies in the SAME chain"
                ),
            }
        )

    if isinstance(rows, int) and rows < MIN_BENEFIT_ROWS and parsed.claims_benefit:
        findings.append(
            {
                "kind": "underpowered-benefit-claim",
                "message": (
                    f"{cell}: {rows} row(s) with a benefit claim; rule 5 makes a batch under "
                    f"{MIN_BENEFIT_ROWS} rows a FORM proof, never evidence of benefit "
                    f"(terminal feedback on 4-16 trajectories cannot distinguish any effect "
                    f"this program is chasing)"
                ),
            }
        )

    floor, arithmetic, metric_findings = _resolve_floor(str(design), rule, int(rows), parsed)
    registered = _date_in(record.get("registered_date"))
    for extra in metric_findings:
        finding = {
            "kind": extra["kind"],
            "message": f"{cell}: {extra['message']}",
        }
        if "severity" in extra:
            finding["severity"] = extra["severity"]
        elif extra["kind"] == "primary-metric-key-missing" and (
            registered is None or registered < STRICT_FROM_190_DEFAULT
        ):
            # Grandfathered: this cell was registered before owner decision 190 required
            # primary_metric_key, so it could not have declared it.
            finding["severity"] = "advisory"
        findings.append(finding)

    # Owner decision 127: an engineering-base item is admitted on sound logic, a stated ceiling and
    # a NO-HARM reading, and never has to demonstrate a gain. Two consequences are enforced here.
    # The margin is measured against the design's SAMPLING half-width (decision 127's own numbers:
    # 1.2485 cross-flight at Fold A 1,080), not against the rule-3 benefit bar a gain must exceed.
    if parsed.admission == "no-harm":
        harm_floor, harm_arithmetic, _harm_metric_findings = _resolve_floor(
            str(design), rule, int(rows), parsed, purpose="harm", emit_findings=False
        )
        if parsed.claims_benefit:
            findings.append(
                {
                    "kind": "no-harm-claims-benefit",
                    "message": (
                        f"{cell}: admission 'no-harm' with claims_benefit true; a base item is "
                        "admitted on a no-harm reading and may never be reported as a gain "
                        "(owner decision 127), so set claims_benefit false"
                    ),
                }
            )
        if parsed.harm_margin_pp is None:
            findings.append(
                {
                    "kind": "missing-harm-margin",
                    "message": (
                        f"{cell}: admission 'no-harm' without harm_margin_pp; a no-harm reading "
                        "is only a reading if the margin it must not breach was preregistered "
                        f"-- the measured floor of {design} at n = {rows} is "
                        f"{'unbounded' if harm_floor is None else format(harm_floor, '.4f') + ' pp'}"
                    ),
                }
            )
        elif harm_floor is not None and parsed.harm_margin_pp < harm_floor:
            findings.append(
                {
                    "kind": "harm-margin-below-floor",
                    "message": (
                        f"{cell}: harm_margin_pp {parsed.harm_margin_pp:g} is tighter than the "
                        f"{design} no-harm floor {harm_floor:.4f} pp at n = {rows} "
                        f"[{'; '.join(harm_arithmetic)}]; a margin the design cannot see is not a "
                        f"bound on harm, it is a bound this cell will appear to satisfy whatever "
                        f"happens -- source: {rule.source}"
                    ),
                }
            )

    # A cell that claims nothing cannot have an effect below the floor: the comparison only means
    # something for a cell registered to LOOK for an effect. Before 2026-09-26 it ran regardless,
    # and every collection and form-proof cell drew a spurious advisory from it.
    if (
        parsed.claims_benefit
        and floor is not None
        and parsed.effect_pp is not None
        and parsed.effect_pp < floor
    ):
        findings.append(
            {
                "kind": "effect-below-floor",
                "message": (
                    f"{cell}: expected_effect_pp {parsed.effect_pp:g} is below the "
                    f"{design} floor {floor:.4f} pp at n = {rows} "
                    f"[{'; '.join(arithmetic)}]; this design cannot see the effect the cell "
                    f"is registered to look for -- source: {rule.source}"
                ),
            }
        )
    return findings


def evaluate(
    repo_root: Path,
    ledger: Path = EXPOSURE_LEDGER,
    strict_from: dt.date = STRICT_FROM_DEFAULT,
) -> dict[str, Any]:
    ledger_rows = _parse_ledger(repo_root, ledger)
    is_stage3 = _stage3_predicate(repo_root)
    files = _declaration_files(repo_root)

    directory = repo_root / EXPERIMENT_DIR
    if not directory.is_dir():
        raise Stage3EffectFloorCheckError(f"missing {EXPERIMENT_DIR.as_posix()}")

    cells: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    out_of_scope = {
        "not_stage3_fragments": 0,
        "no_ledger_row": [],
        "not_live_cells": [],
    }
    consumed_cells: list[str] = []
    form_proof_by_size: list[str] = []
    scanned = 0

    for path in sorted(directory.glob("*.json")):
        scanned += 1
        text = path.read_text(encoding="utf-8")
        fragment = _read_json(path, path.name)
        if not isinstance(fragment, dict):
            raise Stage3EffectFloorCheckError(
                f"{EXPERIMENT_DIR.as_posix()}/{path.name}: a fragment must be a JSON object"
            )
        in_scope, why = is_stage3(path.stem, fragment, text)
        if not in_scope:
            out_of_scope["not_stage3_fragments"] += 1
            continue
        fragment_relpath = f"{EXPERIMENT_DIR.as_posix()}/{path.name}"
        population = fragment.get("population")
        fragment_rows = (
            population.get("count") if isinstance(population, dict) else None
        )
        if isinstance(fragment_rows, bool) or not isinstance(fragment_rows, int):
            fragment_rows = None

        for cell in fragment.get("cells") or []:
            if not isinstance(cell, dict):
                continue
            cell_id = cell.get("cell_id") or path.stem
            run_id = cell.get("run_id") if isinstance(cell.get("run_id"), str) else None
            state = _readiness_state(cell)
            row = ledger_rows.get(run_id or "")
            if state not in LIVE_READINESS_STATES:
                out_of_scope["not_live_cells"].append({"cell": cell_id, "state": state})
                continue
            if row is None:
                out_of_scope["no_ledger_row"].append(cell_id)
                continue

            registered = _date_in(row.get(DATE_COLUMN))
            date_source = f"{ledger.as_posix()} date column"
            if registered is None:
                registered = _date_in(fragment.get("date"))
                date_source = "the fragment's date"
            if registered is None:
                registered = _date_in(str(cell.get("readiness", {})))
                date_source = "a date named in the cell's readiness block"
            if registered is None:
                date_source = "unresolved"

            record = {
                "cell_id": cell_id,
                "run_id": run_id,
                "fragment": path.stem,
                "fragment_relpath": fragment_relpath,
                "in_scope_because": why,
                "readiness_state": state,
                "rows": fragment_rows,
                "consumed": _consumed(row),
                "registered_date": registered.isoformat() if registered else None,
                "registered_date_source": date_source,
            }
            severity = (
                "blocking"
                if registered is not None and registered >= strict_from
                else "advisory"
            )
            if record["consumed"] != "no":
                record["severity"] = "reported (already flown)"
                record["declaration"] = None
                consumed_cells.append(cell_id)
                cells.append(record)
                continue

            parsed = _find_declaration(
                files, run_id, cell_id, fragment, fragment_relpath, fragment_rows
            )
            record["severity"] = severity
            record["declaration"] = (
                None
                if parsed is None
                else {
                    "source": parsed.source,
                    "measurement_design": parsed.design,
                    "expected_effect_pp": parsed.effect_pp,
                    "rows": parsed.rows,
                    "rows_source": parsed.rows_source,
                    "claims_benefit": parsed.claims_benefit,
                    "replicate_run_id": parsed.replicate_run_id,
                    "primary_metric": parsed.primary_metric,
                    "primary_metric_key": parsed.primary_metric_key,
                    "note": parsed.note,
                    "problems": list(parsed.problems),
                    **(
                        {} if parsed.template_variants is None
                        else {"template_variants": parsed.template_variants}
                    ),
                    **({} if parsed.variant_kind is None else {"variant_kind": parsed.variant_kind}),
                }
            )
            cell_findings = _findings_for(record, parsed)
            if parsed is None and not cell_findings:
                form_proof_by_size.append(cell_id)
            for finding in cell_findings:
                # A finding may pre-set its own "severity" (e.g. "primary-metric-key-present",
                # owner decision 190: advisory always, whatever the cell's own registration
                # date says) -- setdefault keeps that instead of the usual date-derived one.
                finding.setdefault("severity", severity)
                finding.update(
                    {
                        "cell": cell_id,
                        "run_id": run_id,
                        "registered_date": record["registered_date"],
                    }
                )
            findings.extend(cell_findings)
            cells.append(record)

    blocking = [finding for finding in findings if finding["severity"] == "blocking"]
    advisory = [finding for finding in findings if finding["severity"] == "advisory"]
    return {
        "schema": "saea-stage3-effect-floor-check-v1",
        "repo_root": str(repo_root),
        "instrument_note": INSTRUMENT_NOTE,
        "ledger": ledger.as_posix(),
        "strict_from": strict_from.isoformat(),
        "declaration_key": MEASUREMENT_KEY,
        "designs": list(DESIGNS),
        "min_benefit_rows": MIN_BENEFIT_ROWS,
        "declaration_files": [entry.relpath for entry in files],
        "scanned_fragments": scanned,
        "in_scope_cells": cells,
        "consumed_cells": sorted(consumed_cells),
        "form_proof_by_size": sorted(form_proof_by_size),
        "out_of_scope": {
            "not_stage3_fragments": out_of_scope["not_stage3_fragments"],
            "no_ledger_row": sorted(out_of_scope["no_ledger_row"]),
            "not_live_cells": sorted(
                out_of_scope["not_live_cells"], key=lambda row: (row["state"], row["cell"])
            ),
        },
        "findings": findings,
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "passed": not blocking,
    }


def render_floor_table(rows: int | None = None) -> list[str]:
    """The floor table, and at ``rows`` its arithmetic, as printable lines."""

    lines = [
        f"floor table (source: {INSTRUMENT_NOTE} sections 2d and 3)",
        f"  a batch under {MIN_BENEFIT_ROWS} rows is a form proof, never evidence (rule 5)",
    ]
    for design, rule in FLOOR_TABLE.items():
        lines.append(f"  {design}:")
        if rule.refused is not None:
            lines.append(f"      refused outright -- {rule.refused}")
        if rule.sampling:
            lines.append(
                "      sampling anchors (n, half-width pp): "
                + ", ".join(f"({n}, {h:g})" for n, h in rule.sampling)
            )
        if rule.sampling_by_metric:
            for metric in sorted(rule.sampling_by_metric):
                lines.append(
                    f"      sampling anchors {metric!r} (n, half-width pp): "
                    + ", ".join(f"({n}, {h:g})" for n, h in rule.sampling_by_metric[metric])
                )
            lines.append(
                "      per-metric floor (owner decision 190): metric= is required, a "
                "metric-blind call is refused"
            )
        if rule.bar:
            lines.append(
                "      rule-3 admission bar anchors: "
                + ", ".join(f"({n}, {h:g})" for n, h in rule.bar)
            )
        if rule.forbids_benefit:
            lines.append("      may prove form only: claims_benefit must be false")
        if rule.requires_replicate:
            lines.append("      must name replicate_run_id (rule 3)")
        if rows is not None and rule.refused is None:
            if rule.sampling_by_metric:
                for metric in sorted(rule.sampling_by_metric):
                    floor, arithmetic = floor_for(design, rows, metric=metric)
                    lines.append(f"      at n = {rows}, metric {metric!r}: " + "; ".join(arithmetic))
            else:
                floor, arithmetic = floor_for(design, rows)
                lines.append(
                    f"      at n = {rows}: " + "; ".join(arithmetic)
                    if floor is not None
                    else f"      at n = {rows}: no numeric floor"
                )
        lines.append(f"      source: {rule.source}")
    return lines


def explain(data: dict[str, Any], cell: str | None) -> list[str]:
    """``--explain``: the table, and one named cell's own arithmetic."""

    if cell is None:
        return render_floor_table()
    matches = [
        row
        for row in data["in_scope_cells"]
        if cell in (row["cell_id"], row["run_id"], row["fragment"])
    ]
    if not matches:
        return [
            f"no in-scope Stage-3 cell matches {cell!r}; in-scope cell ids are in --json",
            *render_floor_table(),
        ]
    lines: list[str] = []
    for row in matches:
        rows_n = row["rows"]
        declaration = row["declaration"]
        lines.append(f"cell {row['cell_id']} (run id {row['run_id']})")
        lines.append(
            f"  fragment {row['fragment_relpath']}, in scope because {row['in_scope_because']}, "
            f"readiness {row['readiness_state']}, consumed {row['consumed']}, "
            f"registered {row['registered_date']} (from {row['registered_date_source']}), "
            f"severity {row['severity']}"
        )
        lines.append(f"  population.count from the fragment: {rows_n}")
        if declaration is None:
            lines.append(f"  no {MEASUREMENT_KEY} declaration found")
        else:
            lines.append(
                f"  declared in {declaration['source']}: design "
                f"{declaration['measurement_design']!r}, expected_effect_pp "
                f"{declaration['expected_effect_pp']}, rows {declaration['rows']} "
                f"(from {declaration['rows_source']}), claims_benefit "
                f"{declaration['claims_benefit']}, primary_metric_key "
                f"{declaration['primary_metric_key']!r}, replicate_run_id "
                f"{declaration['replicate_run_id']}"
            )
            if declaration["problems"]:
                lines.append(f"  unreadable: {'; '.join(declaration['problems'])}")
            design = declaration["measurement_design"]
            n = declaration["rows"] or rows_n
            if design in FLOOR_TABLE and isinstance(n, int) and n > 0:
                metric = declaration["primary_metric_key"]
                try:
                    floor, arithmetic = floor_for(design, n, metric=metric)
                except ValueError as error:
                    lines.append(f"      floor not resolved: {error}")
                    floor = None
                else:
                    for step in arithmetic:
                        lines.append(f"      {step}")
                effect = declaration["expected_effect_pp"]
                if floor is not None and isinstance(effect, (int, float)):
                    verdict = "BELOW the floor" if effect < floor else "clears the floor"
                    lines.append(
                        f"      expected {effect:g} pp vs floor "
                        f"{'infinite' if floor == math.inf else format(floor, '.4f')} pp: "
                        f"{verdict}"
                    )
    first_rows = matches[0]["rows"]
    lines.extend(render_floor_table(first_rows if isinstance(first_rows, int) else None))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--ledger", type=Path, default=EXPOSURE_LEDGER)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--explain",
        nargs="?",
        const="",
        default=None,
        metavar="CELL",
        help=(
            "print the floor table (and, with a cell id / run id / fragment stem, that "
            "cell's own arithmetic) instead of gating"
        ),
    )
    parser.add_argument(
        "--strict-from",
        default=STRICT_FROM_DEFAULT.isoformat(),
        metavar="YYYY-MM-DD",
        help="the registration date from which a finding blocks instead of advising",
    )
    args = parser.parse_args(argv)

    strict_from = _date_in(args.strict_from)
    if strict_from is None:
        print(
            f"stage3 effect floor check: FAIL: --strict-from {args.strict_from!r} is not a "
            "YYYY-MM-DD date",
            file=sys.stderr,
        )
        return 1

    try:
        data = evaluate(args.repo_root.resolve(), args.ledger, strict_from)
    except Stage3EffectFloorCheckError as error:
        print(f"stage3 effect floor check: FAIL: {error}", file=sys.stderr)
        return 1

    if args.explain is not None:
        for line in explain(data, args.explain or None):
            print(line)
        return 0

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for finding in data["findings"]:
        label = "FAIL" if finding["severity"] == "blocking" else "advisory"
        print(f"stage3 effect floor check: {label}: [{finding['kind']}] {finding['message']}")

    out_of_scope = data["out_of_scope"]
    summary = (
        f"{len(data['in_scope_cells'])} in-scope Stage-3 cell(s) of "
        f"{data['scanned_fragments']} fragment(s); {len(data['consumed_cells'])} already "
        f"flown (reported only), {len(data['form_proof_by_size'])} undeclared under "
        f"{MIN_BENEFIT_ROWS} rows (form proof by size); "
        f"{len(data['blocking_findings'])} blocking, "
        f"{len(data['advisory_findings'])} advisory finding(s); blocking from "
        f"{data['strict_from']}; out of scope: "
        f"{out_of_scope['not_stage3_fragments']} non-Stage-3 fragment(s), "
        f"{len(out_of_scope['no_ledger_row'])} cell(s) with no ledger row, "
        f"{len(out_of_scope['not_live_cells'])} not-live cell(s)"
    )
    if data["passed"]:
        print(f"stage3 effect floor check: PASS ({summary})")
        return 0
    print(f"stage3 effect floor check: FAIL ({summary})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
