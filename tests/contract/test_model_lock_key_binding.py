"""Cross-model identity binding: ``contracts.FrozenCoreGate`` must refuse a
run that pairs one pinned model's identity declaration with a runtime
receipt describing a DIFFERENT pinned model, in either direction.

Closes the gap named by ``docs/readiness/2026-08-09-int4-model-identity.md``:
``_validate_runtime`` used to assert the receipt's ``model_lock_key`` against
a single hardcoded module constant (``contracts.MODEL_LOCK_KEY``), so a
receipt selected via ``FrozenCoreGate.for_study_repo``'s ``runtime_receipt_
relpath`` for a SECOND, legitimately pinned model was refused outright --
even a genuinely, correctly built one -- because the gate never learned which
model this particular run actually declares. The fix threads a new
keyword-only ``expected_model_lock_key`` (default: the existing frozen Q8_0
constant, so every caller that does not opt in is byte-identical) through
``FrozenCoreGate`` itself, and ``_validate_runtime``/``_lock_model_entry``
now assert against THAT value instead of the bare module constant --
widening the rail without moving it for anyone who does not ask.

The receipt-PATH selection (which file gets read) was already covered by
``tests/unit/test_runtime_receipt_selection.py``; this module covers the
remaining half -- once the right file is read, is its CONTENT actually
required to describe the model this run declares.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import (
    MODEL_LOCK_KEY,
    FrozenCoreGate,
    GateClosed,
)

from gate_fixture import GateFixture

SECOND_MODEL_KEY = "qwen3-omni-30b-a3b-instruct-gguf-q4km"
SECOND_SUBDIR = f"models/{SECOND_MODEL_KEY}"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def _materialize_second_model_files(fixture: GateFixture) -> dict:
    """Write a second pinned model's on-disk GGUF files (distinct
    subdir/key) and return the runtime-receipt document that truthfully
    describes them -- the llama.cpp launcher/library block is reused
    verbatim (the design this study ships: the launcher is model-agnostic,
    only ``-m``/``--mmproj`` change per model). Deliberately does NOT touch
    ``fixture.lock`` -- callers that need the lock entry too call
    :func:`_add_second_model_lock_entry` separately, so a test can exercise
    "receipt+files exist but the lock entry does not" on its own."""

    gguf_1 = b"GGUF-fake-q4km-shard-one" * 48
    gguf_2 = b"GGUF-fake-q4km-mmproj" * 24
    model_dir = fixture.data_root / SECOND_SUBDIR
    model_dir.mkdir(parents=True)
    (model_dir / "model-q4km.gguf").write_bytes(gguf_1)
    (model_dir / "mmproj-bf16.gguf").write_bytes(gguf_2)

    return {
        "schema": fixture.runtime["schema"],
        "study": fixture.runtime["study"],
        "model_lock_key": SECOND_MODEL_KEY,
        "llama_cpp": dict(fixture.runtime["llama_cpp"]),
        "gguf_files": [
            {
                "path": f"{SECOND_SUBDIR}/model-q4km.gguf",
                "bytes": len(gguf_1),
                "sha256": _sha(gguf_1),
            },
            {
                "path": f"{SECOND_SUBDIR}/mmproj-bf16.gguf",
                "bytes": len(gguf_2),
                "sha256": _sha(gguf_2),
            },
        ],
        "runtime_libraries": [dict(entry) for entry in fixture.runtime["runtime_libraries"]],
    }


def _add_second_model_lock_entry(fixture: GateFixture, second_receipt: dict) -> None:
    total_bytes = sum(entry["bytes"] for entry in second_receipt["gguf_files"])
    fixture.lock["models"].append(
        {
            "name": SECOND_MODEL_KEY,
            "local_subdir": SECOND_SUBDIR,
            "files": len(second_receipt["gguf_files"]),
            "size_bytes": total_bytes,
        }
    )


def _write_second_world(world: GateFixture) -> "tuple[dict, str]":
    """Materialize the second model's files AND lock entry, persist the
    (now two-entry) lock and the E0 closure receipt, and return
    (second_receipt_document, second_receipt_path) -- everything a gate
    needs except the choice of which receipt/expected-key pair to open
    with."""

    second_receipt = _materialize_second_model_files(world)
    _add_second_model_lock_entry(world, second_receipt)
    world.lock_path.write_text(json.dumps(world.lock), encoding="utf-8")
    second_receipt_path = world.receipts / "runtime-second.json"
    second_receipt_path.write_text(json.dumps(second_receipt), encoding="utf-8")
    (world.receipts / "e0-closure.json").write_text(json.dumps(world.e0), encoding="utf-8")
    return second_receipt, second_receipt_path


# ---------------------------------------------------------------------------
# Defaults: byte-identical to before this change for every existing caller.
# ---------------------------------------------------------------------------


@pytest.mark.requires_wsl2_execution_authority
def test_default_expected_model_lock_key_is_the_frozen_constant(world):
    """Constructing a gate the OLD way (no ``expected_model_lock_key`` at
    all) still opens against the existing, unaltered Q8_0 receipt/lock/plan
    world -- the rail widened, but nothing moved for a caller who never
    opted in."""

    world.gate().assert_model_touch_allowed(world.plan())


def test_for_study_repo_defaults_expected_model_lock_key(tmp_path):
    gate = FrozenCoreGate.for_study_repo(tmp_path, tmp_path, tmp_path)
    assert gate.expected_model_lock_key == MODEL_LOCK_KEY


def test_for_study_repo_accepts_an_explicit_expected_model_lock_key(tmp_path):
    gate = FrozenCoreGate.for_study_repo(
        tmp_path, tmp_path, tmp_path, expected_model_lock_key=SECOND_MODEL_KEY
    )
    assert gate.expected_model_lock_key == SECOND_MODEL_KEY
    # Every other field is untouched by the new keyword-only parameter.
    default_gate = FrozenCoreGate.for_study_repo(tmp_path, tmp_path, tmp_path)
    assert gate.runtime_receipt == default_gate.runtime_receipt
    assert gate.e0_receipt == default_gate.e0_receipt
    assert gate.data_root == default_gate.data_root
    assert gate.runtime_root == default_gate.runtime_root
    assert gate.exposure_ledger == default_gate.exposure_ledger
    assert gate.source_root == default_gate.source_root


# ---------------------------------------------------------------------------
# THE cross-binding refusal, both directions.
# ---------------------------------------------------------------------------


@pytest.mark.requires_wsl2_execution_authority
def test_gate_refuses_a_run_that_declares_model_b_but_is_handed_model_as_receipt(world):
    """A run that DECLARES the second model (``expected_model_lock_key=B``)
    but is hand ed the first model's (Q8_0) already-committed receipt is
    refused -- the plain, pre-widening shape of the bug this task closes:
    selecting a different receipt FILE must never, by itself, open the gate
    for a model the run never declared."""

    gate = world.gate()  # runtime_receipt -> the Q8_0 receipt (model_lock_key == MODEL_LOCK_KEY)
    crossed = FrozenCoreGate(
        e0_receipt=gate.e0_receipt,
        runtime_receipt=gate.runtime_receipt,
        data_root=gate.data_root,
        lock_path=gate.lock_path,
        runtime_root=gate.runtime_root,
        exposure_ledger=gate.exposure_ledger,
        source_root=gate.source_root,
        expected_model_lock_key=SECOND_MODEL_KEY,
    )
    with pytest.raises(GateClosed, match="does not match"):
        crossed.assert_model_touch_allowed(world.plan())


@pytest.mark.requires_wsl2_execution_authority
def test_gate_refuses_the_reverse_pairing_too(world):
    """The symmetric direction: a run that declares model A (the default,
    unset) but is handed model B's genuinely, correctly-built receipt is
    refused too -- proves this is a real two-way identity check, not a
    one-sided string comparison that only happens to catch one direction."""

    _second_receipt, second_receipt_path = _write_second_world(world)
    gate = FrozenCoreGate(
        e0_receipt=world.receipts / "e0-closure.json",
        runtime_receipt=second_receipt_path,
        data_root=world.data_root,
        lock_path=world.lock_path,
        runtime_root=world.runtime_root,
        exposure_ledger=world.exposure_ledger,
        source_root=world.source_root,
        # expected_model_lock_key omitted -> defaults to MODEL_LOCK_KEY (model A)
    )
    with pytest.raises(GateClosed, match="does not match"):
        gate.assert_model_touch_allowed(world.plan())


@pytest.mark.requires_wsl2_execution_authority
def test_gate_opens_for_a_correctly_bound_second_model(world):
    """The actual unblock: a run that DECLARES model B and is handed model
    B's own genuinely-built receipt -- matching lock entry, matching on-disk
    GGUF bytes -- opens the gate exactly like the default (model A) case
    does."""

    _second_receipt, second_receipt_path = _write_second_world(world)
    gate = FrozenCoreGate(
        e0_receipt=world.receipts / "e0-closure.json",
        runtime_receipt=second_receipt_path,
        data_root=world.data_root,
        lock_path=world.lock_path,
        runtime_root=world.runtime_root,
        exposure_ledger=world.exposure_ledger,
        source_root=world.source_root,
        expected_model_lock_key=SECOND_MODEL_KEY,
    )
    gate.assert_model_touch_allowed(world.plan())


@pytest.mark.requires_wsl2_execution_authority
def test_gate_refuses_second_model_gguf_drift_too(world):
    """The widened rail is not merely a looser string check -- the SAME
    byte-level GGUF/size verification the Q8_0 path always had still applies
    to a correctly-bound second model: tampering its on-disk bytes refuses
    exactly like it always has."""

    second_receipt, second_receipt_path = _write_second_world(world)
    (world.data_root / SECOND_SUBDIR / "model-q4km.gguf").write_bytes(b"tampered")
    gate = FrozenCoreGate(
        e0_receipt=world.receipts / "e0-closure.json",
        runtime_receipt=second_receipt_path,
        data_root=world.data_root,
        lock_path=world.lock_path,
        runtime_root=world.runtime_root,
        exposure_ledger=world.exposure_ledger,
        source_root=world.source_root,
        expected_model_lock_key=SECOND_MODEL_KEY,
    )
    with pytest.raises(GateClosed, match="drift"):
        gate.assert_model_touch_allowed(world.plan())


@pytest.mark.requires_wsl2_execution_authority
def test_gate_refuses_missing_lock_entry_for_the_declared_second_model(world):
    """``_lock_model_entry`` must look the SECOND model up by its own
    ``expected_model_lock_key`` -- not the frozen Q8_0 constant -- so a
    receipt that already, correctly names the second model (this check
    passes) is STILL refused when the lock never gained that model's own
    entry, with the right diagnostic naming the declared key, never the
    Q8_0 one it is never compared against here."""

    second_receipt = _materialize_second_model_files(world)
    # Deliberately skip _add_second_model_lock_entry: the lock keeps only
    # its original Q8_0 entry, so SECOND_MODEL_KEY has none at all.
    world.lock_path.write_text(json.dumps(world.lock), encoding="utf-8")
    second_receipt_path = world.receipts / "runtime-second.json"
    second_receipt_path.write_text(json.dumps(second_receipt), encoding="utf-8")
    (world.receipts / "e0-closure.json").write_text(json.dumps(world.e0), encoding="utf-8")

    gate = FrozenCoreGate(
        e0_receipt=world.receipts / "e0-closure.json",
        runtime_receipt=second_receipt_path,
        data_root=world.data_root,
        lock_path=world.lock_path,
        runtime_root=world.runtime_root,
        exposure_ledger=world.exposure_ledger,
        source_root=world.source_root,
        expected_model_lock_key=SECOND_MODEL_KEY,
    )
    with pytest.raises(GateClosed, match=f"{SECOND_MODEL_KEY!r} not found in datasets lock"):
        gate.assert_model_touch_allowed(world.plan())
