"""Reuse capacity measurements only for an identical complete boundary."""
import copy
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError, canonical_bytes, digest, prepare_artifact,
)
from speech_aware_evidence_acquisition.core.preparation_fit import (
    boundary_identity, revalidate_phase_fit,
)


def world(tmp_path):
    payloads = ({"sample_id": "s1", "decoding_params": {"max_tokens": 256}},)
    old = {
        "config_sha256": "c" * 64, "split_identity_hash": "d" * 64,
        "sources": {"boundary_sha256": boundary_identity(payloads),
                    "required_identity": {"server": "same"},
                    "implementation": {"runtime": "a" * 64, "transport": "t" * 64}},
    }
    output = {
        "sample_count": 1, "rows": [{"sample_id": "s1", "fits": True}],
        "boundary_sha256": boundary_identity(payloads), "every_request_fits": True,
        "contact_counts": {"POST /tokenize": 2}, "contacts": 2,
        "generation_contacts": 0,
    }
    source = tmp_path / "measured.json"
    pin = prepare_artifact(source, kind="request-fit", inputs=old,
                           producer=lambda: output, contact_class="tokenizer")
    current = copy.deepcopy(old)
    current["sources"]["implementation"]["runtime"] = "b" * 64
    runtime = SimpleNamespace(
        materialize_phase_requests=lambda: payloads,
        preparation_context=lambda: {"sample_ids": ["s1"]},
        request_fit_inputs=lambda p: current,
    )
    registration = {
        "schema": "saea-request-fit-revalidation-registration-v1",
        "execution_profile": "model-free-check",
        "source": {"relpath": "measured.json", "sha256": pin["sha256"]},
        "source_inputs_sha256": digest(old),
        "implementation_changes": {"runtime": {"before": "a" * 64, "after": "b" * 64}},
        "output_relpath": "revalidated.json",
        "reason": "Restore synthetic state without changing requests.",
        "new_endpoint_contacts": 0,
    }
    journal = tmp_path / "measured.json.contacts.jsonl"
    journal.write_bytes(b"".join(canonical_bytes({
        "contact": i, "method": "POST", "route": "/tokenize",
    }) + b"\n" for i in (1, 2)))
    import hashlib
    registration["source_journal"] = {
        "relpath": journal.name, "sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
        "line_count": 2,
    }
    return runtime, registration, current, source


def execute(tmp_path, runtime, registration):
    return revalidate_phase_fit(
        runtime, registration=registration, registration_sha256=digest(registration),
        data_root=tmp_path,
    )


def test_revalidation_preserves_measurements_and_source_bytes(tmp_path):
    runtime, registration, _current, source = world(tmp_path)
    before = source.read_bytes()
    receipt = execute(tmp_path, runtime, registration)
    result = json.loads((tmp_path / "revalidated.json").read_bytes())
    assert result["contact_class"] == "model-free"
    assert result["output"]["rows"] == json.loads(before)["output"]["rows"]
    assert result["output"]["revalidation"]["new_endpoint_contacts"] == 0
    assert result["output"]["revalidation"]["source_measurement_contacts"] == 2
    assert result["output"]["contacts"] == 0
    assert source.read_bytes() == before
    assert execute(tmp_path, runtime, registration)["sha256"] == receipt["sha256"]


def test_revalidation_refuses_same_profile_journal_from_another_fit(tmp_path):
    runtime, registration, _current, source = world(tmp_path)
    source_journal = source.with_name(source.name + ".contacts.jsonl")
    other_journal = tmp_path / "other-fit.json.contacts.jsonl"
    other_journal.write_bytes(source_journal.read_bytes())
    import hashlib
    registration["source_journal"] = {
        "relpath": other_journal.name,
        "sha256": hashlib.sha256(other_journal.read_bytes()).hexdigest(),
        "line_count": 2,
    }

    with pytest.raises(PreparationError, match="source journal path"):
        execute(tmp_path, runtime, registration)
    assert not (tmp_path / "revalidated.json").exists()


@pytest.mark.parametrize("drift", ["boundary", "config", "split", "service", "undeclared-code",
                                  "wrong-code", "source-input-pin", "source-hash",
                                  "escape", "same-output", "profile", "contacts", "journal-hash", "journal-count"])
def test_revalidation_refuses_unapproved_or_request_visible_drift(tmp_path, drift):
    runtime, registration, current, source = world(tmp_path)
    if drift == "boundary":
        current["sources"]["boundary_sha256"] = "e" * 64
    elif drift == "config":
        current["config_sha256"] = "e" * 64
    elif drift == "split":
        current["split_identity_hash"] = "e" * 64
    elif drift == "service":
        current["sources"]["required_identity"]["server"] = "other"
    elif drift == "undeclared-code":
        current["sources"]["implementation"]["transport"] = "e" * 64
    elif drift == "wrong-code":
        current["sources"]["implementation"]["runtime"] = "e" * 64
    elif drift == "source-input-pin":
        registration["source_inputs_sha256"] = "e" * 64
    elif drift == "source-hash":
        source.write_bytes(source.read_bytes() + b" ")
    elif drift == "escape":
        registration["output_relpath"] = "../escape.json"
    elif drift == "same-output":
        registration["output_relpath"] = "measured.json"
    elif drift == "profile":
        registration["execution_profile"] = "bounded-discovery-probe"
    elif drift == "journal-hash":
        registration["source_journal"]["sha256"] = "e" * 64
    elif drift == "journal-count":
        registration["source_journal"]["line_count"] = 1
    else:
        registration["new_endpoint_contacts"] = 1
    with pytest.raises(PreparationError):
        execute(tmp_path, runtime, registration)
    assert not (tmp_path / "revalidated.json").exists()


@pytest.mark.parametrize("defect", ["incomplete", "failed", "duplicate"])
def test_revalidation_refuses_uncertified_source_rows(tmp_path, defect):
    runtime, registration, _current, source = world(tmp_path)
    doc = json.loads(source.read_bytes())
    if defect == "incomplete":
        doc["output"]["rows"] = []
    elif defect == "failed":
        doc["output"]["rows"][0]["fits"] = False
    else:
        doc["output"]["rows"] *= 2
    doc["output_sha256"] = digest(doc["output"])
    source.write_bytes(canonical_bytes(doc))
    import hashlib
    registration["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(PreparationError, match="full roster"):
        execute(tmp_path, runtime, registration)
