"""WAVE W4: the four config tables, each with a null arm.

Owner Decision 11-B of 2026-09-08, item #6 of the openJiuwen implementation
assessment's change list (``docs/readiness/
2026-09-08-openjiuwen-implementation-assessment-v1.md`` section 7). The
design note's admission gate (``docs/readiness/
2026-09-08-agent-system-episode-and-core-pressure-v1.md`` section 8) requires
that **module ON versus module OFF is one config key on one harness, never a
second code path**. Section 7 of the assessment measured how far that is from
true today: of the seven harness modules exactly one is cleanly one key (the
silence tail) and one is nearly so (the slot schema, whose OFF arm still
changes the program id and the contact count); the other five need a
``policy`` change, a ``scorers`` change or a policy subclass to turn off,
which makes the OFF arm a different code path and therefore not a twin.

This module closes that gap by giving every module a home in one of four
config tables, each of which is:

* an object declared at the TOP LEVEL of a composed config fragment, exactly
  as ``phase_material`` / ``phase_supply`` / ``phase_review`` already are, so
  it rides ``core.config.compose``'s config hash with no new plumbing;
* validated FAIL-CLOSED here, before a run starts; and
* equipped with a NULL ARM whose composed config hash is byte-identical to
  the table being absent (``core.config.NULL_ARM_TABLE_KEYS`` /
  :func:`core.config.drop_null_arms`), so "module off" and "module never
  declared" are the same cell identity.

The four tables
---------------

============================ ============================================
table                        what one entry switches
============================ ============================================
``observe`` (per phase)      the Observer's mode: silence tail, speaker-turn
                             unit plan, selective re-listen (margin, budget,
                             derivation kind, flag source)
``knowledge_views``          the knowledge the phase sees: the wrapped
(per phase)                  ``phase_material`` entry (its ``state_fill`` IS
                             the view) and the wrapped ``phase_supply`` entry
                             (the retrieval provider)
``judges`` (per phase)       the Reviewer: W1's ``phase_review`` entry, judge
                             ids plus ``on_flag``
``toolkits`` (per run)       which W3 task-type toolkit row is armed, and for
                             which agent roles
============================ ============================================

Wrapping, not rewriting
-----------------------

``knowledge_views`` and ``judges`` WRAP the blocks W1/E1/E6 already ship and
change none of their bytes: a ``knowledge_views.<phase>.material`` object is
the same object a ``phase_material.<phase>`` entry carries, handed to
``rails.phase_material.load_phase_material_specs`` verbatim; the same holds
for ``supply`` and ``rails.phase_supply``, and for ``judges`` and
``rails.phase_review``. There is exactly one new rule: a fragment may declare
the flat block OR the table, never both, because two spellings of one switch
is how a cell ends up with two identities.

The tables therefore add no second validator, no second registry and no
second code path. Every id inside them keeps resolving in a ``core.base``
registry, which is what ``scripts/checks/engineering_base_check.py`` reads
out of source -- including the any-depth ``judges`` rule that check already
carries "so a future top-level ``judges`` list (the design note's own 'judges
config table with a null arm') [is caught] without a second rule".

Why the knowledge table is spelled ``knowledge_views``
------------------------------------------------------

The brief's working name for it is ``knowledge``. That spelling is already
taken at the top level of a composed fragment:
``configs/experiment/a2t-g3-plain-english-v1.json`` declares a ``knowledge``
object of card-build provenance, and ``core.config.compose`` refuses a
top-level key defined by two fragments. A ``knowledge`` table would therefore
be permanently uncomposable with that cell -- fail-closed, at the worst
possible moment. ``knowledge_views`` is the assessment's own spelling for the
same object (section 7: ``knowledge_views: {slots: ... | null}``), it collides
with nothing, and it says what the table holds.

What this module does NOT do
----------------------------

It parses, validates and hashes. It runs nothing: turning a validated
:class:`ConfigTables` into an ``ObserveStep``, a ``review_for_phase`` or an
armed toolkit is the phase-program dispatch in ``core/flight/runtime.py``,
which belongs to the wave that owns that file. Model-free, import-light, no
model/tool/network contact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..core.base import JUDGES, CoreError
from ..core.config import NULL_ARM_TABLE_KEYS
from .controllers import PhaseProgram
from .errors import RailsError
from .hashing import content_hash
from .observe import ObserveConfig
from .phase_material import PhaseMaterialSpec, load_phase_material_specs
from .phase_review import PhaseReviewSpec, load_phase_review_specs
from .phase_supply import PhaseSupplySpec, load_phase_supply_specs

CONFIG_TABLES_SCHEMA = "saea-config-tables-v1"

#: The four table names, sorted, and identical to
#: ``core.config.NULL_ARM_TABLE_KEYS`` -- the hashing rule and the loaders
#: must never disagree about which keys are tables (asserted below).
OBSERVE_TABLE = "observe"
KNOWLEDGE_VIEWS_TABLE = "knowledge_views"
JUDGES_TABLE = "judges"
TOOLKITS_TABLE = "toolkits"
CONFIG_TABLE_NAMES = (JUDGES_TABLE, KNOWLEDGE_VIEWS_TABLE, OBSERVE_TABLE, TOOLKITS_TABLE)

assert CONFIG_TABLE_NAMES == NULL_ARM_TABLE_KEYS, (
    "the config tables and the null-arm hashing rule must name the same keys"
)

#: The flat block each wrapping table replaces. A fragment declares one or the
#: other, never both (:func:`_assert_not_double_declared`).
WRAPPED_FLAT_KEYS = {
    JUDGES_TABLE: ("phase_review",),
    KNOWLEDGE_VIEWS_TABLE: ("phase_material", "phase_supply"),
}

#: The Earnings obs-loop's own flat observe knobs (``reproduction.obs_loop``).
#: They are the pre-table spelling of two of the ``observe`` table's entries
#: and stay readable on that policy path until Earnings moves onto
#: ``FlightRuntime`` (assessment changes #8/#9). Declaring both spellings in
#: one fragment is refused for the same reason as any other double
#: declaration.
LEGACY_OBSERVE_KEYS = (
    "obs_slice_tail_silence_seconds",
    "obs_unit_plan",
    "obs_unit_plan_sha256",
)

_OBSERVE_ENTRY_KEYS = frozenset({"tail_silence_seconds", "unit_plan", "relisten"})
_KNOWLEDGE_VIEW_ENTRY_KEYS = frozenset({"material", "supply"})
_JUDGES_ENTRY_KEYS = frozenset({"judges", "on_flag", "params"})
_TOOLKITS_ENTRY_KEYS = frozenset({"task_type", "roles"})

_PINNED_FILE_KEYS = frozenset({"relpath", "sha256"})
_RELISTEN_KEYS = frozenset(
    {
        "judges",
        "fixture",
        "context_margin_seconds",
        "max_relistens_per_sample",
        "derivation_kind",
    }
)

#: Every table's null arm, in the two spellings a fragment may use. Both drop
#: out of the config hash (``core.config.drop_null_arms``), so all three of
#: ``"observe": null``, ``"observe": {}`` and no ``observe`` key at all are
#: ONE cell identity rather than three.
NULL_ARMS: tuple[object, ...] = (None, {})

#: The FIFTH switch class, added 2026-09-08 when WAVE W4 met the cross-call
#: dispatcher on ``master``. The four tables above are per-PHASE: they say what
#: a phase observes, is supplied with, is judged by and may call, and every one
#: of them changes the request the frozen core sees. A module can also be one
#: config key and still have no table entry, because it is per-RUN and changes
#: no request at all -- a scheduler. ``obs_prefetch_depth`` is the first: it is
#: read flat by ``core.driver.run`` and ``reproduction.obs_loop``, it decides
#: how many samples of lookahead the driver keeps, and its admission cell
#: proved every emitted slice byte-identical to the comparator's.
#:
#: The class is deliberately a CLOSED allowlist rather than "any flat key".
#: A module that changes the request must earn a table entry; the run class
#: exists for the ones that provably do not, and admitting a new key to it is
#: a code change with a test, not a receipt edit.
RUN_SWITCH_CLASS = "run"

#: The SIXTH and SEVENTH switch classes, added by Fable E6 (2026-09-16,
#: ``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md``
#: section 3) for three SLURP v2 base program modules that the five existing
#: classes cannot name: M0 (review-loop off), M2 (grouped-Solver sampling)
#: and M1 (exemplar-grounded Solver). Unlike the four per-phase tables, none
#: of these modules is a mode of what a phase observes, is supplied with, is
#: judged by or may call; unlike ``run``, none of them provably moves zero
#: request bytes, so neither existing extension point fits.
#:
#: ``episode``: one dotted path under the ALREADY-EXISTING, per-run
#: ``native_episode`` block (``rails.native_episode_config``), on a CLOSED
#: allowlist for the same reason ``run``'s is closed -- a module that reaches
#: for a new ``native_episode`` sub-path is a code change with a test, not a
#: receipt edit. ``native_episode.roles.solver`` (M2) is already exactly one
#: key under the existing ``switch_key`` shared-prefix rule: the OFF arm is
#: simply the historical shape (``samples`` absent or 1, no
#: ``decoding_overrides``/``commit``), so no new expansion code was needed for
#: it. ``native_episode.review_loop`` (M0) is different: today's OFF arm is
#: three leaves (``max_revisions``, ``roles.reviewer.max_iterations``,
#: ``roles.planner.max_iterations``) that share no common dotted prefix, so
#: ``switch_key`` refuses them by construction
#: (``tests/unit/test_config_table_module_switches.py``, "E1 review loop
#: off"). Rather than teach ``core.config.compose`` to EXPAND one declared key
#: into those three leaves before hashing -- which would let two different
#: JSON fragments hash to the same cell identity, a much larger change to the
#: composition pipeline than this module's admission needs -- E1's own
#: ``rails.native_episode_config.load_native_episode_config`` gained an
#: OPTIONAL, VALIDATED marker field: a fragment may additionally declare
#: ``native_episode.review_loop`` as ``"on"``/``"off"``, and the loader
#: refuses the whole config if the marker disagrees with what the three
#: leaves already say. The leaves stay authoritative and required exactly as
#: before; the marker is a redundant, checked declaration of what they mean,
#: which is what lets a harness-admission proof point at ONE key while still
#: trusting the leaves it derives, rather than trusting an expansion nobody
#: can see happen.
#:
#: ``stores``: a whole named ``knowledge_stores.<store_id>`` block (M1, the
#: exemplar-grounded Solver's ``train-exemplars`` store). ``knowledge_views``
#: wraps a PHASE's ``phase_material``/``phase_supply`` entry
#: (:data:`WRAPPED_FLAT_KEYS`); it does not wrap ``knowledge_stores``, which
#: is a named STORE's whole block (release/snapshot pins plus its own
#: ``phase_supply``/``candidate_supply``), so a store's switch needs its own
#: class rather than a `knowledge_views` entry key.
#:
#: The ``stores`` class has TWO arm forms and a receipt entry DECLARES which
#: one it is in. The first, and the only one E6 admitted, is the NULL form:
#: OFF is the named store ABSENT from ``knowledge_stores``
#: (:func:`is_stores_null_arm`), which is the shape of a module that ADDS a
#: store the comparator does not carry. The second, added 2026-09-17 by E9 for
#: cell B4b's module M4b (``docs/results/
#: 2026-09-17-slurp-b4b-slot-store-v2-verdict.md``), is the RE-PIN form: a
#: module that REVISES a store the comparator ALREADY carries moves neither
#: more nor less than that store's two pinned leaves, so its OFF arm is the
#: incumbent's ``{release, snapshot}`` pins and its ON arm is the successor's
#: (:func:`is_stores_repin_arm`, :func:`stores_pins`,
#: :func:`stores_arm_matches`). The form is declared as ``switch.form``
#: :data:`STORES_REPIN_FORM` and is never inferred from the arms, because an
#: OFF arm silently allowed to be anything other than the store's absence is
#: exactly the loosening the null form exists to refuse; and a re-pin whose
#: two arms pin the same bytes is refused, because it switches nothing.
#: Everything else about the class is unchanged: still ONE key, still
#: ``knowledge_stores.<store_id>``, still a proof test that shows the two
#: committed fragments differing in that one sub-block alone.
EPISODE_SWITCH_CLASS = "episode"
STORES_SWITCH_CLASS = "stores"

#: The EIGHTH switch class, added 2026-09-20 by item E25 for cell B1-notool
#: (repair form 0-B, owner decisions 55 and 56): ONE ROLE'S TOOLKIT, the
#: ``phase_tools.<phase>`` mapping that grants a role tool AUTHORITY (what it
#: may call, with which knowledge views and which source-authority role).
#: It is not the ``toolkits`` table, whose entry is a TASK TYPE's catalogue
#: selection (``toolkits.task_type`` / ``toolkits.roles``), and not the
#: ``episode`` class, because ``native_episode.tool_schema_rendering`` (E17)
#: decides how a granted toolkit is RENDERED and leaves authority alone. The
#: class exists so that a module which WITHDRAWS a role's toolkit can be
#: written as the retirement of the toolkit it withdraws -- ON is the
#: mapping the comparator carried, OFF is its null arm (``None``, ``{}`` or
#: the role absent from ``phase_tools``, all of which the runtime reads as
#: "no tool authority": ``core.flight.runtime.tool_free_native_arm``) --
#: rather than being forced to call the absence of a mapping an ON arm.
PHASE_TOOLS_SWITCH_CLASS = "phase_tools"

#: The NINTH switch class, added 2026-09-30 by migration step 6 of the
#: evidence-consumption module (owner decisions 195/196/204; design
#: ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
#: section 3.2 and coordinator ruling R2): the COMPOSED policy as one key,
#: ``native_episode.consumption_module``. It is not the ``episode`` class:
#: every episode-class key's OFF arm is that key's own null form (absent, or
#: its documented default), and the module's OFF arm is not the block's
#: absence -- it is the block with EVERY component off, which compiles
#: byte for byte to the carrier's lock layer (the in-chain A/A comparator of
#: every composed read). So the class's OFF arm is a declared lock, and its
#: licence is verified rather than believed: the check compiles the OFF arm
#: (``rails.consumption_module.compile_module``) and requires it to equal the
#: named lock version's policy blocks, and each cell its falsifier names to
#: carry exactly those blocks on its own roster -- the AT-M0 proof, made by
#: the gate itself. Each component's own admission stays in its own entry or
#: registry row; a ``module`` entry records only the composition.
MODULE_SWITCH_CLASS = "module"

#: Every switch class a ``docs/receipts/harness-admission.json`` entry may
#: name: the four config tables, plus ``run``, ``episode``, ``stores``,
#: ``phase_tools`` and ``module``.
#: NOT the same tuple as :data:`CONFIG_TABLE_NAMES`, which is the hashing
#: rule's own list and must keep naming exactly the four tables.
SWITCH_CLASS_NAMES = CONFIG_TABLE_NAMES + (
    RUN_SWITCH_CLASS,
    EPISODE_SWITCH_CLASS,
    STORES_SWITCH_CLASS,
    PHASE_TOOLS_SWITCH_CLASS,
    MODULE_SWITCH_CLASS,
)

#: The ONE key the ``module`` class admits (closed, like every other class).
MODULE_LEVEL_SWITCH_KEYS = frozenset({"native_episode.consumption_module"})

#: The per-run driver keys the ``run`` class admits.
#:
#: ``slurp_projection_v3_delivery`` (E4, SLURP v2 base program module M3,
#: 2026-09-17) is the second: read flat by ``core.flight.runtime.
#: FlightRuntime._canonical_output_rows``, it turns the USE projection v3
#: transform (``rails.slurp_projection_v3.apply_slurp_projection_v3_delivery``)
#: on for the ``slurp`` carrier's own delivered answer. It belongs here, not
#: in one of the four per-phase tables, for the SAME reason
#: ``obs_prefetch_depth`` does: the transform runs strictly AFTER the model's
#: response is already in hand and rewrites only what gets SEALED into the
#: outputs row (the raw response text is kept in custody beside it, under
#: ``pre_projection_text``, never overwritten) -- it moves no request byte
#: whatsoever, so it fails the table classes' own reason for existing (a
#: table entry changes what the frozen core is asked) exactly as
#: ``obs_prefetch_depth``'s own admission note states. ``1`` is ON; absent or
#: ``0`` is OFF (the module's own documented default -- the switch is
#: read via ``bool(values.get(key))``, and this class's own null-arm rule,
#: :func:`is_run_null_arm`, already treats both as the null arm for an
#: integer-valued run key).
#:
#: ``dispatch`` (owner decision 159, 2026-09-27) is the third: the dispatcher
#: slot-fill switches (``rails.dispatch_slot_fill``) read by
#: ``core.flight.runtime.FlightRuntime._dispatch_phase_program`` for the
#: native role episode. It schedules -- a row's Perception-independent recall
#: computed ahead, the role-input builder off the shared event loop, the
#: loaded heap frozen out of the collector -- and moves no request byte, which
#: its falsifier receipt proves on a registered cell against a fake server;
#: absent is OFF (a block that arms no switch is refused by the parser).
RUN_LEVEL_SWITCH_KEYS = frozenset(
    {"obs_prefetch_depth", "slurp_projection_v3_delivery", "dispatch"}
)

#: The ``run`` class's null arm, in the two spellings a fragment may use: the
#: key absent, or the driver's own documented default. ``obs_prefetch_depth``
#: defaults to 0 and 0 means the strictly sequential path every config before
#: 2026-09-08 ran, so ``0`` and "no key" are one cell identity exactly as a
#: table's ``None``/``{}`` are.
RUN_NULL_ARMS: tuple[object, ...] = (None, 0)

#: The top-level key every ``episode``-class switch key is a dotted path
#: under. Matches the literal spelling ``rails.native_episode_config`` reads,
#: not the class label -- exactly as ``run``'s keys are the flat driver
#: spelling, not ``"run.<key>"``.
NATIVE_EPISODE_TOP_LEVEL_KEY = "native_episode"

#: The closed allowlist of ``episode``-class switch keys. Every member is a
#: dotted path under :data:`NATIVE_EPISODE_TOP_LEVEL_KEY`; admitting one more
#: is a code change with a test, not a receipt edit (see the class docstring
#: above). There are ELEVEN today, and the notes below name them in admission
#: order. (Base-lock finding F-18, repaired here: this docstring said "All
#: three" over seven and then nine members, and "admitting a fourth" over the
#: same -- a count that has to be edited on every admission is a count that
#: will be wrong, so it is now stated once, as a rule, and the per-key notes
#: carry the ordinals.)
#:
#: ``native_episode.context_policy`` (E8a, 2026-09-17,
#: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
#: section 5) is the THIRD, admitted by coordinator decision 3 of 2026-09-17.
#: It belongs here for the same reason the other two do: it is one dotted path
#: under the already-existing, per-run ``native_episode`` block, it changes the
#: request the frozen core sees (so the ``run`` class is wrong), and it is a
#: mode of NONE of the four per-phase tables -- it is not what a phase
#: observes, is supplied with, is judged by or may call, but how the material
#: an EARLIER node produced is handled before a LATER node reads it.
#: The pre-existing optional ``native_episode.role_context`` block is folded
#: under it (``rails.node_context_binding``); a fragment carrying both is
#: refused by ``rails.native_episode_config.load_native_episode_config``.
#:
#: ``native_episode.deliver_normaliser`` (E11, 2026-09-18, owner directive 26)
#: is the FOURTH, and the first admitted by a directive rather than by a
#: module design. It belongs here rather than in the ``run`` class -- whose
#: other two members also move no request byte -- because it is not a
#: per-run driver knob at all: it is a NODE of the episode, declared inside
#: the ``native_episode`` block beside the roles it runs after, applied once
#: by ``rails.runner`` between the Planner's ACCEPT (or the terminal
#: delivery) and the delivered answer, and sealed with its own custody
#: receipt. It belongs here rather than in the ``judges`` TABLE because that
#: table wraps a phase's ``phase_review`` entry -- the Reviewer seat, whose
#: entries owner Decision 11-C makes criticism-only
#: (``core.base.JudgeRegistry``) -- and a node that rewrites the delivered
#: answer can never be one of those. See ``core.base.DELIVERY_NORMALISERS``.
#: ``native_episode.reviewer_audit`` (E12, 2026-09-19, owner directive 26) is
#: the FIFTH, and the second admitted by a directive rather than by a module
#: design. It is the READ-side instance of "analyses into nodes": a
#: deterministic, zero-contact SLOT AUDIT block, authored from construction
#: data alone, rendered into the Reviewer's exposed context beside the draft
#: it is checking. It belongs here rather than in ``run`` because it MOVES
#: REQUEST BYTES -- at one boundary, by design -- so no
#: ``request-bytes-identical`` falsifier can exist for it; rather than in the
#: ``knowledge_views`` table because it is not a phase's material or supply,
#: makes no retrieval and adds no evidence block; and rather than folded into
#: ``native_episode.context_policy`` because an audit is a second, separately
#: switchable factor on a boundary that policy already declares -- folding it
#: in would make a cell that moves the audit indistinguishable from a cell
#: that moves the policy. E19 (2026-09-19, owner decision 32, after cell
#: B7a v2 read the L1 policy HARMFUL) made that separation complete: the
#: block resolves an ATTACHMENT rather than requiring a level, so with the
#: boundary at raw -- or with no ``context_policy`` declared at all -- it is
#: appended to the SEALED draft bytes instead of to an L1 rendering, and a
#: cell can move the audit ALONE on a base that declares no policy. See
#: ``rails.slot_audit``, ``rails.node_context_policy.SLOT_AUDIT_BOUNDARY``
#: and ``rails.node_context_policy.SLOT_AUDIT_ATTACHMENTS``.
#: ``native_episode.finite_completion_policy`` (E13, 2026-09-19) is the SIXTH,
#: and the only one of the six that is a FAILURE MODE rather than a factor.
#: It decides what an episode does with a valid, source-bound completion the
#: core ended before authoritative delivery (``finish_reason`` ``length`` or
#: ``content_filter``): ``"raise"``, the parser's default, aborts the flight;
#: ``"deliver-latest-or-abstain"`` retains the row, delivering the latest
#: delivery-eligible Solver draft (or an abstention) under a
#: ``finite_completion`` terminal disposition that names the interrupted role.
#: It belongs here rather than in the ``run`` class because it is read inside
#: the episode's own role chain and is declared inside the ``native_episode``
#: block; and rather than in any of the four per-phase tables because it is a
#: mode of none of them -- not what a phase observes, is supplied with, is
#: judged by or may call. Like ``deliver_normaliser`` it renders NO request
#: byte (it is consulted only where a completion has already come back), which
#: ``tests/unit/test_slurp_finite_completion_row.py`` proves by flying both
#: arms; that makes its ON arm free to be the default of every new cell.
#: ``native_episode.solver_hints`` (E14, 2026-09-19, owner directive 26) is
#: the SEVENTH, and the third admitted by that directive. It is the second
#: READ-side instance of "analyses into nodes": a deterministic,
#: zero-contact SCENARIO HINTS block, authored from construction data alone,
#: rendered into the SOLVER's exposed context beside the candidate list it
#: is choosing between. It belongs here rather than in ``run`` for exactly
#: the reason ``native_episode.reviewer_audit`` does -- it MOVES REQUEST
#: BYTES at one boundary by design -- and it is a key of its own beside the
#: audit because a cell that moves the Solver's hints must stay
#: distinguishable from a cell that moves the Reviewer's audit. See
#: ``rails.scenario_hints`` and
#: ``rails.node_context_policy.SOLVER_HINTS_BOUNDARY``.
#: ``native_episode.tool_schema_rendering`` (E17, 2026-09-19, lever L1 of
#: ``docs/results/2026-09-19-slurp-throughput-root-cause-v1.md``) is the
#: EIGHTH, and the first admitted for EFFICIENCY rather than for a capability.
#: It decides whether the native ``tools`` array is rendered PER ROLE (today:
#: only the tool-bearing role carries it) or held CONSTANT across every
#: contact of a row. The Qwen3-Omni chat template renders that array INSIDE
#: the system message, so a per-role array toggles the prefix twice per row
#: and invalidates the pinned slot's whole KV prefix -- speech packet
#: included -- on 63.5 % of measured prefill work. It belongs here rather
#: than in ``run`` because it MOVES REQUEST BYTES (three roles gain a
#: constant block), so no ``request-bytes-identical`` falsifier can exist for
#: it; and rather than in the ``phase_tools`` table because that table is
#: what a phase MAY CALL -- tool AUTHORITY, which this key leaves exactly as
#: it is. Rendering is not authority: a role without authority still carries
#: ``tool_choice`` ``"none"`` and is still refused by
#: ``reproduction.ojw.native_roles._RoleAuthorityRail`` if it emits a call.
#: ``native_episode.acquisition`` (E18, 2026-09-19, owner decisions 43 and
#: 44) is the NINTH, and the first that adds a NODE to the graph rather than a
#: mode of an existing one. It arms the sixth node of the agent base -- the
#: ``acquire`` primitive -- by naming its registered policy and its per-row
#: budget; the paired ``native_episode.roles.acquisition`` block is part of
#: the same module and is refused without it. It belongs here rather than in
#: ``run`` because it is declared inside the ``native_episode`` block beside
#: the roles it runs between, and it MOVES REQUEST BYTES (the next Solver
#: revision gains the ``acquired-evidence`` block) as well as, for one of its
#: three kinds, spending a contact -- so no ``request-bytes-identical``
#: falsifier can exist for it. It is a key of its own rather than a member of
#: the ``knowledge_views`` table because that table is what a PHASE observes
#: or is supplied with before its contact, and this is what a NODE brings in
#: mid-episode, after a draft has been reviewed. See ``rails.acquisition``
#: and ``rails.node_context_policy.ACQUIRED_EVIDENCE_BOUNDARY``.
#: ``native_episode.context_fit_policy`` (E20, 2026-09-19, owner decision 45)
#: is the TENTH, and the second FAILURE MODE after E13's. It decides what an
#: OVER-LONG request does: ``"raise"`` -- the key absent or written out loud --
#: aborts at preflight or is killed at dispatch by the server's
#: ``exceed_context_size_error``; ``"compact-or-abstain"`` drops droppable
#: blocks in the declared order (``rails.context_fit.DROP_ORDER``) and, when
#: even that is not enough, retains the row under a ``context_compaction``
#: terminal disposition. Like E13's it renders NO request byte on a row that
#: fits, so its ON arm is free to be the default of every new cell. See
#: ``rails.context_fit``.
#: ``native_episode.knowledge_index`` (item E21 -- the knowledge index, not the
#: Earnings-21 carrier -- 2026-09-19, owner decisions 48 and 50) is the
#: ELEVENTH. It arms the knowledge INDEX -- a stable, addressable,
#: ordered catalogue of the task's knowledge space rendered into the CONSTANT
#: prefix at a declared granularity -- together with the per-row POINTER block
#: and BOUNDED EXPANSION that replace today's "render the full text of
#: everything retrieved". It is ONE key and not two on two measured grounds:
#: an index-only arm adds about 3,526 tokens to every contact and forecloses
#: the np5/np6 serving geometries, while a pointer-only arm removes the card
#: text while the model has no index to resolve the pointers against. The
#: prefix and the pointers are two halves of one mechanism -- the index is the
#: referent and the pointer is the reference -- and one key keeps the cell
#: one-factor. It belongs here rather than in ``run`` because it MOVES REQUEST
#: BYTES (the system message gains the index, the evidence block becomes
#: pointers plus a budgeted expansion), so no ``request-bytes-identical``
#: falsifier can exist for it; rather than in the ``knowledge_views`` table
#: because it changes how a phase's supply is RENDERED, not what is selected;
#: and rather than folded into ``native_episode.solver_hints`` or
#: ``reviewer_audit`` because those are per-row blocks at one boundary and
#: this is the prefix every contact of every row carries. The paired
#: ``native_episode.roles.<role>.knowledge_index_budget`` override table is
#: part of the same module and is refused without it, exactly as E18's
#: ``roles.acquisition`` is. See ``rails.knowledge_index`` and
#: ``core.base.KNOWLEDGE_INDEX_ORDERINGS``.
#: ``native_episode.react_exhaustion_policy`` (item E22 -- the ReAct-exhaustion
#: disposition, not the Earnings-22 carrier -- 2026-09-19) is the TWELFTH, and
#: the THIRD FAILURE MODE after E13's and E20's. It decides what a TOOL role's
#: ReAct loop does when it spends its whole iteration budget on tool calls and
#: never produces an answer: ``"raise"`` -- the key absent or written out loud
#: -- is the pre-E22 behaviour, ``reproduction.ojw.native_episode._ApplyRole``
#: refusing the non-answer with ``NativeEpisodeError: <stage> node did not
#: return an answer`` and taking the flight with it (the B8b-anchor arm,
#: 2 of 410 Reviewer visits, 2,016 contacts lost);
#: ``"continue-without-answer"`` ends that visit with NO finding -- the row
#: continues through the Planner and delivers exactly as it would have -- and
#: records a ``react_exhaustion`` VISIT disposition naming the role, the
#: iterations it spent, every call's tool id and argument digest, whether
#: those calls were identical, and the last observation's digest. Like E13's
#: and E20's it renders NO request byte on a row whose roles answer (nothing
#: is retried and no extra contact is made), so its ON arm is free to be the
#: default of every new cell. See
#: ``reproduction.ojw.native_roles.REACT_EXHAUSTION_OUTPUT`` and
#: ``scripts/checks/finite_completion_policy_check.py``.
#: ``native_episode.reviewer_verdict`` (item E37, owner decision 84,
#: 2026-09-22) is the THIRTEENTH. It decides whether the Reviewer's verdict is
#: parsed as a closed set of primitives: absent -- every spec written before
#: E37 and every OFF arm -- means ``reproduction.ojw.native_episode._ApplyRole``
#: parses nothing on the Reviewer's branch and writes no ``reviewer_verdicts``
#: mark, so the receipt is byte-identical to its pre-E37 self; armed, its
#: value is ``{"vocabulary": "saea-review-primitives-v1"}`` -- the ONE
#: registered vocabulary id (``rails.review_primitives.
#: REVIEW_PRIMITIVES_VOCABULARY``), refused by ``rails.native_episode_config.
#: load_native_episode_config`` when any other id is named -- and every
#: Reviewer visit's response is parsed against
#: ``rails.review_primitives.parse_review_primitive`` and recorded as one mark
#: (``legal`` / ``review_verdict_illegal`` / ``react_exhaustion``) in
#: ``native_episode_receipt.reviewer_verdicts``. Like E13's, E20's and E22's
#: keys it renders NO request byte of its own: the parse happens strictly
#: AFTER the Reviewer's response is already in hand, and the raw text still
#: renders into the Planner's query exactly as it would unarmed (the verdict
#: is a recommendation, never a route -- the Planner keeps routing authority).
#: It belongs here rather than in the ``judges`` table because that table
#: wraps a phase's ``phase_review`` entry (owner Decision 11-C's
#: criticism-only Reviewer seat) and this key changes how the SAME Reviewer
#: seat's own completion is READ afterward, exactly as
#: ``native_episode.deliver_normaliser`` and ``native_episode.
#: finite_completion_policy`` are declared inside ``native_episode`` rather
#: than in a per-phase table.
EPISODE_LEVEL_SWITCH_KEYS = frozenset({
    "native_episode.roles.solver",
    "native_episode.review_loop",
    "native_episode.context_policy",
    "native_episode.deliver_normaliser",
    "native_episode.reviewer_audit",
    "native_episode.finite_completion_policy",
    "native_episode.context_fit_policy",
    "native_episode.solver_hints",
    "native_episode.tool_schema_rendering",
    "native_episode.acquisition",
    "native_episode.knowledge_index",
    "native_episode.react_exhaustion_policy",
    "native_episode.reviewer_verdict",
})

#: The top-level key every ``stores``-class switch key names one child of.
KNOWLEDGE_STORES_TABLE = "knowledge_stores"

#: The token a ``stores`` entry declares as ``switch.form`` to be read in the
#: class's SECOND arm form, the store re-pin. Absent, the entry is in the
#: class's first (null) form -- see the class comment above.
STORES_REPIN_FORM = "repin"

#: The two leaves a store re-pin moves, and the only two it may move: the
#: store's ``release`` and its ``snapshot``, each a ``{relpath, sha256}`` pin.
#: ``store_role``, ``phase_supply`` and ``candidate_supply`` are NOT re-pin
#: leaves: a module that moves one of those is not a re-pin of a store, it is
#: a different store block, and it owes its own arm form rather than this one.
STORES_PIN_FIELDS: tuple[str, ...] = ("release", "snapshot")

#: The fields of one pin, exactly as :class:`PinnedFile` spells them.
STORES_PIN_LEAF_FIELDS = frozenset({"relpath", "sha256"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ConfigTableError(RailsError):
    """A config table, or one of its entries, violated the shape this module
    requires. Raised before a run starts and before any contact."""


def _is_null_arm(declared: object) -> bool:
    return declared is None or declared == {}


def _require_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigTableError(f"{field_name} must be a non-empty string")
    return value


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ConfigTableError(f"{field_name} must be a lowercase 64-hex SHA-256")
    return value


def _require_relpath(value: object, *, field_name: str) -> str:
    """A repo-relative POSIX path, under the same refusals ``core.config``
    applies to every other path-shaped config value: no backslash, not
    absolute, no empty or traversal segment."""

    text = _require_text(value, field_name=field_name)
    if "\\" in text:
        raise ConfigTableError(f"{field_name} must not contain a backslash: {text!r}")
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ConfigTableError(f"{field_name} must be relative, got {text!r}")
    if any(part in ("", ".", "..") for part in text.split("/")):
        raise ConfigTableError(
            f"{field_name} contains an empty or traversal segment: {text!r}"
        )
    return text


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigTableError(f"{field_name} must be an object")
    return value


def _reject_unknown_keys(
    entry: Mapping[str, object], known: frozenset[str], *, field_name: str
) -> None:
    extra = sorted(set(entry) - known)
    if extra:
        raise ConfigTableError(
            f"{field_name} carries unknown key(s) {extra}; known keys are "
            f"{sorted(known)}"
        )


def _assert_not_double_declared(values: Mapping[str, object], table: str) -> None:
    """A fragment declares the flat block OR its wrapping table, never both."""

    for flat in WRAPPED_FLAT_KEYS.get(table, ()):
        if flat in values and not _is_null_arm(values.get(flat)):
            raise ConfigTableError(
                f"a fragment declares both {flat!r} and the {table!r} table; the "
                f"{table!r} table WRAPS {flat!r} without changing its bytes, so "
                "declaring both is two spellings of one switch and would give one "
                f"cell two identities -- keep {flat!r} or move it under "
                f"{table!r}, not both"
            )


# ---------------------------------------------------------------------------
# Table 1: observe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PinnedFile:
    """A repo-relative artifact pinned by its exact bytes. Selecting
    different bytes changes the config hash, which is what makes an observe
    mode reproducible."""

    relpath: str
    sha256: str

    def validate(self, *, field_name: str) -> "PinnedFile":
        _require_relpath(self.relpath, field_name=f"{field_name}.relpath")
        _require_sha256(self.sha256, field_name=f"{field_name}.sha256")
        return self

    def as_json(self) -> dict[str, object]:
        return {"relpath": self.relpath, "sha256": self.sha256}


@dataclass(frozen=True)
class ReListenSpec:
    """The selective re-listen entry: WHERE the flags come from, and W2's own
    :class:`rails.observe.ObserveConfig` for the margin, the per-sample budget
    and the derivation kind.

    ``judges`` and ``fixture`` are mutually exclusive and one is required: a
    re-listen that has no flag source re-listens to nothing. ``judges`` is
    spelled as a LIST of ``core.base.JUDGES`` ids on purpose -- that is the
    key ``scripts/checks/engineering_base_check.py`` already resolves at any
    depth, so the flag source is checked by the same rule as every other
    judge id rather than by a second one.
    """

    config: ObserveConfig
    judges: tuple[str, ...] = ()
    fixture: PinnedFile | None = None

    def validate(self, *, field_name: str) -> "ReListenSpec":
        self.config.validate()
        if bool(self.judges) == (self.fixture is not None):
            raise ConfigTableError(
                f"{field_name} must declare exactly one flag source: 'judges' (a "
                "list of registered judge ids) or 'fixture' (a pinned flag "
                "document); a re-listen with neither re-listens to nothing, and a "
                "re-listen with both has two sources of truth"
            )
        seen: set[str] = set()
        for index, judge_id in enumerate(self.judges):
            _require_text(judge_id, field_name=f"{field_name}.judges[{index}]")
            if judge_id in seen:
                raise ConfigTableError(
                    f"{field_name}.judges repeats {judge_id!r}; one judge raises its "
                    "flags once"
                )
            seen.add(judge_id)
            try:
                JUDGES.resolve(judge_id)
            except CoreError as error:
                raise ConfigTableError(
                    f"{field_name}.judges[{index}]: {error}"
                ) from None
        if self.fixture is not None:
            self.fixture.validate(field_name=f"{field_name}.fixture")
        return self

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {
            "context_margin_seconds": self.config.context_margin_seconds,
            "max_relistens_per_sample": self.config.max_relistens_per_sample,
            "derivation_kind": self.config.derivation_kind,
        }
        if self.judges:
            document["judges"] = list(self.judges)
        if self.fixture is not None:
            document["fixture"] = self.fixture.as_json()
        return document


@dataclass(frozen=True)
class ObserveModeSpec:
    """One phase's observe row. Every entry is independently nullable, and a
    row that selects no mode at all is refused: it would read as if the
    Observer did something and the cell would carry a key that changes
    nothing."""

    phase: str
    tail_silence_seconds: float | None = None
    unit_plan: PinnedFile | None = None
    relisten: ReListenSpec | None = None

    def validate(self) -> "ObserveModeSpec":
        where = f"observe[{self.phase!r}]"
        _require_text(self.phase, field_name="ObserveModeSpec.phase")
        if self.tail_silence_seconds is not None:
            value = self.tail_silence_seconds
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value != value  # NaN
                or value in (float("inf"), float("-inf"))
            ):
                raise ConfigTableError(
                    f"{where}.tail_silence_seconds must be a finite number, got "
                    f"{value!r}"
                )
            if float(value) < 0:
                raise ConfigTableError(
                    f"{where}.tail_silence_seconds must be non-negative, got {value!r}"
                )
        if self.unit_plan is not None:
            self.unit_plan.validate(field_name=f"{where}.unit_plan")
        if self.relisten is not None:
            self.relisten.validate(field_name=f"{where}.relisten")
        if (
            self.tail_silence_seconds is None
            and self.unit_plan is None
            and self.relisten is None
        ):
            raise ConfigTableError(
                f"{where} selects no observe mode; an all-null row is the table's "
                "null arm written the long way -- drop the row (or the whole "
                "'observe' block) instead, so the OFF arm and today's graph carry "
                "one config hash"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        document: dict[str, object] = {"phase": self.phase}
        if self.tail_silence_seconds is not None:
            document["tail_silence_seconds"] = float(self.tail_silence_seconds)
        if self.unit_plan is not None:
            document["unit_plan"] = self.unit_plan.as_json()
        if self.relisten is not None:
            document["relisten"] = self.relisten.as_json()
        return document


def _load_pinned_file(entry: object, *, field_name: str) -> PinnedFile:
    document = _require_mapping(entry, field_name=field_name)
    _reject_unknown_keys(document, _PINNED_FILE_KEYS, field_name=field_name)
    missing = sorted(_PINNED_FILE_KEYS - set(document))
    if missing:
        raise ConfigTableError(
            f"{field_name} must carry {sorted(_PINNED_FILE_KEYS)}; missing {missing}"
        )
    return PinnedFile(
        relpath=document["relpath"], sha256=document["sha256"]
    ).validate(field_name=field_name)


def _load_relisten(entry: object, *, field_name: str) -> ReListenSpec:
    document = _require_mapping(entry, field_name=field_name)
    _reject_unknown_keys(document, _RELISTEN_KEYS, field_name=field_name)
    for required in ("context_margin_seconds", "max_relistens_per_sample"):
        if required not in document:
            raise ConfigTableError(f"{field_name} must declare {required!r}")
    judges = document.get("judges")
    if judges is not None and (
        isinstance(judges, (str, bytes)) or not isinstance(judges, (list, tuple))
    ):
        raise ConfigTableError(
            f"{field_name}.judges must be a list of registered judge ids, got "
            f"{judges!r}"
        )
    fixture = document.get("fixture")
    return ReListenSpec(
        config=ObserveConfig(
            context_margin_seconds=document["context_margin_seconds"],
            max_relistens_per_sample=document["max_relistens_per_sample"],
            derivation_kind=document.get("derivation_kind", "recut-span"),
        ),
        judges=tuple(judges or ()),
        fixture=(
            None
            if fixture is None
            else _load_pinned_file(fixture, field_name=f"{field_name}.fixture")
        ),
    ).validate(field_name=field_name)


def load_observe_table(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, ObserveModeSpec]:
    """Parse the fragment's ``observe`` table against ``program``.

    The null arm (absent, ``null`` or ``{}``) returns an empty mapping: no
    phase declares an observe mode and the loop's observation is today's
    fixed window, byte for byte. Present: refuses a non-object; a phase the
    program does not declare; an unknown key in a row; an all-null row; a
    negative or non-finite tail; an unpinned unit plan; a re-listen with no
    flag source, with both, or with an unregistered judge id; and a fragment
    that ALSO carries the Earnings obs-loop's flat observe knobs.

    Returned in the program's own phase order, so a receipt reads the way the
    program runs.
    """

    program.validate()
    declared = values.get(OBSERVE_TABLE)
    if _is_null_arm(declared):
        return {}
    legacy = sorted(key for key in LEGACY_OBSERVE_KEYS if values.get(key) is not None)
    if legacy:
        raise ConfigTableError(
            f"a fragment declares the 'observe' table and the flat obs-loop key(s) "
            f"{legacy}; those keys are the pre-table spelling of the same observe "
            "modes (reproduction.obs_loop) and declaring both is two switches for "
            "one module -- keep the flat keys on the obs-agent-loop policy path, or "
            "move them into 'observe', not both"
        )
    table = _require_mapping(declared, field_name="'observe'")
    known = set(program.phase_names())
    unknown = sorted(set(table) - known)
    if unknown:
        raise ConfigTableError(
            f"observe names phase(s) {unknown} that program {program.program_id!r} "
            f"does not declare; its phases are {sorted(known)}"
        )
    specs: dict[str, ObserveModeSpec] = {}
    for phase in program.phases:
        if phase.name not in table:
            continue
        where = f"observe[{phase.name!r}]"
        entry = _require_mapping(table[phase.name], field_name=where)
        _reject_unknown_keys(entry, _OBSERVE_ENTRY_KEYS, field_name=where)
        unit_plan = entry.get("unit_plan")
        relisten = entry.get("relisten")
        specs[phase.name] = ObserveModeSpec(
            phase=phase.name,
            tail_silence_seconds=entry.get("tail_silence_seconds"),
            unit_plan=(
                None
                if unit_plan is None
                else _load_pinned_file(unit_plan, field_name=f"{where}.unit_plan")
            ),
            relisten=(
                None
                if relisten is None
                else _load_relisten(relisten, field_name=f"{where}.relisten")
            ),
        ).validate()
    return specs


# ---------------------------------------------------------------------------
# Table 2: knowledge_views
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeViewsTable:
    """The wrapped E1/E6 specs, produced by the SAME loaders the flat blocks
    use, from the SAME bytes."""

    material: Mapping[str, PhaseMaterialSpec] = field(default_factory=dict)
    supply: Mapping[str, PhaseSupplySpec] = field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        return {
            "material": sorted(self.material),
            "supply": sorted(self.supply),
        }


def unwrap_knowledge_views(values: Mapping[str, object]) -> dict[str, object]:
    """The flat ``{phase_material, phase_supply}`` mapping a
    ``knowledge_views`` table is equivalent to.

    Bytes in, bytes out: each phase's ``material`` / ``supply`` object is
    carried over UNCHANGED, which is what lets the existing loaders and the
    existing engineering-base-check rules read the table with no change of
    their own. A fragment that declares no table gets its flat blocks back
    verbatim, so this function is the one place the two spellings meet.
    """

    declared = values.get(KNOWLEDGE_VIEWS_TABLE)
    if _is_null_arm(declared):
        return {
            "phase_material": values.get("phase_material"),
            "phase_supply": values.get("phase_supply"),
        }
    _assert_not_double_declared(values, KNOWLEDGE_VIEWS_TABLE)
    table = _require_mapping(declared, field_name="'knowledge_views'")
    material: dict[str, object] = {}
    supply: dict[str, object] = {}
    for phase_name in sorted(table):
        where = f"knowledge_views[{phase_name!r}]"
        entry = _require_mapping(table[phase_name], field_name=where)
        _reject_unknown_keys(entry, _KNOWLEDGE_VIEW_ENTRY_KEYS, field_name=where)
        if entry.get("material") is not None:
            material[phase_name] = entry["material"]
        if entry.get("supply") is not None:
            supply[phase_name] = entry["supply"]
    return {
        "phase_material": material or None,
        "phase_supply": supply or None,
    }


def load_knowledge_views_table(
    values: Mapping[str, object], program: PhaseProgram
) -> KnowledgeViewsTable:
    """Parse the fragment's ``knowledge_views`` table (or its flat
    ``phase_material`` / ``phase_supply`` equivalent) against ``program``.

    Delegates verbatim to ``rails.phase_material.load_phase_material_specs``
    and ``rails.phase_supply.load_phase_supply_specs``: every refusal those
    two already make is this table's refusal too, with no second validator to
    drift from them. ``material`` is required for every phase of a phase
    program (their rule, not a new one); ``supply`` is per-phase optional and
    its absence IS the retrieval provider's OFF arm.
    """

    program.validate()
    flat = unwrap_knowledge_views(values)
    material = (
        load_phase_material_specs(flat, program)
        if flat.get("phase_material") is not None
        else {}
    )
    supply = load_phase_supply_specs(flat, program)
    return KnowledgeViewsTable(material=material, supply=supply)


# ---------------------------------------------------------------------------
# Table 3: judges
# ---------------------------------------------------------------------------


def unwrap_judges(values: Mapping[str, object]) -> dict[str, object]:
    """The flat ``{phase_review}`` mapping a ``judges`` table is equivalent
    to -- the entry objects carried over unchanged."""

    declared = values.get(JUDGES_TABLE)
    if _is_null_arm(declared):
        return {"phase_review": values.get("phase_review")}
    _assert_not_double_declared(values, JUDGES_TABLE)
    table = _require_mapping(declared, field_name="'judges'")
    for phase_name in sorted(table):
        entry = _require_mapping(
            table[phase_name], field_name=f"judges[{phase_name!r}]"
        )
        _reject_unknown_keys(
            entry, _JUDGES_ENTRY_KEYS, field_name=f"judges[{phase_name!r}]"
        )
    return {"phase_review": dict(table)}


def load_judges_table(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseReviewSpec]:
    """Parse the fragment's ``judges`` table (or its flat ``phase_review``
    equivalent) against ``program``, through W1's own loader.

    The null arm returns an empty mapping: no phase is reviewed and the cell
    is byte-identical to the same cell with no Reviewer -- which is exactly
    what makes "Reviewer on versus off" a paired arm rather than a rebuild.
    """

    return load_phase_review_specs(unwrap_judges(values), program)


# ---------------------------------------------------------------------------
# Table 4: toolkits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolkitSelection:
    """Which W3 task-type toolkit row is armed, and for which agent roles.

    Run-scoped rather than per-phase: W3's table is keyed by task type (a
    property of the carrier, not of a phase), and a role's toolkit is the set
    of tools that role may call for the whole episode.
    """

    task_type: str
    roles: tuple[str, ...]
    tools_by_role: Mapping[str, tuple[str, ...]]

    def as_json(self) -> dict[str, object]:
        return {
            "task_type": self.task_type,
            "roles": list(self.roles),
            "tools_by_role": {
                role: list(self.tools_by_role[role]) for role in sorted(self.tools_by_role)
            },
        }


def load_toolkits_table(
    values: Mapping[str, object], *, table: Any | None = None
) -> ToolkitSelection | None:
    """Parse the fragment's ``toolkits`` table against W3's committed table.

    The null arm returns ``None``: no tool is armed and the loop is today's
    loop, which is also W3's own state (no tool is wired into a running loop
    yet). Present: refuses a non-object; an unknown key; a missing or unknown
    ``task_type``; an empty, repeating or unknown ``roles`` entry; and a role
    the selected task type does not declare. ``table`` is the seam a test or
    a caller holding its own table uses; the default is the committed
    ``configs/toolkit/task-toolkits-v1.json``.
    """

    declared = values.get(TOOLKITS_TABLE)
    if _is_null_arm(declared):
        return None
    entry = _require_mapping(declared, field_name="'toolkits'")
    _reject_unknown_keys(entry, _TOOLKITS_ENTRY_KEYS, field_name="'toolkits'")
    task_type = _require_text(entry.get("task_type"), field_name="toolkits.task_type")
    from .tools import TOOLKIT_ROLES, ToolCatalogError, default_toolkit_table

    resolved = default_toolkit_table() if table is None else table
    try:
        toolkit = resolved.for_task(task_type)
    except ToolCatalogError as error:
        raise ConfigTableError(f"toolkits.task_type: {error}") from None
    declared_roles = entry.get("roles")
    if declared_roles is None:
        roles = tuple(role for role in TOOLKIT_ROLES if role in toolkit.tools_by_role)
    else:
        if isinstance(declared_roles, (str, bytes)) or not isinstance(
            declared_roles, (list, tuple)
        ):
            raise ConfigTableError(
                f"toolkits.roles must be a list of agent roles, got {declared_roles!r}"
            )
        if not declared_roles:
            raise ConfigTableError(
                "toolkits.roles is empty; a selection that arms no role arms nothing "
                "-- write \"toolkits\": null, which is the table's null arm and "
                "carries the same config hash as no table at all"
            )
        seen: set[str] = set()
        for index, role in enumerate(declared_roles):
            _require_text(role, field_name=f"toolkits.roles[{index}]")
            if role in seen:
                raise ConfigTableError(f"toolkits.roles repeats {role!r}")
            seen.add(role)
            if role not in TOOLKIT_ROLES:
                raise ConfigTableError(
                    f"toolkits.roles[{index}] is {role!r}; the roles that may call a "
                    f"tool are {list(TOOLKIT_ROLES)} (the Solver is the frozen core "
                    "and calls none)"
                )
            if role not in toolkit.tools_by_role:
                raise ConfigTableError(
                    f"toolkits.roles[{index}] is {role!r} but task type "
                    f"{task_type!r} declares no such role"
                )
        roles = tuple(role for role in TOOLKIT_ROLES if role in seen)
    from .experience_memory_runtime import CORRECTIVE_MEMORY_TOOL

    phase_tools = values.get("phase_tools")
    memory_action = isinstance(phase_tools, Mapping) and any(
        isinstance(spec, Mapping)
        and isinstance(spec.get("allowed_tools"), (list, tuple))
        and CORRECTIVE_MEMORY_TOOL in spec["allowed_tools"]
        for spec in phase_tools.values()
    )
    memory_armed = values.get("experience_memory") is not None and memory_action

    def selected_tools(role: str) -> tuple[str, ...]:
        tools = toolkit.tools_for(role)
        if memory_armed:
            return tools
        return tuple(tool for tool in tools if tool != CORRECTIVE_MEMORY_TOOL)

    return ToolkitSelection(
        task_type=task_type,
        roles=roles,
        tools_by_role={role: selected_tools(role) for role in roles},
    )


# ---------------------------------------------------------------------------
# The bundle, and the flattened-config diff the admission gate reads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigTables:
    """All four tables of one composed config, validated together."""

    observe: Mapping[str, ObserveModeSpec] = field(default_factory=dict)
    knowledge_views: KnowledgeViewsTable = field(default_factory=KnowledgeViewsTable)
    judges: Mapping[str, PhaseReviewSpec] = field(default_factory=dict)
    toolkits: ToolkitSelection | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "schema": CONFIG_TABLES_SCHEMA,
            "judges": {
                phase: self.judges[phase].as_json() for phase in sorted(self.judges)
            },
            "knowledge_views": self.knowledge_views.as_json(),
            "observe": {
                phase: self.observe[phase].as_json() for phase in sorted(self.observe)
            },
            "toolkits": (
                None if self.toolkits is None else self.toolkits.as_json()
            ),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())


def load_config_tables(
    values: Mapping[str, object], program: PhaseProgram, *, toolkit_table: Any | None = None
) -> ConfigTables:
    """Load all four tables of one composed config, fail-closed."""

    return ConfigTables(
        observe=load_observe_table(values, program),
        knowledge_views=load_knowledge_views_table(values, program),
        judges=load_judges_table(values, program),
        toolkits=load_toolkits_table(values, table=toolkit_table),
    )


def flatten_config(values: Mapping[str, object], *, prefix: str = "") -> dict[str, object]:
    """A composed config as ``{dotted.path: leaf}``.

    Nested objects are walked; every other value (including a list) is a
    leaf, so a changed list shows up as ONE changed key rather than as a
    diff of its elements. This is the view the module-admission proof reads:
    ON and OFF of one module must differ in exactly one of these keys.
    """

    flat: dict[str, object] = {}
    for key in values:
        path = f"{prefix}{key}"
        value = values[key]
        if isinstance(value, Mapping):
            if not value:
                flat[path] = {}
                continue
            flat.update(flatten_config(value, prefix=f"{path}."))
        else:
            flat[path] = value
    return flat


def config_key_diff(
    on: Mapping[str, object], off: Mapping[str, object]
) -> tuple[str, ...]:
    """The sorted dotted paths on which two composed configs differ.

    A module is expressible as one config key exactly when this returns a
    one-element tuple for its ON and OFF arms -- the machine form of the
    design note's "one config key, never a second code path".
    """

    flat_on = flatten_config(on)
    flat_off = flatten_config(off)
    return tuple(
        sorted(
            key
            for key in set(flat_on) | set(flat_off)
            if key not in flat_on or key not in flat_off or flat_on[key] != flat_off[key]
        )
    )


def switch_key(on: Mapping[str, object], off: Mapping[str, object]) -> str:
    """The ONE config key that distinguishes two arms, or a refusal.

    A key here is a dotted path, and an object-valued key changes several
    leaves at once (``observe.<phase>.unit_plan`` moves both its ``relpath``
    and its ``sha256``). So the machine form of "one config key" is: every
    leaf on which the two composed configs differ lies under ONE common
    dotted path, and that path resolves in at least one of the two arms.

    That is exactly the property the design note's admission gate needs and
    exactly what today's flat spellings lack: ``obs_unit_plan`` and
    ``obs_unit_plan_sha256`` share no dotted prefix, and neither do a
    ``policy`` swap and the post-processor pair that rides with it, so both
    are refused here by construction rather than by opinion.

    Raises :class:`ConfigTableError` when the arms are identical, or when
    their difference is more than one key.
    """

    diff = config_key_diff(on, off)
    if not diff:
        raise ConfigTableError(
            "the two arms compose to the same config; an ON/OFF pair that moves "
            "no key is not a contrast"
        )
    segments = [key.split(".") for key in diff]
    shared: list[str] = []
    for index in range(min(len(parts) for parts in segments)):
        candidate = segments[0][index]
        if any(parts[index] != candidate for parts in segments):
            break
        shared.append(candidate)
    if not shared:
        raise ConfigTableError(
            f"the two arms differ in {len(diff)} unrelated config keys {list(diff)}; "
            "a module whose OFF arm moves more than one key is not one switch, and "
            "its ON/OFF pair is not a twin"
        )
    path = ".".join(shared)
    if not any(_resolves(values, shared) for values in (on, off)):
        raise ConfigTableError(
            f"the shared path {path!r} of the changed keys {list(diff)} resolves in "
            "neither arm"
        )
    return path


def _resolves(values: Mapping[str, object], path: Sequence[str]) -> bool:
    cursor: object = values
    for segment in path:
        if not isinstance(cursor, Mapping) or segment not in cursor:
            return False
        cursor = cursor[segment]
    return True


def resolve_switch_key(table: str, key: str) -> str:
    """The table entry key a ``switch.key`` declaration names, or a refusal.

    ``docs/receipts/harness-admission.json`` records, per admitted module,
    the ONE config key that switches it -- as a dotted path whose phase
    segment may be the placeholder ``<phase>`` because a module's admission
    is about the module, not about one program's phase names. The path must
    start with its table and must name one of that table's entry keys
    somewhere after it, which is what makes "the key resolves in a table" a
    machine question:

    * ``observe.<phase>.tail_silence_seconds`` -> ``tail_silence_seconds``
    * ``knowledge_views.<phase>.material.state_fill`` -> ``material``
    * ``judges.<phase>.judges`` -> ``judges``
    * ``toolkits.task_type`` -> ``task_type``
    """

    if table not in CONFIG_TABLE_NAMES:
        raise ConfigTableError(
            f"unknown config table {table!r}; the tables are {list(CONFIG_TABLE_NAMES)}"
        )
    segments = key.split(".") if isinstance(key, str) else []
    if not segments or segments[0] != table:
        raise ConfigTableError(
            f"switch key {key!r} does not start with its table {table!r}; a switch "
            "that names no table is not one config key"
        )
    entry_keys = table_entry_keys(table)
    named = [segment for segment in segments[1:] if segment in entry_keys]
    if not named:
        raise ConfigTableError(
            f"switch key {key!r} names no entry of the {table!r} table; its entry "
            f"keys are {list(entry_keys)}"
        )
    return named[0]


def resolve_run_switch_key(key: str) -> str:
    """The per-run driver key a ``run``-class ``switch.key`` names, or a refusal.

    Unlike a table key this one is FLAT -- ``obs_prefetch_depth``, not
    ``run.obs_prefetch_depth`` -- because that is the spelling the fragment
    actually carries and a switch declaration that does not match the bytes
    is not a switch. The allowlist is closed on purpose (see
    :data:`RUN_LEVEL_SWITCH_KEYS`).
    """

    if not isinstance(key, str) or not key.strip():
        raise ConfigTableError("a run-level switch key must be a non-empty string")
    if "." in key:
        raise ConfigTableError(
            f"run-level switch key {key!r} is dotted; a run-level key is a FLAT "
            "config key, which is the spelling the fragment carries"
        )
    if key not in RUN_LEVEL_SWITCH_KEYS:
        raise ConfigTableError(
            f"run-level switch key {key!r} is not admitted; the run class is a "
            f"closed allowlist {sorted(RUN_LEVEL_SWITCH_KEYS)} and a module that "
            "changes the request the core sees belongs in a config table, not here"
        )
    return key


def is_run_null_arm(value: object) -> bool:
    """Whether ``value`` is the ``run`` class's null arm (absent, or the
    driver's documented default)."""

    if value is None:
        return True
    if isinstance(value, bool):
        return False
    return isinstance(value, int) and value == 0


def resolve_episode_switch_key(key: str) -> str:
    """The ``episode``-class switch key a ``switch.key`` declaration names,
    or a refusal.

    Unlike a table key this one is the literal dotted path a fragment
    carries under ``native_episode`` (not ``"episode.<key>"``), exactly as a
    ``run``-class key is the literal flat spelling rather than
    ``"run.<key>"``. The allowlist is closed on purpose: see
    :data:`EPISODE_LEVEL_SWITCH_KEYS`.
    """

    if not isinstance(key, str) or not key.strip():
        raise ConfigTableError("an episode switch key must be a non-empty string")
    if not key.startswith(f"{NATIVE_EPISODE_TOP_LEVEL_KEY}."):
        raise ConfigTableError(
            f"episode switch key {key!r} does not start with "
            f"{NATIVE_EPISODE_TOP_LEVEL_KEY + '.'!r}; an episode-class module's one "
            "key is a dotted path under the native_episode block, because that "
            "block -- not one of the four per-phase tables -- is what the module "
            "actually changes"
        )
    if key not in EPISODE_LEVEL_SWITCH_KEYS:
        raise ConfigTableError(
            f"episode switch key {key!r} is not admitted; the episode class is a "
            f"closed allowlist {sorted(EPISODE_LEVEL_SWITCH_KEYS)} and a module that "
            "reaches for a new native_episode sub-path is a code change with a "
            "test, not a receipt edit"
        )
    return key


def is_episode_null_arm(key: str, value: object) -> bool:
    """Whether ``value`` is ``key``'s own OFF form in the ``episode`` class.

    Each admitted key has its own null shape, because the three today mean
    different things: ``native_episode.roles.solver``'s OFF is the historical
    Solver role (no grouped-sampling fields, or ``samples`` explicitly 1);
    ``native_episode.review_loop``'s OFF is the literal marker ``"off"`` (or
    its absence from a fragment that never declares the marker at all);
    ``native_episode.context_policy``'s OFF is level L0 -- the key absent, the
    literal ``"raw"``, or an object whose effective level is ``raw`` at every
    boundary (``rails.node_context_binding.is_node_context_null_arm``, which
    ``load_native_episode_config`` applies too, so an all-raw declaration
    reaches the runtime as no policy at all and renders the pre-policy bytes);
    ``native_episode.deliver_normaliser``'s OFF is the key's absence, because
    a delivery node is either absent or armed (E11);
    ``native_episode.reviewer_audit``'s OFF is the key's absence for the same
    reason (E12), and ``native_episode.solver_hints``'s for that same reason
    (E14), leaving the ``solver:candidate-hypothesis`` boundary at its
    pre-E14 bytes;
    ``native_episode.finite_completion_policy``'s OFF is the key's absence OR
    its explicit default ``"raise"`` (E13), because the parser reads the two
    the same way -- a context block is either absent or rendered, and with it
    absent the ``reviewer:current-draft`` boundary renders exactly its
    pre-E12 bytes; ``native_episode.tool_schema_rendering``'s OFF is the
    key's absence OR its explicit default ``"per-role"`` (E17), for the same
    reason; ``native_episode.context_fit_policy``'s OFF is the key's absence
    OR its explicit default ``"raise"`` (E20), which the parser reads
    identically; and ``native_episode.knowledge_index``'s OFF is the key's
    ABSENCE (E21), because an index is either rendered into the constant
    prefix or it is not -- with the key absent the system message carries its
    pre-E21 contract fill and the evidence block the selected values' own
    full text; and ``native_episode.react_exhaustion_policy``'s OFF is the
    key's absence OR its explicit default ``"raise"`` (item E22 -- the
    ReAct-exhaustion disposition, not the Earnings-22 carrier), for exactly
    the reason E13's and E20's are; and ``native_episode.reviewer_verdict``'s
    OFF is the key's ABSENCE (item E37, owner decision 84), because the
    primitive-verdict parse is either armed or it is not -- with the key
    absent the Reviewer's ``_ApplyRole`` branch writes no
    ``reviewer_verdicts`` mark at all, for the same reason
    ``deliver_normaliser``'s and ``acquisition``'s OFF arms are the key's
    absence.
    """

    if key == "native_episode.context_policy":
        # Function-local: rails.node_context_binding imports core.base and the
        # policy module, and this table module is imported by everything.
        from .node_context_binding import (  # noqa: PLC0415
            is_node_context_null_arm,
        )

        return is_node_context_null_arm(value)
    if key == "native_episode.roles.solver":
        if value is None:
            return True
        if not isinstance(value, Mapping):
            return False
        return (
            value.get("samples", 1) == 1
            and value.get("decoding_overrides") is None
            and value.get("commit") is None
        )
    if key == "native_episode.review_loop":
        return value is None or value == "off"
    if key == "native_episode.deliver_normaliser":
        # E11: the node is ABSENT or it is armed -- there is no third shape.
        # The OFF arm therefore renders exactly the pre-key delivered bytes
        # (and, request-side, exactly the pre-key request bytes, since the
        # node runs after every contact of the episode is already made).
        return value is None
    if key == "native_episode.finite_completion_policy":
        # E13: the OFF arm is the key's ABSENCE or its explicit default
        # ``"raise"`` -- the two spellings of the pre-E13 behaviour, which
        # ``rails.native_episode_config.load_native_episode_config`` reads
        # identically, so a fragment that writes the default out loud composes
        # the same episode as one that omits it. Any other value is the armed
        # arm.
        return value is None or value == "raise"
    if key == "native_episode.context_fit_policy":
        # E20 (2026-09-19): the same OFF semantics E13's key has -- the
        # key's ABSENCE or its explicit default ``"raise"``, which
        # ``rails.native_episode_config.load_native_episode_config`` reads
        # identically. Like E13's it renders NO request byte on a row that
        # fits, so its ON arm moves nothing until a request is actually
        # wider than the live slot.
        from .context_fit import is_context_fit_null_arm  # noqa: PLC0415

        return is_context_fit_null_arm(value)
    if key == "native_episode.reviewer_audit":
        # E12: the block is ABSENT or it is rendered. Function-local for the
        # same reason the context_policy branch is: rails.node_context_binding
        # imports core.base and the policy module, and this table module is
        # imported by everything.
        from .node_context_binding import (  # noqa: PLC0415
            is_reviewer_audit_null_arm,
        )

        return is_reviewer_audit_null_arm(value)
    if key == "native_episode.solver_hints":
        # E14: the same OFF semantics as the audit's -- the block is ABSENT
        # or it is rendered, and with the key absent the
        # solver:candidate-hypothesis boundary renders exactly its pre-E14
        # bytes.
        from .node_context_binding import (  # noqa: PLC0415
            is_solver_hints_null_arm,
        )

        return is_solver_hints_null_arm(value)
    if key == "native_episode.tool_schema_rendering":
        # E17: the OFF arm is the key's ABSENCE or its explicit default
        # ``"per-role"`` -- the two spellings of the pre-E17 rendering, which
        # ``rails.native_episode_config.load_native_episode_config`` reads
        # identically, so a fragment that writes the default out loud
        # composes the same episode as one that omits it. ``"constant"`` is
        # the one armed value.
        return value is None or value == "per-role"
    if key == "native_episode.acquisition":
        # E18: the node is ABSENT or it is armed -- there is no third shape.
        # With the key absent no acquisition role may be declared
        # (``rails.native_episode_config``), no acquisition node is built and
        # the Planner's ACQUIRE names no registered action, which is exactly
        # the E15 retained-row disposition the OFF arm must reproduce.
        return value is None
    if key == "native_episode.knowledge_index":
        # E21: the index is ABSENT or it is rendered -- there is no third
        # shape. With the key absent the system message carries exactly its
        # pre-E21 contract fill, the evidence block carries exactly the
        # selected values' full text, and the receipt carries no block, which
        # is the byte-identity falsifier E11/E12/E14/E17/E18 all carry.
        from .knowledge_index import is_knowledge_index_null_arm  # noqa: PLC0415

        return is_knowledge_index_null_arm(value)
    if key == "native_episode.react_exhaustion_policy":
        # Item E22 (the ReAct-exhaustion disposition, not the Earnings-22
        # carrier): the same OFF semantics E13's and E20's keys have -- the
        # key's ABSENCE or its explicit default ``"raise"``, which
        # ``rails.native_episode_config.load_native_episode_config`` reads
        # identically, so a fragment that writes the abort default out loud
        # composes the same episode as one that omits it.
        # ``"continue-without-answer"`` is the one armed value.
        return value is None or value == "raise"
    if key == "native_episode.reviewer_verdict":
        # Item E37 (owner decision 84): the block is ABSENT or it is armed --
        # there is no third shape, exactly as native_episode.deliver_normaliser's
        # and native_episode.acquisition's own OFF arms are the key's absence.
        return value is None
    raise ConfigTableError(f"unknown episode switch key {key!r}")


def resolve_stores_switch_key(key: str) -> str:
    """The ``stores``-class switch key a ``switch.key`` declaration names, or
    a refusal: ``knowledge_stores.<store_id>``, naming the whole named store
    block a module adds -- not one ``knowledge_views`` entry, because
    ``knowledge_views`` wraps a PHASE's ``phase_material``/``phase_supply``
    (:data:`WRAPPED_FLAT_KEYS`) and a store is a different object: its own
    release/snapshot pins plus its own supply.
    """

    if not isinstance(key, str) or not key.strip():
        raise ConfigTableError("a stores switch key must be a non-empty string")
    segments = key.split(".")
    if (
        len(segments) != 2
        or segments[0] != KNOWLEDGE_STORES_TABLE
        or not segments[1].strip()
    ):
        raise ConfigTableError(
            f"stores switch key {key!r} must be {KNOWLEDGE_STORES_TABLE!r} followed "
            "by '.' and one non-empty store id; a stores-class module's one key "
            "names the whole named knowledge_stores block the module adds"
        )
    return key


def is_stores_null_arm(value: object) -> bool:
    """A named store's null arm: the store id absent from ``knowledge_stores``
    (or ``knowledge_stores`` itself absent, at the field this key stops at)."""

    return value is None


def resolve_module_switch_key(key: str) -> str:
    """The ``module``-class switch key a ``switch.key`` declaration names, or a
    refusal: exactly ``native_episode.consumption_module``
    (:data:`MODULE_LEVEL_SWITCH_KEYS`)."""

    if not isinstance(key, str) or key not in MODULE_LEVEL_SWITCH_KEYS:
        raise ConfigTableError(
            f"module switch key {key!r} is not admitted; the module class is the closed "
            f"allowlist {sorted(MODULE_LEVEL_SWITCH_KEYS)}"
        )
    return key


def module_block_of(fragment: Mapping[str, object]) -> object:
    """The ``native_episode.consumption_module`` block a fragment declares, or
    ``None`` when it declares none."""

    episode = fragment.get(NATIVE_EPISODE_TOP_LEVEL_KEY)
    if not isinstance(episode, Mapping):
        return None
    return episode.get("consumption_module")


def resolve_phase_tools_switch_key(key: str) -> str:
    """The ``phase_tools``-class switch key a ``switch.key`` declaration names,
    or a refusal: exactly ``phase_tools.<phase>``, where ``<phase>`` is the
    literal phase id whose toolkit the module grants or withdraws.

    The key is the literal spelling the fragment carries (``phase_tools`` is
    a flat top-level mapping keyed by phase id), exactly as a ``stores``-class
    key is the literal ``knowledge_stores.<store_id>``. No ``<phase>``
    placeholder is accepted here, because a toolkit's admission IS about one
    role: the Reviewer's task-contract tool and a Planner toolkit are two
    modules, not one module in two phases.
    """

    if not isinstance(key, str) or not key.strip():
        raise ConfigTableError("a phase_tools switch key must be a non-empty string")
    prefix = f"{PHASE_TOOLS_SWITCH_CLASS}."
    if not key.startswith(prefix):
        raise ConfigTableError(
            f"phase_tools switch key {key!r} must be 'phase_tools.<phase>'; the class "
            "names ONE role's toolkit mapping, which the fragment carries flat under "
            "phase_tools keyed by phase id"
        )
    phase = key[len(prefix):]
    if not phase or "." in phase or phase != phase.strip() or phase == "<phase>":
        raise ConfigTableError(
            f"phase_tools switch key {key!r} must name exactly one literal phase id "
            "after 'phase_tools.' (no placeholder, no deeper path)"
        )
    return key


def is_phase_tools_null_arm(value: object) -> bool:
    """A role's toolkit null arm: ``None`` or ``{}`` (the role absent from
    ``phase_tools``, or ``phase_tools`` itself absent, both read by the
    runtime as no tool authority for that role)."""

    return value is None or (isinstance(value, Mapping) and len(value) == 0)


def phase_tools_role_armed(fragment: Mapping[str, object], key: str) -> bool:
    """Whether ``fragment`` grants the role named by the ``phase_tools.<phase>``
    key a non-null toolkit mapping."""

    phase = resolve_phase_tools_switch_key(key).split(".", 1)[1]
    block = fragment.get(PHASE_TOOLS_SWITCH_CLASS)
    if not isinstance(block, Mapping):
        return False
    return not is_phase_tools_null_arm(block.get(phase))


def is_stores_repin_arm(value: object) -> bool:
    """Whether ``value`` is a ``stores``-class RE-PIN arm.

    The class's second arm form (:data:`STORES_REPIN_FORM`): a mapping
    carrying EXACTLY :data:`STORES_PIN_FIELDS`, each of them a pin of exactly
    ``relpath`` and ``sha256``, under the same refusals every other pinned
    file in this module is read under (a relative POSIX path, no backslash, no
    traversal segment; a lowercase 64-hex digest). Exactly, not at least: an
    arm that also carried ``store_role`` or a supply block would be claiming a
    re-pin while moving something a re-pin does not move.
    """

    if not isinstance(value, Mapping):
        return False
    if set(value) != set(STORES_PIN_FIELDS):
        return False
    for leaf in STORES_PIN_FIELDS:
        pin = value[leaf]
        if not isinstance(pin, Mapping) or set(pin) != set(STORES_PIN_LEAF_FIELDS):
            return False
        try:
            _require_relpath(pin["relpath"], field_name=f"{leaf}.relpath")
            _require_sha256(pin["sha256"], field_name=f"{leaf}.sha256")
        except ConfigTableError:
            return False
    return True


def stores_pins(
    fragment: Mapping[str, object], store_id: str
) -> dict[str, dict[str, str]] | None:
    """The ``release``/``snapshot`` pins ``fragment`` gives ``store_id``, or
    ``None`` when the fragment pins that store no way at all.

    ``None`` covers three cases a caller treats alike -- no ``knowledge_stores``
    block, no such store in it, or a store whose two pins are not both
    well-formed -- because none of them is a fragment that carries THESE pins.
    The return value is a plain, normalized dict, so two fragments' pins
    compare by value.
    """

    if not isinstance(fragment, Mapping):
        return None
    stores = fragment.get(KNOWLEDGE_STORES_TABLE)
    if not isinstance(stores, Mapping):
        return None
    block = stores.get(store_id)
    if not isinstance(block, Mapping):
        return None
    pins: dict[str, dict[str, str]] = {}
    for leaf in STORES_PIN_FIELDS:
        pin = block.get(leaf)
        if not isinstance(pin, Mapping):
            return None
        relpath, sha256 = pin.get("relpath"), pin.get("sha256")
        if not isinstance(relpath, str) or not isinstance(sha256, str):
            return None
        pins[leaf] = {"relpath": relpath, "sha256": sha256}
    return pins if is_stores_repin_arm(pins) else None


def stores_arm_matches(
    fragment: Mapping[str, object], store_id: str, arm: object
) -> bool:
    """Whether ``fragment`` carries ``store_id`` in the arm ``arm`` names.

    The one question a plan-arming rule asks, answered for both of the class's
    arm forms: a NULL arm matches a fragment the named store is absent from,
    and a RE-PIN arm matches a fragment whose store pins exactly those release
    and snapshot bytes. A fragment carrying the OTHER side's pins matches
    neither, which is the point: a plan that still carries the incumbent's
    pins has not armed the successor.
    """

    stores = (
        fragment.get(KNOWLEDGE_STORES_TABLE) if isinstance(fragment, Mapping) else None
    )
    declared = stores.get(store_id) if isinstance(stores, Mapping) else None
    if is_stores_null_arm(arm):
        return is_stores_null_arm(declared)
    if not is_stores_repin_arm(arm):
        return False
    expected = {
        leaf: {"relpath": arm[leaf]["relpath"], "sha256": arm[leaf]["sha256"]}
        for leaf in STORES_PIN_FIELDS
    }
    return stores_pins(fragment, store_id) == expected


def table_entry_keys(table: str) -> tuple[str, ...]:
    """The entry keys ``table`` admits, sorted -- what a switch declaration
    in ``docs/receipts/harness-admission.json`` must name."""

    if table == OBSERVE_TABLE:
        return tuple(sorted(_OBSERVE_ENTRY_KEYS))
    if table == KNOWLEDGE_VIEWS_TABLE:
        return tuple(sorted(_KNOWLEDGE_VIEW_ENTRY_KEYS))
    if table == JUDGES_TABLE:
        return tuple(sorted(_JUDGES_ENTRY_KEYS))
    if table == TOOLKITS_TABLE:
        return tuple(sorted(_TOOLKITS_ENTRY_KEYS))
    raise ConfigTableError(
        f"unknown config table {table!r}; the tables are {list(CONFIG_TABLE_NAMES)}"
    )


__all__ = [
    "CONFIG_TABLES_SCHEMA",
    "CONFIG_TABLE_NAMES",
    "EPISODE_LEVEL_SWITCH_KEYS",
    "EPISODE_SWITCH_CLASS",
    "JUDGES_TABLE",
    "KNOWLEDGE_STORES_TABLE",
    "KNOWLEDGE_VIEWS_TABLE",
    "LEGACY_OBSERVE_KEYS",
    "MODULE_LEVEL_SWITCH_KEYS",
    "MODULE_SWITCH_CLASS",
    "NATIVE_EPISODE_TOP_LEVEL_KEY",
    "NULL_ARMS",
    "OBSERVE_TABLE",
    "PHASE_TOOLS_SWITCH_CLASS",
    "RUN_LEVEL_SWITCH_KEYS",
    "RUN_NULL_ARMS",
    "RUN_SWITCH_CLASS",
    "STORES_PIN_FIELDS",
    "STORES_PIN_LEAF_FIELDS",
    "STORES_REPIN_FORM",
    "STORES_SWITCH_CLASS",
    "SWITCH_CLASS_NAMES",
    "TOOLKITS_TABLE",
    "WRAPPED_FLAT_KEYS",
    "ConfigTableError",
    "ConfigTables",
    "KnowledgeViewsTable",
    "ObserveModeSpec",
    "PinnedFile",
    "ReListenSpec",
    "ToolkitSelection",
    "config_key_diff",
    "flatten_config",
    "switch_key",
    "load_config_tables",
    "load_judges_table",
    "load_knowledge_views_table",
    "load_observe_table",
    "load_toolkits_table",
    "module_block_of",
    "resolve_module_switch_key",
    "is_episode_null_arm",
    "is_run_null_arm",
    "is_phase_tools_null_arm",
    "is_stores_null_arm",
    "is_stores_repin_arm",
    "resolve_episode_switch_key",
    "resolve_run_switch_key",
    "phase_tools_role_armed",
    "resolve_phase_tools_switch_key",
    "resolve_stores_switch_key",
    "resolve_switch_key",
    "stores_arm_matches",
    "stores_pins",
    "table_entry_keys",
    "unwrap_judges",
    "unwrap_knowledge_views",
]
