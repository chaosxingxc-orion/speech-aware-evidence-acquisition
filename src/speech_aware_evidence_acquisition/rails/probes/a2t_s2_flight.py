"""P-A2T Stage-2 supply-arm flight orchestration -- REGISTERED probe
(Stage-2, ``bounded-discovery-probe``):
``docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md``.

Four arms over the SAME 120-sample Stage-1 A0 headroom set (S1'/S2/S4/N0r),
NOT run through ``rails.runner.run_rails_experiment`` -- that runner's
``arms=`` vocabulary is frozen to exactly ``("zero-supply", "supplied")``
(``rails.runner.RAILS_ARMS``); four independently-named, differently-dosed
arms need their own orchestration loop, mirroring
``rails.probes.pslu_flight``'s own precedent (a probe-specific module built
from the SAME shared primitives -- ``CoreClient.complete`` /
``rails.supply.SupplyPacket`` / ``rails.core_client.FrozenCoreClient`` --
rather than a distortion of the frozen two-arm runner contract). Unlike
P-SLU this probe needs no two-phase scenario-prediction pass (the mission
brief: "the P-SLU two-phase pattern minus phase 1"): every sample's own
correctly-selected tool is already known from the CONSUMED Stage-1 A0 read,
so this module's one flight loop just issues the four arms' requests, in a
fixed deterministic order, over ``FrozenCoreClient`` (or, in every test in
this repository, ``rails.core_client.MockCoreClient``).

Registered arms (prereg section 2; the coded arm-string spellings below
avoid the apostrophe in "S1'" the same way ``rails.probes.pslu_flight``
avoids one in "A1'" -- its own arm string is ``"A1p"``, not ``"A1'"``):

- ``S1p`` -- self-supplied single roster: the registry row(s) of the tool(s)
  the core ITSELF named in its own Stage-1 A0 response for that sample.
  Exactly 1 row for the ~75/120 single-intent-tier headroom samples
  (tier1/2/4/5/6/7); >1 row only for the tier3/tier8 multi-intent minority
  where the core's own A0 pass named more than one DISTINCT tool (honestly
  reflecting "the tool(s) the core itself selected" rather than silently
  truncating to one -- see :func:`s1p_tool_names`'s own docstring).
- ``S2`` -- diluted: the correct tool row(s) plus seeded distractor rows,
  total roster size fixed at 9 (the prereg's own "K=9" -- read literally as
  a TOTAL dose of 9 entries: "the correct row + 8 seeded distractor rows
  (K=9)" -- not 9 distractors on top of the correct row(s); see
  :func:`s2_tool_names`).
- ``S4`` -- deranged: exactly ONE wrong tool's row, drawn from a
  fixed-point-free seeded (Sattolo-cycle) mapping over the DISTINCT tool
  identities the 120 headroom samples' own A0 selections cover (never over
  raw sample indices -- see :func:`build_s4_derangement`'s own docstring
  for why a sample-index derangement risks a coincidental self-match when
  two different samples share the same correct tool).
- ``N0r`` -- the noise-floor arm: a zero-supply RE-FLY of 40 seeded,
  tier-proportional samples of the 120 (see :func:`n0r_seeded_draw`). This
  is NOT a supply arm: it reuses
  ``rails.adapters.audio2tool.Audio2ToolAdapter.assemble_prompt(sample,
  None)`` UNCHANGED, so its request is byte-identical to A0's own (the full
  152-row registry, no extra content part) -- exactly the "A0 comparator
  stability" replay the prereg's VOID branch rule needs.

SUPPLY-SHAPE DECISION (bridge mission instruction, item 3): for S1p/S2/S4,
supply REPLACES the ``{tool_schemas}`` system-prompt fill with the arm's own
narrowed roster -- NOT an extra ``{"type": "text", ...}`` user-content part
the way ``Audio2ToolAdapter.assemble_prompt`` folds an ordinary
``SupplyPacket`` in. This module therefore does NOT call
``Audio2ToolAdapter.assemble_prompt`` for S1p/S2/S4 (only for N0r, above):
:func:`assemble_roster_prompt` below reuses ``Audio2ToolAdapter``'s own
frozen ``_INSTRUCTION_TEMPLATE`` (imported directly -- module-private, but
the byte-identical-rest-of-the-instruction requirement means this module
must fill the SAME template string, never a hand-copied duplicate that could
drift) with a NARROWED ``tool_schemas`` fill instead of the full 152-row
one ``data.audio2tool.render_tool_schemas`` produces. A ``SupplyPacket`` is
still constructed per (arm, sample) -- purely as an internal, auditable
dose/token-count record (:func:`roster_supply_packet`) -- even though its
``prompt_block`` lands in the SYSTEM message rather than a user ``text``
content part; ``FrozenCoreClient`` never sees it as "supplied evidence"
(``supplied_evidence``/``evidence_provenance`` stay empty for every arm in
this probe, S1p/S2/S4 included -- exactly as they already do for A0's own
zero-supply request, since the manipulation lives inside
``task_instruction`` text on both sides).

S1' TOOL-SOURCE BINDING (mission brief: "verify the read outputs carry it,
and if not, derive it"): VERIFIED that neither
``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/
headroom.json`` (schema ``saea-a2t-a0-headroom-v1``: only
``attempt_dir``/``count``/``sample_ids``) nor ``verdict.json`` (schema
``saea-a2t-a0-read-v1``: per-tier aggregates, headroom id list, recheck
mismatches) carries a per-sample selected-tool-name field anywhere --
``analysis.a2t_read.build_a2t_report`` computes ``tool_accuracy``/
``exact_match`` per row but never threads the PARSED PREDICTED tool-call
list back out into either artifact. This module therefore DERIVES it
(:func:`derive_a0_selected_tools`) directly from the CONSUMED attempt's own
``outputs.jsonl`` (the path ``headroom.json["attempt_dir"]`` already names),
reusing ``analysis.a2t_read.load_attempt_rows`` (never a second JSONL
parser) and ``reproduction.toolcall_scoring.parse_tool_calls_text`` (the
SAME committed parser ``Audio2ToolAdapter.score`` itself calls) -- never
reading gold, never re-deriving the parse logic. This is a READ of an
already-flown, already-consumed attempt's own recorded output, not a new
model contact.

Zero live model contact, engineering only: every test in this repository's
own suite for this module drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...data.audio2tool import render_registry_row
from ...reproduction.toolcall_scoring import parse_tool_calls_text
from ..adapters.audio2tool import _INSTRUCTION_TEMPLATE, Audio2ToolAdapter, Audio2ToolSample
from ..runner import ZERO_SUPPLY_ARM
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket

_PROBE_ID = "P-A2T"

S1P_ARM = "S1p"
S2_ARM = "S2"
S4_ARM = "S4"
N0R_ARM = "N0r"
A2T_S2_SUPPLY_ARMS: tuple[str, ...] = (S1P_ARM, S2_ARM, S4_ARM)
A2T_S2_ARMS: tuple[str, ...] = (S1P_ARM, S2_ARM, S4_ARM, N0R_ARM)

DEFAULT_SEED = 20260807
HEADROOM_N = 120
S2_TOTAL_ROSTER_SIZE = 9
N0R_TARGET_N = 40

HEADROOM_SCHEMA = "saea-a2t-a0-headroom-v1"


class A2tS2FlightError(RuntimeError):
    """A Stage-2 supply-probe flight input is malformed, a headroom/attempt
    artifact fails its own load-time checks, a seeded arm-construction
    invariant is violated (not enough distractor tools, a derangement with
    fewer than two distinct tool identities), or the flight loop is asked
    to run over a sample set that does not match its own precomputed plan."""


# ---------------------------------------------------------------------------
# Headroom manifest + A0 selected-tool derivation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeadroomManifest:
    """The frozen 120-id Stage-2 headroom list
    (``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/
    headroom.json``) -- owner ruling 2026-08-18: fly ALL 120, no
    subsampling, so a real flight must run over exactly this set."""

    sample_ids: tuple[str, ...]
    attempt_dir: str
    split_identity_hash: str | None


def load_headroom_manifest(path: Path) -> HeadroomManifest:
    import json

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema") != HEADROOM_SCHEMA:
        raise A2tS2FlightError(
            f"{path}: schema must be {HEADROOM_SCHEMA!r}, got {document.get('schema')!r}"
        )
    sample_ids = document.get("sample_ids")
    if not isinstance(sample_ids, list) or not sample_ids:
        raise A2tS2FlightError(f"{path}: sample_ids must be a non-empty list")
    sample_ids = tuple(str(sid) for sid in sample_ids)
    if len(set(sample_ids)) != len(sample_ids):
        raise A2tS2FlightError(f"{path}: duplicate sample_id in sample_ids")
    if len(sample_ids) != HEADROOM_N:
        raise A2tS2FlightError(
            f"{path}: owner ruling is to fly ALL {HEADROOM_N} headroom samples, got "
            f"{len(sample_ids)}"
        )
    attempt_dir = document.get("attempt_dir")
    if not isinstance(attempt_dir, str) or not attempt_dir:
        raise A2tS2FlightError(f"{path}: attempt_dir must be a non-empty string")
    split_identity_hash = document.get("split_identity_hash")
    return HeadroomManifest(
        sample_ids=tuple(sorted(sample_ids)),
        attempt_dir=attempt_dir,
        split_identity_hash=split_identity_hash,
    )


def derive_a0_selected_tools(
    attempt_dir: Path, sample_ids: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """``sample_id -> sorted, deduplicated tool names`` the core ITSELF
    named in its own zero-supply A0 response for that sample -- the S1'
    tool-source binding (module docstring). Reuses
    ``analysis.a2t_read.load_attempt_rows`` for the JSONL read and
    ``reproduction.toolcall_scoring.parse_tool_calls_text`` for the parse,
    never a second implementation of either. Fail-closed: a malformed row,
    a missing sample, a non-zero-supply row, or a headroom sample whose own
    A0 response failed to parse a NON-EMPTY tool-call list (impossible if
    the row genuinely scored ``tool_accuracy == 1.0``, so this is a harness
    inconsistency, not a soft case) all raise :class:`A2tS2FlightError`
    rather than silently proceeding."""

    # Deferred, function-local import: mirrors rails.consumption.classify_outcome's
    # own reuse of analysis.p2_reads._count_subsequence (the SAME cross-module
    # "rails' package top level stays free of analysis/scoring-stack imports for
    # any caller that never actually needs this" discipline), rather than a
    # second, duplicated outputs.jsonl parser in this module.
    from ...analysis.a2t_read import load_attempt_rows

    rows, malformed = load_attempt_rows(Path(attempt_dir))
    if malformed:
        raise A2tS2FlightError(
            f"{attempt_dir}: {len(malformed)} malformed outputs.jsonl row(s), e.g. "
            f"{malformed[0]!r}"
        )
    wanted = set(sample_ids)
    by_id: dict[str, tuple[str, ...]] = {}
    for row in rows:
        if row.sample_id not in wanted:
            continue
        if row.arm != ZERO_SUPPLY_ARM:
            raise A2tS2FlightError(
                f"{attempt_dir}: headroom sample {row.sample_id!r} has an outputs.jsonl row on "
                f"arm {row.arm!r}, expected {ZERO_SUPPLY_ARM!r} (A0 is the only arm this attempt "
                "is meant to carry)"
            )
        if row.sample_id in by_id:
            raise A2tS2FlightError(
                f"{attempt_dir}: duplicate zero-supply row for sample {row.sample_id!r}"
            )
        predicted, parsed = parse_tool_calls_text(row.response_text)
        if not parsed or not predicted:
            raise A2tS2FlightError(
                f"{attempt_dir}: headroom sample {row.sample_id!r} membership requires "
                "tool_accuracy == 1.0, which is impossible for a response that fails to parse a "
                f"non-empty tool-call list (parsed={parsed}, predicted={predicted!r}); refusing "
                "(harness inconsistency between the frozen headroom list and this attempt dir)"
            )
        by_id[row.sample_id] = tuple(sorted({call.name for call in predicted}))
    missing = wanted - set(by_id)
    if missing:
        raise A2tS2FlightError(
            f"{attempt_dir}: {len(missing)} headroom sample id(s) have no zero-supply row: "
            f"{sorted(missing)[:5]}"
        )
    return by_id


# ---------------------------------------------------------------------------
# Arm construction: S1p / S2 / S4 tool-name selection, N0r's seeded draw.
# ---------------------------------------------------------------------------


def s1p_tool_names(selected_tool_names: Sequence[str]) -> tuple[str, ...]:
    """The S1' roster's own tool identities: sorted, deduplicated. Exactly
    1 element for a single-intent-tier sample; the tier3/tier8 multi-intent
    minority may carry more than one DISTINCT tool name here (module
    docstring: honest reflection of "the tool(s) the core itself selected",
    never a silent truncation to one)."""

    return tuple(sorted(set(selected_tool_names)))


def s2_distractor_pool(correct_tool_names: Sequence[str], all_tool_names: Sequence[str]) -> tuple[str, ...]:
    correct = set(correct_tool_names)
    return tuple(name for name in all_tool_names if name not in correct)


def s2_tool_names(
    correct_tool_names: Sequence[str],
    all_tool_names: Sequence[str],
    rng: random.Random,
    *,
    total: int = S2_TOTAL_ROSTER_SIZE,
) -> tuple[str, ...]:
    """S2's diluted roster: the correct tool name(s) plus seeded distractors,
    total roster size fixed at ``total`` (prereg: "K=9" read as a TOTAL dose,
    module docstring) -- for the overwhelming single-intent-tier majority
    this is exactly 1 correct + 8 distractors; the tier3/tier8 multi-intent
    minority (more than one correct tool) draws proportionally fewer
    distractors so the DOSE stays a controlled constant across every one of
    the 120 samples, rather than ballooning with tier. ``rng`` is consumed
    (advances its own state) -- callers wanting full-flight reproducibility
    must drive ONE ``random.Random`` across every sample IN A FIXED, STABLE
    ORDER (:func:`build_flight_plan` iterates sorted ``sample_id``s)."""

    correct = tuple(sorted(set(correct_tool_names)))
    n_distractors = max(0, total - len(correct))
    pool = s2_distractor_pool(correct, all_tool_names)
    if len(pool) < n_distractors:
        raise A2tS2FlightError(
            f"S2 needs {n_distractors} distractor tool(s) beyond the {len(correct)} correct "
            f"one(s), but the registry only offers {len(pool)} outside the correct set"
        )
    distractors = tuple(sorted(rng.sample(list(pool), n_distractors))) if n_distractors else ()
    return tuple(sorted(set(correct) | set(distractors)))


def build_s4_derangement(tool_names: Sequence[str], *, seed: int) -> dict[str, str]:
    """A fixed-point-free seeded mapping ``tool_name -> deranged_tool_name``
    over the DISTINCT tool identities named in ``tool_names`` (Sattolo's
    algorithm: a single, uniformly-random n-cycle, which for n>=2 is
    guaranteed to have NO fixed points -- see e.g. Sattolo 1986).

    Deranging over TOOL IDENTITY (deduplicated) rather than over raw SAMPLE
    indices is deliberate: two different headroom samples can share the
    same correct tool (the same tool gets selected for more than one
    sample), and a plain index-based permutation over the 120 samples could
    then coincidentally map sample A's own tool to sample B's IDENTICAL
    tool name even though A != B as indices -- silently handing S4 a "wrong"
    row that is not actually wrong. Deriving the derangement over the
    distinct tool set instead makes every sample sharing one correct tool
    receive the SAME (guaranteed-different) deranged tool, and the
    guarantee is checked at the TOOL level, not merely the sample-index
    level."""

    distinct = sorted(set(tool_names))
    n = len(distinct)
    if n < 2:
        raise A2tS2FlightError(
            f"S4 derangement requires at least 2 distinct tool identities among the headroom "
            f"selections, got {n}"
        )
    rng = random.Random(seed)
    order = list(range(n))
    # Sattolo's algorithm: unlike Fisher-Yates (randrange(i + 1), which can
    # leave order[i] == i), j is drawn from randrange(i) -- strictly less
    # than i, so index i is NEVER swapped with itself; the result is
    # guaranteed to be a single n-cycle, hence fixed-point-free for n >= 2.
    for i in range(n - 1, 0, -1):
        j = rng.randrange(i)
        order[i], order[j] = order[j], order[i]
    mapping = {distinct[i]: distinct[order[i]] for i in range(n)}
    fixed_points = [tool for tool, deranged in mapping.items() if tool == deranged]
    if fixed_points:  # pragma: no cover -- Sattolo's algorithm precludes this; defense in depth
        raise A2tS2FlightError(f"S4 derangement produced fixed point(s): {fixed_points}")
    return mapping


def _s4_wrong_tool_for_sample(
    canonical: str, own_tools: Sequence[str], derangement: Mapping[str, str]
) -> str:
    """The tool actually supplied to S4 for one sample: ``derangement[canonical]``,
    UNLESS that coincidentally lands on one of the sample's OWN other
    correctly-selected tools (possible only for the tier3/tier8 multi-intent
    minority, where ``own_tools`` has more than one member) -- in which case
    the Sattolo cycle (module docstring: :func:`build_s4_derangement`
    produces a single n-cycle) is chased one step further until a tool
    outside ``own_tools`` is found. A single n-cycle visits every distinct
    tool identity exactly once before returning to ``canonical``, so this
    always terminates; it fails closed only if ``own_tools`` were to cover
    the ENTIRE distinct-tool universe (practically impossible)."""

    own = set(own_tools)
    current = canonical
    seen: set[str] = set()
    while True:
        current = derangement[current]
        if current == canonical or current in seen:
            raise A2tS2FlightError(
                f"S4 could not find a wrong tool for canonical {canonical!r} outside its own "
                f"selected set {sorted(own)} -- the derangement cycle exhausted every other "
                "distinct tool identity without finding one"
            )
        seen.add(current)
        if current not in own:
            return current


def _tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def n0r_seeded_draw(
    headroom_ids: Sequence[str], *, seed: int = DEFAULT_SEED, target_n: int = N0R_TARGET_N
) -> tuple[str, ...]:
    """The N0r noise-floor arm's 40-sample, tier-proportional seeded draw
    (prereg: "40 seeded samples of the 120 ... tier-proportional"; the exact
    per-tier count is an engineering interpretation, documented here rather
    than left implicit): largest-remainder (Hare quota) apportionment of
    ``target_n`` across tiers by each tier's own share of ``headroom_ids``,
    ties among equal remainders broken by a seeded shuffle (never an
    arbitrary tier-name ordering), then a seeded, per-tier draw without
    replacement. Fully deterministic given ``(headroom_ids, seed,
    target_n)`` -- calling this twice with the same inputs returns the same
    tuple."""

    if not headroom_ids:
        raise A2tS2FlightError("n0r_seeded_draw requires at least one headroom id")
    by_tier: dict[str, list[str]] = {}
    for sample_id in sorted(headroom_ids):
        by_tier.setdefault(_tier_of(sample_id), []).append(sample_id)
    total = len(headroom_ids)
    tiers = sorted(by_tier)

    quotas = {tier: len(by_tier[tier]) * target_n / total for tier in tiers}
    floors = {tier: int(quotas[tier]) for tier in tiers}
    remainders = {tier: quotas[tier] - floors[tier] for tier in tiers}
    deficit = target_n - sum(floors.values())
    if not (0 <= deficit <= len(tiers)):
        raise A2tS2FlightError(
            f"n0r tier-proportional quota computation is inconsistent (deficit={deficit} for "
            f"{len(tiers)} tiers)"
        )

    rng = random.Random(seed)
    tie_order = tiers[:]
    rng.shuffle(tie_order)
    tie_rank = {tier: index for index, tier in enumerate(tie_order)}
    ranked = sorted(tiers, key=lambda tier: (-remainders[tier], tie_rank[tier]))
    counts = dict(floors)
    for tier in ranked[:deficit]:
        counts[tier] += 1

    draw: list[str] = []
    for tier in tiers:
        pool = by_tier[tier]
        count = counts[tier]
        if count > len(pool):
            raise A2tS2FlightError(
                f"n0r tier {tier!r} quota {count} exceeds its own headroom pool {len(pool)}"
            )
        draw.extend(rng.sample(pool, count))
    if len(draw) != target_n:
        raise A2tS2FlightError(
            f"n0r draw produced {len(draw)} id(s), expected {target_n}"
        )
    return tuple(sorted(draw))


# ---------------------------------------------------------------------------
# Roster rendering + supply-packet bookkeeping + prompt assembly.
# ---------------------------------------------------------------------------


def render_roster_prompt_block(rows: Sequence[Mapping[str, str]]) -> str:
    """The narrowed ``{tool_schemas}`` fill for S1p/S2/S4: the SAME per-row
    JSON rendering ``data.audio2tool.render_tool_schemas`` uses for all 152
    rows (:func:`~data.audio2tool.render_registry_row`, reused directly),
    newline-joined over only ``rows`` -- so a supply arm's rendered prompt
    is byte-comparable to A0's own full-registry rendering, differing only
    in which rows are present."""

    return "\n".join(render_registry_row(row) for row in rows)


def roster_supply_packet(arm: str, sample_id: str, rows: Sequence[Mapping[str, str]]) -> SupplyPacket:
    """The internal, auditable ``SupplyPacket`` for one (arm, sample)'s
    roster -- dose/token-count bookkeeping only (module docstring: this
    packet's ``prompt_block`` lands in the SYSTEM message, never a user
    ``text`` content part, so ``FrozenCoreClient`` never sees it as
    "supplied evidence"). Mirrors ``rails.probes.pslu_flight._roster_packet``'s
    own shape."""

    if not rows:
        raise A2tS2FlightError(f"{arm}/{sample_id}: roster_supply_packet requires at least one row")
    prompt_block = render_roster_prompt_block(rows)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{sample_id}-{index:03d}-{row['tool_name']}", text=render_registry_row(row))
        for index, row in enumerate(rows)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(rows), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"a2t-s2-{arm}-roster-v1",
        items=items,
    ).validate()


def assemble_roster_prompt(
    sample: Audio2ToolSample, tool_schemas_text: str
) -> tuple[Mapping[str, object], ...]:
    """S1p/S2/S4's own prompt assembly: the SAME frozen instruction template
    ``rails.adapters.audio2tool`` uses for A0 (imported directly, module
    docstring: "byte-identical rest of the instruction"), with
    ``tool_schemas_text`` filling ``{tool_schemas}`` instead of the full
    152-row registry. The user message carries ONLY the audio part -- no
    extra ``text`` content part (the supply manipulation already lives in
    the system message; module docstring)."""

    instruction = _INSTRUCTION_TEMPLATE.format(tool_schemas=tool_schemas_text)
    return (
        {"role": "system", "content": instruction},
        {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
    )


def _supplied_tool_label(tool_names: Sequence[str]) -> str:
    """The single ``supplied_tool`` label an outputs.jsonl row carries for
    S1p/S2 (module docstring: "the correct/target tool identity", never the
    full roster -- the full roster is fully reconstructible later from
    ``(headroom, seed, registry)`` since every arm's construction is
    deterministic, so nothing is lost by not repeating it per row): sorted,
    comma-joined tool names."""

    return ",".join(sorted(set(tool_names)))


# ---------------------------------------------------------------------------
# The flight plan: every arm's per-sample roster, precomputed once and
# independently auditable/testable before any request is ever issued.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2FlightPlan:
    """Every arm's fully-resolved, precomputed per-sample roster -- built
    ONCE from ``(headroom, selected_tools, registry_rows, seed)``, entirely
    deterministic and model-free. ``run_a2t_s2_flight`` below is a thin
    consumer of this plan; every field here is independently testable
    without a ``core_client`` at all."""

    headroom_ids: tuple[str, ...]
    selected_tools: Mapping[str, tuple[str, ...]]
    s1p_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    s2_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    s4_derangement: Mapping[str, str]
    s4_tool_name_by_sample: Mapping[str, str]
    n0r_sample_ids: tuple[str, ...]
    registry_index: Mapping[str, Mapping[str, str]]


def build_flight_plan(
    headroom: HeadroomManifest,
    selected_tools: Mapping[str, tuple[str, ...]],
    registry_rows: Sequence[Mapping[str, str]],
    *,
    seed: int = DEFAULT_SEED,
    n0r_target_n: int = N0R_TARGET_N,
) -> A2tS2FlightPlan:
    """Resolve every arm's per-sample roster deterministically. Fail-closed
    if ``selected_tools`` does not carry EXACTLY ``headroom.sample_ids``, if
    the registry has a duplicate/missing ``tool_name``, or if any selected
    or deranged tool name is absent from the registry. ``n0r_target_n``
    defaults to the REGISTERED 40 (:data:`N0R_TARGET_N`); overridable only
    so a test can exercise this function's full pipeline over a headroom
    set smaller than 120 without ``n0r_seeded_draw`` running out of
    per-tier pool -- a real flight must never override it."""

    registry_index: dict[str, Mapping[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not name:
            raise A2tS2FlightError("registry row is missing tool_name")
        if name in registry_index:
            raise A2tS2FlightError(f"registry has a duplicate tool_name {name!r}")
        registry_index[name] = row
    all_tool_names = tuple(sorted(registry_index))

    headroom_ids = tuple(sorted(headroom.sample_ids))
    have = set(selected_tools)
    want = set(headroom_ids)
    if have != want:
        missing = want - have
        extra = have - want
        raise A2tS2FlightError(
            f"selected_tools does not match headroom.sample_ids exactly "
            f"(missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )
    for sample_id, tool_names in selected_tools.items():
        if not tool_names:
            raise A2tS2FlightError(f"sample {sample_id!r} carries no selected tool name(s)")
        unknown = set(tool_names) - registry_index.keys()
        if unknown:
            raise A2tS2FlightError(
                f"sample {sample_id!r} selects tool(s) {sorted(unknown)} not present in the "
                "registry"
            )

    s1p_by_sample = {
        sample_id: s1p_tool_names(selected_tools[sample_id]) for sample_id in headroom_ids
    }

    s2_rng = random.Random(seed)
    s2_by_sample: dict[str, tuple[str, ...]] = {}
    for sample_id in headroom_ids:  # fixed, sorted order -- reproducibility contract
        s2_by_sample[sample_id] = s2_tool_names(
            selected_tools[sample_id], all_tool_names, s2_rng
        )

    canonical_by_sample = {
        sample_id: s1p_by_sample[sample_id][0] for sample_id in headroom_ids
    }
    derangement = build_s4_derangement(canonical_by_sample.values(), seed=seed)
    s4_by_sample = {
        sample_id: _s4_wrong_tool_for_sample(
            canonical_by_sample[sample_id], s1p_by_sample[sample_id], derangement
        )
        for sample_id in headroom_ids
    }

    n0r_ids = n0r_seeded_draw(headroom_ids, seed=seed, target_n=n0r_target_n)

    return A2tS2FlightPlan(
        headroom_ids=headroom_ids,
        selected_tools=dict(selected_tools),
        s1p_tool_names_by_sample=s1p_by_sample,
        s2_tool_names_by_sample=s2_by_sample,
        s4_derangement=derangement,
        s4_tool_name_by_sample=s4_by_sample,
        n0r_sample_ids=n0r_ids,
        registry_index=registry_index,
    )


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2ArmResult:
    """One flight request's own outputs.jsonl row content (mission brief:
    "carrying {arm, sample_id, supplied_tool, response, timing} + predicted
    nothing else" -- deliberately narrower than
    ``rails.probes.pslu_flight.PsluArmResult``: no ``messages``/``metrics``/
    ``consumption`` field, since scoring is a SEPARATELY-registered later
    read mission's job, mirroring ``analysis.a2t_read``'s own "scores an
    already-written attempt" discipline rather than scoring inline here)."""

    arm: str
    sample_id: str
    supplied_tool: str | None
    response: str
    timing: Mapping[str, object]


@dataclass(frozen=True)
class A2tS2FlightSummary:
    results: tuple[A2tS2ArmResult, ...]


def _iso(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _complete_and_record(
    core_client,
    *,
    arm: str,
    sample_id: str,
    supplied_tool: str | None,
    messages: Sequence[Mapping[str, object]],
    decoding_params: Mapping[str, object] | None,
    now: Callable[[], float],
) -> A2tS2ArmResult:
    started_at = _iso(now())
    t0 = now()
    response = core_client.complete(messages, decoding_params=decoding_params)
    latency_seconds = now() - t0
    return A2tS2ArmResult(
        arm=arm,
        sample_id=sample_id,
        supplied_tool=supplied_tool,
        response=response,
        timing={"started_at": started_at, "latency_seconds": latency_seconds},
    )


def run_a2t_s2_flight(
    *,
    adapter: Audio2ToolAdapter,
    core_client,
    samples: Sequence[Audio2ToolSample],
    plan: A2tS2FlightPlan,
    decoding_params: Mapping[str, object] | None = None,
    now: Callable[[], float] = time.time,
) -> A2tS2FlightSummary:
    """Execute the full four-arm P-A2T Stage-2 flight: S1p/S2/S4 (one
    request per sample per arm, in that order, over ``plan.headroom_ids``
    sorted) then N0r (one zero-supply request per ``plan.n0r_sample_ids``,
    reusing ``Audio2ToolAdapter.assemble_prompt(sample, None)`` unchanged --
    module docstring). ``core_client`` is duck-typed against
    ``rails.core_client.CoreClient`` (never imported/annotated directly --
    the same "no forced import" discipline ``rails.probes.pslu_flight``
    itself already uses)."""

    if not samples:
        raise A2tS2FlightError("run_a2t_s2_flight requires at least one sample")
    by_id = {sample.sample_id: sample for sample in samples}
    missing = set(plan.headroom_ids) - set(by_id)
    if missing:
        raise A2tS2FlightError(
            f"plan names {len(missing)} headroom sample id(s) not present in samples: "
            f"{sorted(missing)[:5]}"
        )
    missing_n0r = set(plan.n0r_sample_ids) - set(by_id)
    if missing_n0r:
        raise A2tS2FlightError(
            f"plan names {len(missing_n0r)} N0r sample id(s) not present in samples: "
            f"{sorted(missing_n0r)[:5]}"
        )

    results: list[A2tS2ArmResult] = []

    for sample_id in plan.headroom_ids:
        sample = by_id[sample_id]

        s1p_names = plan.s1p_tool_names_by_sample[sample_id]
        s1p_rows = [plan.registry_index[name] for name in s1p_names]
        s1p_block = render_roster_prompt_block(s1p_rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=S1P_ARM,
                sample_id=sample_id,
                supplied_tool=_supplied_tool_label(s1p_names),
                messages=assemble_roster_prompt(sample, s1p_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

        s2_names = plan.s2_tool_names_by_sample[sample_id]
        s2_rows = [plan.registry_index[name] for name in s2_names]
        s2_block = render_roster_prompt_block(s2_rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=S2_ARM,
                sample_id=sample_id,
                supplied_tool=_supplied_tool_label(s1p_names),
                messages=assemble_roster_prompt(sample, s2_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

        s4_name = plan.s4_tool_name_by_sample[sample_id]
        s4_block = render_roster_prompt_block([plan.registry_index[s4_name]])
        results.append(
            _complete_and_record(
                core_client,
                arm=S4_ARM,
                sample_id=sample_id,
                supplied_tool=s4_name,
                messages=assemble_roster_prompt(sample, s4_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

    for sample_id in plan.n0r_sample_ids:
        sample = by_id[sample_id]
        results.append(
            _complete_and_record(
                core_client,
                arm=N0R_ARM,
                sample_id=sample_id,
                supplied_tool=None,
                messages=adapter.assemble_prompt(sample, None),
                decoding_params=decoding_params,
                now=now,
            )
        )

    return A2tS2FlightSummary(results=tuple(results))


# ---------------------------------------------------------------------------
# outputs.jsonl serialization.
# ---------------------------------------------------------------------------


def result_to_json(result: A2tS2ArmResult) -> dict[str, object]:
    return {
        "arm": result.arm,
        "sample_id": result.sample_id,
        "supplied_tool": result.supplied_tool,
        "response": result.response,
        "timing": dict(result.timing),
    }


def write_outputs_jsonl(path: Path, results: Sequence[A2tS2ArmResult]) -> None:
    import json

    with Path(path).open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result_to_json(result), ensure_ascii=False) + "\n")


__all__ = [
    "A2T_S2_ARMS",
    "A2T_S2_SUPPLY_ARMS",
    "DEFAULT_SEED",
    "HEADROOM_N",
    "HEADROOM_SCHEMA",
    "N0R_TARGET_N",
    "N0R_ARM",
    "S1P_ARM",
    "S2_ARM",
    "S2_TOTAL_ROSTER_SIZE",
    "S4_ARM",
    "A2tS2ArmResult",
    "A2tS2FlightError",
    "A2tS2FlightPlan",
    "A2tS2FlightSummary",
    "HeadroomManifest",
    "assemble_roster_prompt",
    "build_flight_plan",
    "build_s4_derangement",
    "derive_a0_selected_tools",
    "load_headroom_manifest",
    "n0r_seeded_draw",
    "render_roster_prompt_block",
    "result_to_json",
    "roster_supply_packet",
    "run_a2t_s2_flight",
    "s1p_tool_names",
    "s2_distractor_pool",
    "s2_tool_names",
    "write_outputs_jsonl",
]
