"""Deterministic four-fragment config composition (model/dataset/baseline/experiment).

JSON, stdlib-only, no override semantics: top-level keys must be disjoint
across fragments so a later fragment can never silently rewrite an earlier
one. The composed hash and the protocol hash are the identity cells every
formal ledger row carries.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..scoring import SCORING_STACK_VERSION
from .reasoning_knobs import (
    ReasoningKnobError,
    fold_into_decoding,
    validate_fragment_knobs,
    validate_thinking_policy,
)
from .data_root_placeholder import DATA_ROOT_PLACEHOLDER, collapse_data_root, expand_data_root, resolve_data_root_text  # noqa: F401 (re-exported)

_KINDS = ("model", "dataset", "baseline", "experiment")
_FRAGMENT_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# A model fragment may pin a SECOND runtime receipt (e.g.
# "receipts/runtime-q4km.json" for a Q4_K_M pinned model alongside the
# default Q8_0) via an optional top-level "runtime_receipt" key, relative to
# the study repo's docs/ directory. Every fragment that predates this key
# (and every fragment that simply never sets it) resolves to exactly this
# same default -- unchanged behaviour, unchanged config_hash for any
# fragment that omits the key entirely (the default is applied here, at
# CONSUMPTION time, never injected into `compose()`'s merged dict, so an
# existing fragment's canonical hash never shifts under it). A fragment that
# DOES set the key changes `config_hash` -> `protocol_hash` automatically,
# the same way any other model-config key already does: `compose()` merges
# every fragment's top-level keys verbatim before hashing.
DEFAULT_RUNTIME_RECEIPT_RELPATH = "receipts/runtime.json"
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# WAVE W4 (owner Decision 11-B change #6, 2026-09-08). The four config TABLES
# a harness module's ON/OFF switch lives in (``rails.config_tables``, which
# asserts it names exactly these four). Each has a NULL ARM, and the design
# note's admission gate (``docs/readiness/
# 2026-09-08-agent-system-episode-and-core-pressure-v1.md`` section 8) requires
# the contrast to be "module ON versus module OFF in the same harness on the
# same roster (one config key, never a second code path)". That is only true
# if the OFF arm and a fragment that never mentioned the table are the SAME
# CELL: a config hash that moved when a table was written out as ``null``
# would make the OFF arm a third cell identity, and the paired arm would no
# longer be a twin of the pre-table baseline.
#
# So a table key whose value is its null arm is dropped BEFORE hashing, and
# dropped from the composed ``values`` too (a consumer reading ``values.get
# ("observe")`` gets ``None`` either way, which is what it already means).
# The rule is deliberately NARROW -- these four keys only, never a general
# "drop every null" -- because elsewhere in this study an explicit ``null``
# is a real declaration: ``d1_media_supplement``, for one, is refused unless
# it and its sha256 are BOTH present or BOTH absent, and a blanket rule would
# quietly erase that pairing.
#
# No committed fragment's hash moves under this rule: no fragment under
# ``configs/{model,dataset,baseline,experiment}/`` carries any of these four
# keys with a null arm (proved by
# ``tests/unit/test_config_tables.py::test_no_committed_fragment_declares_a_
# null_arm_so_no_existing_config_hash_moves``).
NULL_ARM_TABLE_KEYS = ("judges", "knowledge_views", "observe", "toolkits")

# The two spellings of a null arm. ``{}`` is included because the loaders
# already treat an empty object exactly as they treat an absent block
# (``rails.phase_review.load_phase_review_specs`` has since E6's own pattern);
# leaving the hash to disagree with the semantics would put two identities on
# one cell.
_NULL_ARM_VALUES: tuple[object, ...] = (None, {})


class ConfigError(RuntimeError):
    """A config fragment is missing, unreadable, or collides with another."""


#: The only two frozen-source-receipt roots ``core.preparation.
#: verify_source_receipts`` resolves at prepare time.  Kept in sync with
#: that function's own ``roots = {"repository": ..., "data": ...}`` mapping
#: by ``test_config_composition.py``'s cross-check.
_PREPARATION_SOURCE_RECEIPT_ROOTS = frozenset({"repository", "data"})
_PREPARATION_SOURCE_RECEIPT_PIN_KEYS = frozenset({"root", "relpath", "sha256"})


def assert_preparation_source_receipts_are_well_formed(
    values: Mapping[str, object],
) -> None:
    """Refuse a malformed ``preparation_source_receipts`` pin at config LOAD
    time, structurally, before ``core.preparation.verify_source_receipts``
    ever walks the filesystem for it at prepare time.

    This never touches a filesystem (no ``repo_root``/``data_root`` is known
    at composition time) and never checks a SHA-256 against real bytes --
    only the exact three-key shape and the two accepted ``root`` names that
    ``verify_source_receipts`` itself enforces. A config whose pin already
    passes this can still fail ``verify_source_receipts`` later (missing
    file, hash mismatch); a config that fails this can never reach that far.

    Three real committed fragments (``configs/baseline/
    slurp-native-dual-store-train-fold-a-exemplars-k20{,-twin}-v1.json`` and
    the ``-k12-v1`` sibling) pinned a receipt with ``"root": "repo"`` --
    accepted by nothing, refused only once ``prepare-supply`` actually read
    it, hundreds of steps into a flight. This closes that gap at the
    cheapest possible point: the moment ``compose()`` merges the fragment
    that declared it.
    """

    receipts = values.get("preparation_source_receipts")
    if receipts is None:
        return
    if not isinstance(receipts, list) or not receipts:
        raise ConfigError("preparation_source_receipts must be a non-empty list")
    for pin in receipts:
        if (
            not isinstance(pin, Mapping)
            or set(pin) != _PREPARATION_SOURCE_RECEIPT_PIN_KEYS
            or not isinstance(pin.get("root"), str)
            or pin["root"] not in _PREPARATION_SOURCE_RECEIPT_ROOTS
            or not isinstance(pin.get("relpath"), str)
            or not pin["relpath"]
            or not isinstance(pin.get("sha256"), str)
            or _SHA256.fullmatch(pin["sha256"]) is None
        ):
            raise ConfigError(
                "preparation_source_receipts pin must be exactly "
                "{root, relpath, sha256} with root in "
                f"{sorted(_PREPARATION_SOURCE_RECEIPT_ROOTS)} and sha256 a "
                f"lowercase 64-hex digest, got {pin!r}"
            )


def assert_reasoning_knobs_are_well_formed(values: Mapping[str, object]) -> None:
    """Thinking-core harness knobs (decision 283 A): validate the model-fragment knobs and the per-node ``thinking_policy``.

    Fail-closed at composition time, before any contact: ``max_tokens`` must equal budget + reserve, an Instruct fragment may
    carry only ``reasoning_context_policy``, the pinned forced-close message hash must match the ``server_args`` value, and
    every node override must resolve inside the geometry cap. A config that declares none of these is untouched.
    """

    try:
        validate_fragment_knobs(values)
        validate_thinking_policy(values.get("thinking_policy"), values)
    except ReasoningKnobError as error:
        raise ConfigError(str(error)) from error


_REQUEST_INTEGER_BOUNDS = {
    "max_tokens": (1, None),
    "seed": (0, 2**32 - 2),  # UINT32_MAX asks llama.cpp for a random seed.
    "top_k": (0, None),
}
_REQUEST_NUMERIC_BOUNDS = {
    "temperature": (0, 2),
    "top_p": (0, 1),
    "min_p": (0, 1),
    "presence_penalty": (-2, 2),
    "frequency_penalty": (-2, 2),
}


def effective_request_decoding_params(values: Mapping[str, object]) -> object:
    """Resolve explicit request sampling/caps without changing serving identity.

    Preserve the original mapping when no override is declared. Request-only
    fields change the composed experiment hash and actual request bytes, never
    weights, geometry, slot allocation, tool controls or role-owned schemas.
    """
    declared = values.get("decoding_params")
    override = values.get("request_decoding_overrides")
    if override is None:
        return declared
    allowed = _REQUEST_INTEGER_BOUNDS.keys() | _REQUEST_NUMERIC_BOUNDS.keys()
    if not isinstance(override, Mapping) or not override or not set(override) <= allowed:
        raise ConfigError(
            "request_decoding_overrides must be a non-empty mapping of supported "
            f"request-only fields: {sorted(allowed)}"
        )
    for key, value in override.items():
        integer = key in _REQUEST_INTEGER_BOUNDS
        low, high = (_REQUEST_INTEGER_BOUNDS if integer else _REQUEST_NUMERIC_BOUNDS)[key]
        valid_type = isinstance(value, int) if integer else isinstance(value, (int, float))
        if (
            isinstance(value, bool) or not valid_type
            or (isinstance(value, float) and not math.isfinite(value))
            or value < low or (high is not None and value > high)
        ):
            raise ConfigError(
                f"request_decoding_overrides.{key} must be a "
                f"{'non-boolean integer' if integer else 'finite number'} "
                f"in [{low}, {high if high is not None else 'unbounded'}]"
            )
    if declared is None:
        resolved: dict[str, object] = {}
    elif isinstance(declared, Mapping):
        resolved = dict(declared)
    else:
        raise ConfigError("decoding_params must be a mapping when declared")
    resolved.update(override)
    budget, reserve = resolved.get("thinking_budget_tokens"), values.get("answer_reserve_tokens")
    if budget is not None and reserve is not None and resolved.get("max_tokens") != budget + reserve:
        raise ConfigError(
            "request_decoding_overrides.max_tokens must keep max_tokens equal to reasoning_budget_tokens + "
            "answer_reserve_tokens"
        )
    return resolved


def effective_request_values(values: Mapping[str, object]) -> Mapping[str, object]:
    """Return values with declared request sampling and caps applied purely."""
    decoded = effective_request_decoding_params(values)
    if values.get("request_decoding_overrides") is None:
        return values
    resolved = dict(values)
    resolved["decoding_params"] = decoded
    return resolved


def _reject_duplicate_keys(fragment_path: Path):
    """``object_pairs_hook`` factory (M-5 fix): a human reading a JSON
    fragment top-to-bottom sees the FIRST value for a repeated key, but
    ``json.loads``'s default dict-building silently keeps the LAST -- the
    two readers of the same fragment (a person, and this composer) would
    disagree about what the fragment means. Raising here, at parse time,
    turns that silent last-write-wins behavior into a fail-closed
    :class:`ConfigError` naming both the offending key and the fragment
    file, before the duplicate can ever reach ``compose``'s own (unrelated)
    cross-fragment collision check below."""

    def hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ConfigError(
                    f"config fragment {fragment_path} has a duplicate key {key!r}; "
                    "a human reading it top-to-bottom sees the FIRST value but JSON "
                    "parsing would otherwise silently keep the LAST -- refused"
                )
            seen[key] = value
        return seen

    return hook


@dataclass(frozen=True)
class ComposedConfig:
    values: Mapping[str, object]
    config_hash: str
    fragments: Mapping[str, str]


def drop_null_arms(values: Mapping[str, object]) -> dict[str, object]:
    """``values`` without any :data:`NULL_ARM_TABLE_KEYS` key that carries its
    null arm (``null`` or ``{}``).

    The one place the null-arm rule is implemented, so the composed hash, the
    composed ``values`` and a single fragment's own hash can never disagree
    about it. A mapping that declares none of the four table keys comes back
    unchanged, which is every fragment committed before WAVE W4.
    """

    return {
        key: value
        for key, value in values.items()
        if not (key in NULL_ARM_TABLE_KEYS and any(value == arm for arm in _NULL_ARM_VALUES))
    }


def _canonical_hash(document: Mapping[str, object]) -> str:
    # A document that carries the resolved data root (an expanded composed config) hashes as its placeholder form.
    document = collapse_data_root(document)
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def fragment_path(repo_root: Path, kind: str, name: str) -> Path:
    """``<repo_root>/configs/<kind>/<name>.json``, with the fragment-name
    pattern :func:`compose` enforces applied to ``name`` first."""

    if kind not in _KINDS:
        raise ConfigError(f"unknown config fragment kind {kind!r}; known kinds are {_KINDS}")
    if not isinstance(name, str) or not _FRAGMENT_NAME_PATTERN.fullmatch(name):
        raise ConfigError(f"invalid config fragment name for {kind}: {name!r}")
    return Path(repo_root) / "configs" / kind / f"{name}.json"


def read_fragment(repo_root: Path, kind: str, name: str) -> dict[str, object]:
    """ONE config fragment's own top-level object, read exactly the way
    :func:`compose` reads it (duplicate top-level keys refused before
    ``json.loads`` can silently keep the last value).

    Split out of :func:`compose` so a caller that legitimately has only ONE
    fragment -- the operator-run serving session, which composes no dataset,
    baseline or experiment -- reads it through the same rules a flight does,
    rather than a second ``json.loads`` with different discipline.
    """

    path = fragment_path(repo_root, kind, name)
    if not path.is_file():
        raise ConfigError(f"missing config fragment: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ConfigError(f"cannot read config fragment {path}: {error}") from error
    try:
        # M-5 fix: object_pairs_hook rejects a duplicate top-level key
        # before json.loads ever builds the (last-value-wins) dict --
        # ConfigError raised inside the hook propagates straight out of
        # json.loads uncaught below, since it is not a json.JSONDecodeError.
        fragment = json.loads(text, object_pairs_hook=_reject_duplicate_keys(path))
    except json.JSONDecodeError as error:
        raise ConfigError(f"cannot read config fragment {path}: {error}") from error
    if not isinstance(fragment, dict):
        raise ConfigError(f"config fragment {path} must be a JSON object")
    return fragment


def fragment_hash(fragment: Mapping[str, object]) -> str:
    """The canonical SHA-256 of ONE fragment's own object -- the same
    canonicalization :func:`compose` applies to the merged four, including
    the WAVE W4 null-arm rule (:func:`drop_null_arms`)."""

    return _canonical_hash(drop_null_arms(fragment))


def compose(
    repo_root: Path,
    model: str,
    dataset: str,
    baseline: str,
    experiment: str,
    data_root: "str | Path | None" = None,
) -> ComposedConfig:
    names = dict(zip(_KINDS, (model, dataset, baseline, experiment)))
    merged: dict[str, object] = {}
    origins: dict[str, str] = {}
    for kind in _KINDS:
        fragment = read_fragment(repo_root, kind, names[kind])
        for key, value in fragment.items():
            if key in merged:
                raise ConfigError(
                    f"config key collision: {key!r} defined by {origins[key]} and {kind}"
                )
            merged[key] = value
            origins[key] = kind
    # WAVE W4: a table key carrying its null arm is dropped here -- AFTER the
    # cross-fragment collision check above, so declaring "observe": null in
    # one fragment and an observe table in another is still the collision it
    # is, and not silently resolved in the table's favour.
    composed = drop_null_arms(merged)
    assert_preparation_source_receipts_are_well_formed(composed)
    assert_reasoning_knobs_are_well_formed(composed)
    # The knobs are the single hashed source of the two reasoning wire fields; they fold into decoding_params HERE so every
    # consumer of the composed values sees the identical request shape. A config without knobs composes byte-identically.
    folded = fold_into_decoding(composed)
    if folded is not None:
        composed = folded
    # The hash is over the unexpanded text; consumers get the expanded values (DATA_ROOT_PLACEHOLDER).
    return ComposedConfig(
        values=expand_data_root(composed, data_root), config_hash=_canonical_hash(composed), fragments=names
    )


def runtime_receipt_relpath(values: Mapping[str, object]) -> str:
    """Resolve a composed config's ``runtime_receipt`` model key (relative to
    the study repo's ``docs/`` directory), defaulting to today's committed
    ``receipts/runtime.json`` when the key is absent -- so every fragment
    that predates the key, or simply never sets it, behaves identically to
    before. Fails closed (``ConfigError``) on a malformed value: this string
    is about to be joined onto a filesystem path (``resolve_runtime_receipt_
    path``), so the same absolute/drive-letter/backslash/traversal refusals
    the rest of this study applies to any path-shaped config value apply
    here too, before it ever reaches a caller."""

    value = values.get("runtime_receipt", DEFAULT_RUNTIME_RECEIPT_RELPATH)
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"model config runtime_receipt must be a non-empty string, got {value!r}"
        )
    if "\\" in value:
        raise ConfigError(f"model config runtime_receipt must not contain a backslash: {value!r}")
    if value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ConfigError(f"model config runtime_receipt must be relative, got {value!r}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ConfigError(
            f"model config runtime_receipt contains an empty or traversal segment: {value!r}"
        )
    return value


# A CARRIER-PREFIXED ALIAS of the plain D1 media-supplement pair, e.g.
# ``a2t_calibration_d1_media_supplement`` +
# ``a2t_calibration_d1_media_supplement_sha256``. Two readers of the same
# fragment disagreed about which spelling is the declaration, and a cell died
# of it (2026-09-09, ``docs/readiness/
# 2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``): ``core.base.
# declared_derived_media_roots`` reads the PREFIXED pair to widen payload
# confinement, while ``core.flight.FlightRuntime.preflight`` builds the media
# IDENTITY gate from the PLAIN pair only. Six Audio2Tool derived-media
# fragments carried the prefixed pair alone, so confinement was satisfied and
# the identity gate saw no supplement at all -- every roster id refused as
# "outside D1's identity closure" at the first real request.
#
# The rule below makes that state unrepresentable rather than merely fixed:
# a prefixed spelling that is a REAL declaration must be matched, value for
# value, by the plain pair the gate actually reads.
_D1_MEDIA_SUPPLEMENT_ALIAS = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_d1_media_supplement$")


def assert_d1_media_supplement_spellings_agree(values: Mapping[str, object]) -> None:
    """Refuse a config whose carrier-prefixed D1 media supplement disagrees
    with -- or is not accompanied by -- the plain pair the gate reads.

    A prefixed key is a real DECLARATION exactly when its own
    ``..._sha256`` companion is a lowercase 64-hex digest; that is the same
    discriminator ``core.base._assert_d1_media_supplement`` already uses, and
    it is what tells a declaration apart from the several fragments that
    carry a prefixed key as PROSE explaining why they need no supplement
    (``audio2tool-calibration-400.json``: "none, by design ..."). Prose is
    inert here, as it is there.

    For every real prefixed declaration, two things must hold:

    1. the plain ``d1_media_supplement`` / ``d1_media_supplement_sha256``
       pair must be present -- a fragment that declares a supplement ONLY
       under a prefixed key is refused, because the identity gate would
       silently see no supplement at all; and
    2. both halves must be equal to the prefixed values -- when both
       spellings exist they name the same artifact and the same bytes, or
       the fragment is refused.
    """

    plain_path = values.get("d1_media_supplement")
    plain_digest = values.get("d1_media_supplement_sha256")
    for key in sorted(values):
        if _D1_MEDIA_SUPPLEMENT_ALIAS.fullmatch(key) is None:
            continue
        digest_key = f"{key}_sha256"
        alias_digest = values.get(digest_key)
        if not isinstance(alias_digest, str) or _SHA256.fullmatch(alias_digest) is None:
            continue
        alias_path = values.get(key)
        if plain_path is None and plain_digest is None:
            raise ConfigError(
                f"config declares a D1 media supplement under {key!r} + {digest_key!r} "
                "but not under the plain d1_media_supplement / "
                "d1_media_supplement_sha256 pair; the media identity gate reads ONLY "
                "the plain pair, so a prefixed-only declaration widens payload "
                "confinement while leaving every sample outside D1's identity closure"
            )
        if alias_path != plain_path or alias_digest != plain_digest:
            raise ConfigError(
                f"config declares the D1 media supplement twice and the two spellings "
                f"disagree: {key!r}={alias_path!r} / {digest_key!r}={alias_digest!r} "
                f"against d1_media_supplement={plain_path!r} / "
                f"d1_media_supplement_sha256={plain_digest!r}"
            )


def _d1_media_supplement_pair(
    values: Mapping[str, object],
) -> tuple[object | None, object | None]:
    assert_d1_media_supplement_spellings_agree(values)
    path = values.get("d1_media_supplement")
    digest = values.get("d1_media_supplement_sha256")
    if (path is None) != (digest is None):
        raise ConfigError(
            "model config d1_media_supplement and d1_media_supplement_sha256 "
            "must be configured together"
        )
    return path, digest


def d1_media_supplement_relpath(values: Mapping[str, object]) -> str | None:
    """Return the optional, protocol-bound D1 media supplement path.

    Supplements are additive successors for a bounded carrier slice that was
    outside the original immutable D1 closure. The path is relative to
    ``<repo_root>/docs`` and is accepted only together with its exact SHA-256,
    so selecting different bytes changes the composed protocol identity.
    """

    value, _digest = _d1_media_supplement_pair(values)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"model config d1_media_supplement must be a non-empty string, got {value!r}"
        )
    if "\\" in value:
        raise ConfigError(
            f"model config d1_media_supplement must not contain a backslash: {value!r}"
        )
    if value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ConfigError(
            f"model config d1_media_supplement must be relative, got {value!r}"
        )
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ConfigError(
            "model config d1_media_supplement contains an empty or traversal "
            f"segment: {value!r}"
        )
    return value


def d1_media_supplement_sha256(values: Mapping[str, object]) -> str | None:
    """Return the exact digest paired with :func:`d1_media_supplement_relpath`."""

    _path, value = _d1_media_supplement_pair(values)
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ConfigError(
            "model config d1_media_supplement_sha256 must be a lowercase 64-hex SHA-256"
        )
    return value


def _d1_evidence_supplement_pair(
    values: Mapping[str, object],
) -> tuple[object | None, object | None]:
    path = values.get("d1_evidence_supplement")
    digest = values.get("d1_evidence_supplement_sha256")
    if (path is None) != (digest is None):
        raise ConfigError(
            "model config d1_evidence_supplement and d1_evidence_supplement_sha256 "
            "must be configured together"
        )
    return path, digest


def d1_evidence_supplement_relpath(values: Mapping[str, object]) -> str | None:
    """Return the optional, protocol-bound D1 EVIDENCE-layer supplement path.

    The evidence-layer counterpart of :func:`d1_media_supplement_relpath`, with
    the same rules: additive successor for a layer the immutable D1 closure does
    not carry, relative to ``<repo_root>/docs``, accepted only together with its
    exact SHA-256, so selecting different bytes changes the composed protocol
    identity. ``contracts.FrozenCoreGate`` additionally refuses a configuration
    that carries BOTH supplements.
    """

    value, _digest = _d1_evidence_supplement_pair(values)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"model config d1_evidence_supplement must be a non-empty string, got {value!r}"
        )
    if "\\" in value:
        raise ConfigError(
            f"model config d1_evidence_supplement must not contain a backslash: {value!r}"
        )
    if value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ConfigError(
            f"model config d1_evidence_supplement must be relative, got {value!r}"
        )
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ConfigError(
            "model config d1_evidence_supplement contains an empty or traversal "
            f"segment: {value!r}"
        )
    return value


def d1_evidence_supplement_sha256(values: Mapping[str, object]) -> str | None:
    """Return the exact digest paired with :func:`d1_evidence_supplement_relpath`."""

    _path, value = _d1_evidence_supplement_pair(values)
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ConfigError(
            "model config d1_evidence_supplement_sha256 must be a lowercase 64-hex SHA-256"
        )
    return value


def model_lock_key(values: Mapping[str, object]) -> str:
    """Resolve a composed config's ``model_lock_key`` -- the pinned model
    THIS RUN declares. Read directly, no default: every model fragment names
    its own frozen umbrella-lock entry explicitly (unlike ``runtime_receipt``,
    which is genuinely optional), so an omitted or malformed value fails
    closed rather than silently falling back to any one model. This is the
    SAME declaration ``runtime_receipt_relpath`` already uses to pick the
    receipt FILE -- callers bind both to the identical ``values`` mapping so
    a run can never pair one model's config with a different model's
    receipt (``contracts.FrozenCoreGate``'s ``expected_model_lock_key``)."""

    value = values.get("model_lock_key")
    if not isinstance(value, str) or not value:
        raise ConfigError(f"model config model_lock_key must be a non-empty string, got {value!r}")
    return value


def model_materialization_root(values: Mapping[str, object]) -> str | None:
    """Return the explicit root holding lock-relative model bytes.

    The canonical dataset root remains the default when the model fragment
    omits this key.  A configured value is a POSIX absolute path because all
    formal inference runs execute inside WSL2; relative paths, traversal,
    repeated separators, backslashes and non-string values are refused before
    they can select a different host file by accident.
    """

    value = values.get("model_materialization_root")
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            "model config model_materialization_root must be a non-empty POSIX "
            f"absolute path, got {value!r}"
        )
    if not value.startswith("/") or "\\" in value:
        raise ConfigError(
            "model config model_materialization_root must be a POSIX absolute "
            f"path, got {value!r}"
        )
    if any(part in ("", ".", "..") for part in value[1:].split("/")):
        raise ConfigError(
            "model config model_materialization_root contains an empty or "
            f"traversal segment: {value!r}"
        )
    return value


def feature_encoder_runtime_receipt_relpath(values: Mapping[str, object]) -> str | None:
    """Return the optional preprocess-role receipt path with runtime grammar."""

    value = values.get("feature_encoder_runtime_receipt")
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            "model config feature_encoder_runtime_receipt must be a non-empty string"
        )
    if "\\" in value or value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ConfigError(
            "model config feature_encoder_runtime_receipt must be a relative POSIX path"
        )
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ConfigError(
            "model config feature_encoder_runtime_receipt contains an empty or traversal segment"
        )
    return value


def resolve_feature_encoder_runtime_receipt_path(
    repo_root: Path, values: Mapping[str, object]
) -> Path | None:
    relative = feature_encoder_runtime_receipt_relpath(values)
    return None if relative is None else Path(repo_root) / "docs" / relative


def prepared_window_feature_cache(
    values: Mapping[str, object],
) -> dict[str, object] | None:
    """Validate the optional prepared raw-audio feature-cache declaration."""

    value = values.get("prepared_window_feature_cache")
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "audit",
        "provenance",
        "expected_n_embd",
    }:
        raise ConfigError(
            "prepared_window_feature_cache must contain exactly audit, provenance, "
            "and expected_n_embd"
        )
    width = value["expected_n_embd"]
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ConfigError(
            "prepared_window_feature_cache.expected_n_embd must be a positive integer"
        )
    result: dict[str, object] = {"expected_n_embd": width}
    for name in ("audit", "provenance"):
        pin = value[name]
        if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
            raise ConfigError(
                f"prepared_window_feature_cache.{name} must contain exactly relpath and sha256"
            )
        relpath = pin["relpath"]
        sha256 = pin["sha256"]
        if (
            not isinstance(relpath, str)
            or not relpath
            or relpath.startswith("/")
            or "\\" in relpath
            or _DRIVE_PREFIX.match(relpath)
            or any(part in ("", ".", "..") for part in relpath.split("/"))
        ):
            raise ConfigError(
                f"prepared_window_feature_cache.{name}.relpath must be a confined "
                "relative POSIX path"
            )
        if not isinstance(sha256, str) or _SHA256.fullmatch(sha256) is None:
            raise ConfigError(
                f"prepared_window_feature_cache.{name}.sha256 must be a lowercase SHA256"
            )
        result[name] = {"relpath": relpath, "sha256": sha256}
    return result


def resolve_runtime_receipt_path(repo_root: Path, values: Mapping[str, object]) -> Path:
    """The absolute path a composed config's ``runtime_receipt`` key names,
    under ``<repo_root>/docs/`` -- the one place every caller (driver smoke,
    ``saea-driver run``, and ``contracts.FrozenCoreGate.for_study_repo``'s
    own default) should derive this path from, rather than each
    re-implementing the same join."""

    return Path(repo_root) / "docs" / runtime_receipt_relpath(values)


def protocol_hash(config_hash: str, arm: str, split_identity_hash: str) -> str:
    return _canonical_hash(
        {
            "arm": arm,
            "config": config_hash,
            "scoring": SCORING_STACK_VERSION,
            "split": split_identity_hash,
        }
    )
