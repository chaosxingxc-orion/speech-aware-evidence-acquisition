"""Audio2Tool carrier loading (P1 scaffold): frozen-receipt-scoped, fail-closed.

Layout facts (verified against the materialized asset, 2026-08-08):
``<asset root>/tools_registry.csv`` plus ``<asset root>/public/`` holding one
``tier{N}_{name}_data/tier{N}_{name}.json`` manifest (a JSON list of items)
and one ``tier{N}_{name}_audios/query_{id:05d}/*.wav`` directory tree per
tier. Manifest items carry identity (``tier``/``id``/``query_idx``), media
facts (``path``/``duration`` — except tier7_multiturn, where audio lives per
turn inside ``chat_history`` and those top-level keys are absent), the
ground-truth fields (``tool_name``/``expected_tool_call``/
``extracted_params``/``additional_tool_calls``) and the spoken ``query``
text, all in ONE file. That single-manifest shape forces this module to
parse a file that also contains annotations; the RUNTIME surface
(:func:`load_audio2tool`) exposes only the standard five ``SampleRef``
identity/media fields (boundary-checked by ``SampleRef.runtime_view``), and
gold leaves this module only through the scorer-side
:func:`load_expected_calls`.

The loader's sample universe IS the frozen probe receipt
(``docs/receipts/probe-samples/``, P0.D): pre-registration means no run may
ever resolve Audio2Tool items outside it, so ``load_audio2tool`` hydrates
exactly the receipt's items — the receipt's ``split_identity_hash`` is
recomputed fail-closed (``reproduction.sampling.split_identity_hash``)
before any manifest is read, every receipt item must exist in its tier
manifest with a matching ``query_idx``, and every referenced wav must exist
(its header supplies ``sample_rate_hz``, the one media fact the manifests do
not carry; ``duration`` supplies ``audio_seconds``).

Lock binding mirrors the earnings pattern: identity resolves through the
umbrella lock entry named ``audio2tool`` (``lock_entry``/``asset_dir``).
That entry now exists (``docs/datasets.lock.json``'s ``asset_catalog``,
``local_subdir: "datasets/audio2tool"``, ``status: "COMPLETE"``) — the
owner lock amendment referenced below has landed, and the bounded
discovery probe it gates is admitted by the 2026-08-15 owner amendment
(umbrella ``wiki/experiments/speech-aware-evidence-acquisition/
2026-08-15-owner-go-dual-track-agentic.md``, Amendment 1). The loader
resolves against the real umbrella lock directly; a lock lacking the entry
(e.g. a synthetic test lock) still fails closed with
``AssetResolutionError('audio2tool' ...)`` — see
``docs/readiness/2026-08-08-p1-engineering-notes.md`` for the original
engineering notes this scaffold was built from.

Tier7 protocol note: the P1 scaffold sends the FINAL user turn's wav only
(``chat_history[-1]``, whose role must be ``user`` — fail-closed otherwise).
Prior turns (user and agent audio) are not yet representable in the
D2-frozen bare-core payload beyond its empty ``history`` field; the
engineering notes record this protocol-fidelity gap and the options.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.sampling import split_identity_hash
from ..reproduction.toolcall_gold import GoldParseError, expected_tool_calls_for_entry
from ..reproduction.toolcall_scoring import ToolCall
from .loader import LoaderError, SampleRef
from .lock import REPO_ROOT, asset_dir, lock_entry

AUDIO2TOOL_LOCK_KEY = "audio2tool"

_STAGE2_SPLIT_ROLES = frozenset({"discovery", "dev"})
_TIER_PATTERN = re.compile(r"tier[0-9]+_[a-z0-9_]+")


@dataclass(frozen=True)
class _ResolvedItem:
    """One receipt item hydrated from its tier manifest (internal only)."""

    sample_id: str
    tier: str
    audio_relpath_in_public: str
    audio_seconds: float
    entry: Mapping[str, object]


def _probe_samples_dir(repo_root: Path) -> Path:
    return Path(repo_root) / "docs" / "receipts" / "probe-samples"


def audio2tool_receipts(repo_root: Path) -> dict[str, Mapping[str, object]]:
    """Every committed probe-sample receipt whose ``carrier`` is
    ``audio2tool``, keyed by receipt name (filename stem), each strictly
    verified via :func:`load_receipt`. The union of their items IS this
    carrier's loadable universe (sample-once policy,
    ``configs/probes/manifest.json``): pre-registration means no run may ever
    resolve Audio2Tool items outside a frozen receipt. Receipts naming OTHER
    carriers (r2-bba, r5-vab) are skipped by their ``carrier`` field; an
    unreadable receipt file fails closed regardless of carrier."""

    directory = _probe_samples_dir(repo_root)
    if not directory.is_dir():
        raise LoaderError(f"probe sample receipt directory missing: {directory}")
    receipts: dict[str, Mapping[str, object]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise LoaderError(f"cannot read probe sample receipt {path}: {error}") from error
        if not isinstance(payload, Mapping):
            raise LoaderError(f"probe sample receipt {path} must be a JSON object")
        if payload.get("carrier") != AUDIO2TOOL_LOCK_KEY:
            continue
        receipts[path.stem] = _verify_receipt(path, payload)
    if not receipts:
        raise LoaderError(
            f"no {AUDIO2TOOL_LOCK_KEY!r} probe sample receipt found under {directory}"
        )
    return receipts


def _verify_receipt(path: Path, payload: Mapping[str, object]) -> Mapping[str, object]:
    """Strictly verify one frozen probe-sample receipt, re-verifying its
    ``split_identity_hash`` (fail-closed) before anything trusts its items."""
    split_role = payload.get("split_role")
    if split_role not in _STAGE2_SPLIT_ROLES:
        raise LoaderError(
            f"probe sample receipt {path} split_role {split_role!r} is not a Stage-2 "
            f"role {sorted(_STAGE2_SPLIT_ROLES)} (fail-closed)"
        )
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise LoaderError(f"probe sample receipt {path} has no items")
    keys: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise LoaderError(f"probe sample receipt {path} item is not an object")
        key = item.get("key")
        tier = item.get("tier")
        item_id = item.get("id")
        if (
            not isinstance(key, str)
            or not isinstance(tier, str)
            or not _TIER_PATTERN.fullmatch(tier)
            or isinstance(item_id, bool)
            or not isinstance(item_id, int)
            or item_id < 0
        ):
            raise LoaderError(f"probe sample receipt {path} item is malformed: {item!r}")
        if key != f"{AUDIO2TOOL_LOCK_KEY}:{tier}:{item_id:06d}":
            raise LoaderError(
                f"probe sample receipt {path} item key {key!r} does not match its own "
                f"tier/id fields (expected '{AUDIO2TOOL_LOCK_KEY}:{tier}:{item_id:06d}')"
            )
        keys.append(key)
    try:
        recomputed = split_identity_hash(keys)
    except ValueError as error:
        raise LoaderError(f"probe sample receipt {path}: {error}") from error
    if recomputed != payload.get("split_identity_hash"):
        raise LoaderError(
            f"probe sample receipt {path} split_identity_hash "
            f"{payload.get('split_identity_hash')!r} does not match the hash recomputed "
            f"from its own item keys ({recomputed!r}); refusing a tampered receipt"
        )
    return payload


def _validate_audio_relpath(relpath: object, context: str) -> str:
    """A manifest audio path must be a plain, confined, relative wav path —
    same character discipline the transport's media confinement enforces."""

    if not isinstance(relpath, str) or not relpath:
        raise LoaderError(f"{context}: manifest audio path must be a non-empty string")
    if "\\" in relpath or ":" in relpath or relpath.startswith("/"):
        raise LoaderError(f"{context}: manifest audio path {relpath!r} is not a plain relative path")
    segments = relpath.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise LoaderError(f"{context}: manifest audio path {relpath!r} escapes its tier directory")
    if not relpath.endswith(".wav"):
        raise LoaderError(f"{context}: manifest audio path {relpath!r} is not a .wav file")
    return relpath


def _audio_seconds(value: object, context: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise LoaderError(f"{context}: duration must be a finite positive number, got {value!r}")
    return float(value)


def _entry_media(entry: Mapping[str, object], context: str) -> tuple[str, float]:
    """(audio relpath under public/, audio_seconds) for one manifest entry.

    tier7_multiturn rows carry no top-level ``path``/``duration``; the P1
    scaffold sends the FINAL user turn's wav (module docstring records the
    protocol-fidelity gap this leaves).
    """

    path = entry.get("path")
    if isinstance(path, str) and path:
        return (
            _validate_audio_relpath(path, context),
            _audio_seconds(entry.get("duration"), context),
        )
    history = entry.get("chat_history")
    if not isinstance(history, list) or not history:
        raise LoaderError(
            f"{context}: manifest entry has neither a top-level audio path nor a chat_history"
        )
    final_turn = history[-1]
    if not isinstance(final_turn, Mapping) or final_turn.get("role") != "user":
        raise LoaderError(
            f"{context}: the final chat_history turn must be a user turn carrying the "
            "request audio (fail-closed)"
        )
    return (
        _validate_audio_relpath(final_turn.get("path"), context),
        _audio_seconds(final_turn.get("duration"), context),
    )


def _tier_manifest(public_dir: Path, tier: str) -> dict[int, Mapping[str, object]]:
    path = public_dir / f"{tier}_data" / f"{tier}.json"
    if not path.is_file():
        raise LoaderError(f"audio2tool tier manifest missing: {path}")
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LoaderError(f"cannot read audio2tool tier manifest {path}: {error}") from error
    if not isinstance(entries, list):
        raise LoaderError(f"audio2tool tier manifest {path} must be a JSON list")
    by_id: dict[int, Mapping[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or isinstance(entry.get("id"), bool):
            raise LoaderError(f"audio2tool tier manifest {path} has a malformed item")
        entry_id = entry.get("id")
        if not isinstance(entry_id, int) or entry_id in by_id:
            raise LoaderError(
                f"audio2tool tier manifest {path} has a missing or duplicate id: {entry_id!r}"
            )
        by_id[entry_id] = entry
    return by_id


def _resolve_items(lock: Mapping[str, object], root: Path, repo_root: Path) -> tuple[str, list[_ResolvedItem]]:
    """(carrier local_subdir, receipt-scoped resolved items sorted by sample_id)."""

    entry = lock_entry(lock, AUDIO2TOOL_LOCK_KEY)
    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    subdir = str(entry["local_subdir"]).rstrip("/")
    public_dir = carrier_dir / "public"
    if not public_dir.is_dir():
        raise LoaderError(f"audio2tool public directory missing: {public_dir}")

    wanted_by_tier: dict[str, list[Mapping[str, object]]] = {}
    for payload in audio2tool_receipts(repo_root).values():
        for item in payload["items"]:
            wanted_by_tier.setdefault(str(item["tier"]), []).append(item)

    resolved: list[_ResolvedItem] = []
    seen: set[str] = set()
    for tier in sorted(wanted_by_tier):
        manifest = _tier_manifest(public_dir, tier)
        for item in wanted_by_tier[tier]:
            item_id = int(item["id"])
            sample_id = f"{tier}:{item_id:06d}"
            if sample_id in seen:
                raise LoaderError(f"duplicate audio2tool receipt item {sample_id!r}")
            seen.add(sample_id)
            entry_doc = manifest.get(item_id)
            if entry_doc is None:
                raise LoaderError(
                    f"receipt item {sample_id!r} has no row in the {tier} manifest; "
                    "the frozen receipt and the on-disk carrier disagree"
                )
            receipt_query_idx = item.get("query_idx")
            if receipt_query_idx is not None and entry_doc.get("query_idx") != receipt_query_idx:
                raise LoaderError(
                    f"receipt item {sample_id!r} query_idx {receipt_query_idx!r} does not "
                    f"match the manifest row's query_idx {entry_doc.get('query_idx')!r}"
                )
            audio_relpath, audio_seconds = _entry_media(entry_doc, sample_id)
            resolved.append(
                _ResolvedItem(
                    sample_id=sample_id,
                    tier=tier,
                    audio_relpath_in_public=audio_relpath,
                    audio_seconds=audio_seconds,
                    entry=entry_doc,
                )
            )
    resolved.sort(key=lambda item: item.sample_id)
    return subdir, resolved


def _wav_sample_rate(path: Path, context: str) -> int:
    if not path.is_file():
        raise LoaderError(f"{context}: media missing: {path}")
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        raise LoaderError(f"{context}: cannot read wav header of {path}: {error}") from error
    if not isinstance(rate, int) or rate <= 0:
        raise LoaderError(f"{context}: wav header of {path} reports sample rate {rate!r}")
    return rate


def load_audio2tool(
    lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
) -> list[SampleRef]:
    """Every frozen-receipt Audio2Tool sample, sorted by sample id, with media
    facts re-verified against the on-disk manifests and wav headers. Runtime
    surface only — no ground-truth field leaves this function.

    ``repo_root`` (where the committed probe receipt lives) resolves at CALL
    time to this study checkout when not supplied — the ``core.base.CARRIERS``
    seam calls every loader as ``loader(lock, root)``, and only tests bind a
    synthetic repo."""

    subdir, resolved = _resolve_items(
        lock, root, Path(REPO_ROOT if repo_root is None else repo_root)
    )
    samples: list[SampleRef] = []
    for item in resolved:
        media_relpath = f"{subdir}/public/{item.audio_relpath_in_public}"
        samples.append(
            SampleRef(
                carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
                sample_id=item.sample_id,
                media_relpath=media_relpath,
                audio_seconds=item.audio_seconds,
                sample_rate_hz=_wav_sample_rate(Path(root) / media_relpath, item.sample_id),
            )
        )
    return samples


def load_expected_calls(
    lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
) -> dict[str, tuple[ToolCall, ...]]:
    """Scorer-side ONLY: each receipt sample's expected ``ToolCall`` tuple,
    parsed under ``reproduction.toolcall_gold`` (a2t-gold-v1). Never callable
    from the runtime request path — gold must not enter runtime (D2)."""

    _, resolved = _resolve_items(
        lock, root, Path(REPO_ROOT if repo_root is None else repo_root)
    )
    expected: dict[str, tuple[ToolCall, ...]] = {}
    for item in resolved:
        try:
            expected[item.sample_id] = expected_tool_calls_for_entry(item.entry)
        except GoldParseError as error:
            raise LoaderError(
                f"cannot parse expected tool calls for {item.sample_id!r}: {error}"
            ) from error
    return expected


@dataclass(frozen=True)
class OfficialGold:
    """One sample's ground truth in exactly the shape the pinned Audio2Tool
    release hands its own evaluator (``audio_benchmark/datasets/
    release_dataset.py`` -> ``QuerySample``, commit ``b9d5383c``).

    Distinct from :func:`load_expected_calls` on purpose. That function
    returns ``a2t-gold-v1`` ``ToolCall`` tuples, whose primary arguments may
    come from the ``expected_tool_call`` CALL STRING and whose values are
    JSON-coerced; the official evaluator never looks at the call string and
    never coerces, it passes ``extracted_params`` straight into
    ``normalize_parameters``. Scoring the official metric against
    ``a2t-gold-v1`` arguments would be scoring a different gold, so the
    official scorer reads this instead. Both are scorer-side only.
    """

    tool_name: str
    extracted_params: Mapping[str, object]
    additional_tool_calls: tuple[str, ...]


def load_official_gold(
    lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
) -> dict[str, OfficialGold]:
    """Scorer-side ONLY: each receipt sample's ground truth as the pinned
    Audio2Tool release's own dataset loader would build it. Never callable
    from the runtime request path -- gold must not enter runtime (D2).

    Coercion mirrors ``ReleaseDataset._build_sample`` line for line: a
    ``extracted_params``/``additional_tool_calls`` value that arrives as a
    STRING is put through ``ast.literal_eval`` and degrades to ``{}``/``[]``
    on a parse failure, exactly as upstream does. Everything else is passed
    through untouched -- no JSON coercion of values, no call-string parsing.
    On the pinned carrier every row already carries a mapping and a
    list-or-null (surveyed 2026-09-04 over all 608 receipt-scoped rows:
    456 ``(dict, None)`` and 152 ``(dict, list)``), so the string branches
    are upstream fidelity rather than live behaviour; a value that survives
    coercion with the wrong type fails closed here rather than silently
    scoring as an empty expectation.
    """

    import ast

    _, resolved = _resolve_items(
        lock, root, Path(REPO_ROOT if repo_root is None else repo_root)
    )
    gold: dict[str, OfficialGold] = {}
    for item in resolved:
        entry = item.entry
        tool_name = entry.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise LoaderError(
                f"manifest entry for {item.sample_id!r} lacks a non-empty tool_name"
            )
        params: object = entry.get("extracted_params") or {}
        if isinstance(params, str):
            try:
                params = ast.literal_eval(params)
            except (ValueError, SyntaxError):
                params = {}
        if not isinstance(params, Mapping):
            raise LoaderError(
                f"manifest entry for {item.sample_id!r} has a non-mapping "
                f"extracted_params of type {type(params).__name__}"
            )
        additional: object = entry.get("additional_tool_calls") or []
        if isinstance(additional, str):
            try:
                additional = ast.literal_eval(additional)
            except (ValueError, SyntaxError):
                additional = []
        if not isinstance(additional, list) or not all(
            isinstance(name, str) for name in additional
        ):
            raise LoaderError(
                f"manifest entry for {item.sample_id!r} has a malformed "
                "additional_tool_calls (expected a list of strings)"
            )
        gold[item.sample_id] = OfficialGold(
            tool_name=tool_name,
            extracted_params=dict(params),
            additional_tool_calls=tuple(additional),
        )
    return gold


#: The audio2tool sample-id shape, ``"<tier>:<six digits>"`` -- the same
#: identity :func:`_resolve_items` builds and every receipt records, spelled
#: from :data:`_TIER_PATTERN` so there is one tier convention in this module.
_SAMPLE_ID_RE = re.compile(rf"(?P<tier>{_TIER_PATTERN.pattern}):(?P<id>\d{{6}})")

#: The three fields :func:`load_query_rows` returns per sample.
QUERY_ROW_FIELDS = ("query", "gold_call", "tool_name")


def load_query_rows(
    lock: Mapping[str, object],
    root: Path,
    sample_ids: Sequence[str],
) -> dict[str, dict[str, str]]:
    """The spoken ``query`` text, the ``expected_tool_call`` string and the
    primary ``tool_name`` of EXACTLY the named samples, straight from the
    tier manifests.

    IDENTITY-SCOPED, and deliberately not receipt-scoped: unlike
    :func:`load_audio2tool` (whose universe is the frozen probe receipt) this
    reader resolves whatever ids the caller names, because the two callers
    that need it are both outside the probe-receipt universe and both carry
    their own legality argument:

    * ``rails.evolution.build_proposer_material`` -- construction rows of a
      committed ``roster_role == "construction"`` roster, whose gold the
      ``construction-proposer-text`` arm may see (owner decision
      2026-09-05, ``contracts.CONSTRUCTION_VISIBLE_ARMS``);
    * the EVO-A1 decontamination gate (preregistration section 8), which
      opens evaluation query text INSIDE
      ``rails.proposer.validate_candidate_artifact`` alone and never renders,
      logs or echoes it.

    This is therefore a SCORER-SIDE / GATE-SIDE reader in the same class as
    :func:`load_expected_calls` and :func:`load_official_gold`: it is never
    called from a scored row's request path, and the one arm that does put
    its output on the wire is the text-only proposer arm, whose payload
    records every id it saw in the audited ``construction_targets`` field.

    Fail-closed on a malformed id, an id absent from its tier manifest, a
    duplicate, a row with no non-empty ``query``/``tool_name``, and a row
    whose ``expected_tool_call`` is not a non-empty string (a construction
    exemplar with no call string has no gold to show).
    """

    if isinstance(sample_ids, (str, bytes)):
        raise LoaderError("sample_ids must be a sequence of audio2tool sample ids")
    wanted: dict[str, list[str]] = {}
    seen: set[str] = set()
    for sample_id in sample_ids:
        if not isinstance(sample_id, str) or not _SAMPLE_ID_RE.fullmatch(sample_id):
            raise LoaderError(
                f"{sample_id!r} is not an audio2tool sample id of the shape "
                "'<tier>:<six digits>'"
            )
        if sample_id in seen:
            raise LoaderError(f"duplicate audio2tool sample id {sample_id!r}")
        seen.add(sample_id)
        tier, _, _ = sample_id.partition(":")
        wanted.setdefault(tier, []).append(sample_id)

    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    public_dir = carrier_dir / "public"
    if not public_dir.is_dir():
        raise LoaderError(f"audio2tool public directory missing: {public_dir}")

    rows: dict[str, dict[str, str]] = {}
    for tier in sorted(wanted):
        manifest = _tier_manifest(public_dir, tier)
        for sample_id in sorted(wanted[tier]):
            entry = manifest.get(int(sample_id.partition(":")[2]))
            if entry is None:
                raise LoaderError(
                    f"sample {sample_id!r} has no row in the {tier} manifest"
                )
            query = entry.get("query")
            tool_name = entry.get("tool_name")
            gold_call = entry.get("expected_tool_call")
            for field, value in (
                ("query", query),
                ("tool_name", tool_name),
                ("expected_tool_call", gold_call),
            ):
                if not isinstance(value, str) or not value.strip():
                    raise LoaderError(
                        f"sample {sample_id!r} has no usable {field} in the {tier} manifest"
                    )
            rows[sample_id] = {
                "query": str(query).strip(),
                "gold_call": str(gold_call).strip(),
                "tool_name": str(tool_name).strip(),
            }
    return rows


def load_media_rows(
    lock: Mapping[str, object],
    root: Path,
    sample_ids: Sequence[str],
) -> dict[str, dict[str, object]]:
    """Measured media facts for EXACTLY the named samples.

    The same four facts a flight-roster receipt records --
    ``media_relpath``/``audio_seconds``/``audio_sha256``/``sample_rate_hz`` --
    resolved the way :func:`load_audio2tool` resolves them (the manifest's own
    ``path``/``duration``, or the final user turn's for tier7) and MEASURED
    from the file rather than trusted from the manifest: the sha256 is over
    the bytes on disk and the sample rate comes from the wav header.

    Identity-scoped for the same reason :func:`load_query_rows` is: the EVO-A1
    proposer roster's anchors are construction rows outside every probe-sample
    receipt, so the receipt-scoped loader cannot see them. It carries NO
    ground-truth field, so it is a runtime-safe reader.
    """

    if isinstance(sample_ids, (str, bytes)):
        raise LoaderError("sample_ids must be a sequence of audio2tool sample ids")
    entry = lock_entry(lock, AUDIO2TOOL_LOCK_KEY)
    subdir = str(entry["local_subdir"]).rstrip("/")
    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    public_dir = carrier_dir / "public"
    if not public_dir.is_dir():
        raise LoaderError(f"audio2tool public directory missing: {public_dir}")

    wanted: dict[str, list[str]] = {}
    for sample_id in sample_ids:
        if not isinstance(sample_id, str) or not _SAMPLE_ID_RE.fullmatch(sample_id):
            raise LoaderError(
                f"{sample_id!r} is not an audio2tool sample id of the shape "
                "'<tier>:<six digits>'"
            )
        wanted.setdefault(sample_id.partition(":")[0], []).append(sample_id)

    rows: dict[str, dict[str, object]] = {}
    for tier in sorted(wanted):
        manifest = _tier_manifest(public_dir, tier)
        for sample_id in sorted(set(wanted[tier])):
            manifest_entry = manifest.get(int(sample_id.partition(":")[2]))
            if manifest_entry is None:
                raise LoaderError(
                    f"sample {sample_id!r} has no row in the {tier} manifest"
                )
            relative, audio_seconds = _entry_media(manifest_entry, sample_id)
            media_relpath = f"{subdir}/public/{relative}"
            media_path = Path(root) / media_relpath
            if not media_path.is_file():
                raise LoaderError(f"{sample_id}: media missing: {media_path}")
            rows[sample_id] = {
                "media_relpath": media_relpath,
                "audio_seconds": audio_seconds,
                "audio_sha256": hashlib.sha256(media_path.read_bytes()).hexdigest(),
                "sample_rate_hz": _wav_sample_rate(media_path, sample_id),
            }
    return rows


_REGISTRY_COLUMNS = (
    "tool_id",
    "domain",
    "category",
    "tool_name",
    "signature",
    "description",
    "argument_defaults",
    "argument_constraints",
)


def _load_registry_rows_with_sha256(
    lock: Mapping[str, object], root: Path
) -> tuple[tuple[tuple[int, dict[str, str]], ...], str]:
    """Every ``tools_registry.csv`` row, parsed and validated, sorted by
    numeric ``tool_id``, plus the SHA-256 of the exact bytes parsed."""

    import csv

    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    path = carrier_dir / "tools_registry.csv"
    if not path.is_file():
        raise LoaderError(f"audio2tool tools_registry.csv missing: {path}")
    try:
        raw = path.read_bytes()
        with io.StringIO(raw.decode("utf-8-sig"), newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            missing = [column for column in _REGISTRY_COLUMNS if column not in fields]
            if missing:
                raise LoaderError(f"tools_registry.csv lacks required columns {missing}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise LoaderError(f"cannot read tools_registry.csv {path}: {error}") from error
    if not rows:
        raise LoaderError(f"tools_registry.csv {path} has no rows")
    parsed: list[tuple[int, dict[str, str]]] = []
    seen_ids: set[int] = set()
    for row in rows:
        try:
            tool_id = int(str(row["tool_id"]).strip())
        except (TypeError, ValueError) as error:
            raise LoaderError(f"tools_registry.csv has a non-numeric tool_id: {error}") from error
        if tool_id in seen_ids:
            raise LoaderError(f"tools_registry.csv has a duplicate tool_id {tool_id}")
        seen_ids.add(tool_id)
        name = row.get("tool_name")
        signature = row.get("signature")
        if not name or not signature:
            raise LoaderError(f"tools_registry.csv row {tool_id} lacks tool_name/signature")
        parsed.append(
            (tool_id, {column: (row.get(column) or "") for column in _REGISTRY_COLUMNS})
        )
    parsed.sort(key=lambda pair: pair[0])
    return tuple(parsed), hashlib.sha256(raw).hexdigest()


def _load_registry_rows(
    lock: Mapping[str, object], root: Path
) -> tuple[tuple[int, dict[str, str]], ...]:
    """Compatibility view of the shared source-bound registry parse."""

    rows, _source_sha256 = _load_registry_rows_with_sha256(lock, root)
    return rows


def render_registry_row(row: Mapping[str, str], *, strip_defaults: bool = False) -> str:
    """Canonical one-line JSON rendering of a SINGLE registry row -- the
    exact per-row format :func:`render_tool_schemas` joins with newlines
    for all 152 rows, extracted here so a caller (e.g. a supply-narrowing
    probe) can render an arbitrary SUBSET of rows with byte-identical
    per-row formatting.

    ``strip_defaults=True`` (Stage-2b's B1 arm, corruption-channel probe:
    ``docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md``
    section 1, Q-A) REMOVES the ``argument_defaults`` KEY entirely rather
    than blanking its value -- "schema structure + constraints only, no
    values" (the prereg's own wording) reads as the key being ABSENT, not
    present-but-empty, since an empty-string value is already how a tool
    with genuinely no defaults renders today (indistinguishable from
    "stripped" under blanking). Every other key/value and the JSON
    formatting convention (``sort_keys=True``, ``ensure_ascii=False``) stay
    byte-identical to the ``strip_defaults=False`` rendering."""

    payload = dict(row)
    if strip_defaults:
        payload.pop("argument_defaults", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def load_tool_registry(lock: Mapping[str, object], root: Path) -> tuple[dict[str, str], ...]:
    """Every ``tools_registry.csv`` row, sorted by numeric ``tool_id`` --
    the SAME rows :func:`render_tool_schemas` flattens into one string, but
    exposed per-row (each a plain ``{column: value}`` dict over
    ``_REGISTRY_COLUMNS``, ``tool_name`` included) for a caller that needs
    PER-TOOL lookup (e.g. keying a subset roster by ``tool_name``) rather
    than the flattened all-152 string."""

    return tuple(row for _tool_id, row in _load_registry_rows(lock, root))


def load_tool_registry_with_sha256(
    lock: Mapping[str, object], root: Path
) -> tuple[tuple[dict[str, str], ...], str]:
    """Public rows paired with the hash of the exact registry bytes parsed."""

    rows, source_sha256 = _load_registry_rows_with_sha256(lock, root)
    return tuple(row for _tool_id, row in rows), source_sha256


def render_tool_schemas(lock: Mapping[str, object], root: Path) -> str:
    """The deterministic ``{tool_schemas}`` fill for the frozen P1 prompt
    template: the FULL ``tools_registry.csv`` (the paper's direct protocol
    prompts with the full tool schema), one canonical JSON object per line,
    sorted by numeric ``tool_id``."""

    rows = _load_registry_rows(lock, root)
    return "\n".join(render_registry_row(row) for _tool_id, row in rows)
