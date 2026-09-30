"""E5-0 tool pass (scripts/analysis/e5_asr_tool_pass.py) on fakes only.

No Whisper, model, GPU, audio decode or data-root write happens here: the producer is replaced by a fake
runner, the promotion receipt, dataset fragment, exposure ledger, umbrella lock and checkout are synthetic
(a temporary git repository), and the process list is injected.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "analysis" / "e5_asr_tool_pass.py"
HEADER = ("| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
          "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | "
          "notes |\n" + "| --- " * 15 + "|\n")


def _module():
    spec = importlib.util.spec_from_file_location("e5_asr_tool_pass_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def m():
    return _module()


def _row(row_id, split, notes, consumed="no", carrier="slurp TRAIN Fold A 1080"):
    return (f"| 2026-09-29 | {row_id} | bounded-discovery-probe | E5-0 | Whisper | {carrier} | discovery | {split} | "
            f"{consumed} | 1080 | 3085 | 5.0 | inherited | docs/readiness/x | {notes} |\n")


DRAFT = "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) 2026-09-29."
SIGNED = "REGISTERED BEFORE CONTACT (root countersigned 2026-09-30T00:00:00Z by root) 2026-09-29."


# ---------------------------------------------------------------------------- pure predicates


def test_ledger_row_state_reads_presence_uniqueness_consumed_and_countersignature(m):
    split = "0" * 64
    text = "# ledger\n\n" + HEADER + _row("R-DRAFT", split, DRAFT) + _row("R-SIGNED", split, SIGNED) \
        + _row("R-TWICE", split, SIGNED) + _row("R-TWICE", split, SIGNED) + _row("R-USED", split, SIGNED, "yes")
    assert m.ledger_row_state(text, "R-DRAFT") == {
        "row_id": "R-DRAFT", "present": True, "unique": True, "consumed": "no", "countersigned": False}
    assert m.ledger_row_state(text, "R-SIGNED")["countersigned"] is True
    assert m.ledger_row_state(text, "R-TWICE")["unique"] is False
    assert m.ledger_row_state(text, "R-USED")["consumed"] == "yes"
    assert m.ledger_row_state(text, "R-ABSENT")["present"] is False


def test_flight_and_serving_detection_match_the_serving_library(m, tmp_path):
    prepare = "11 python -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply --repo-root /w"
    campaign = "12 python -B -m speech_aware_evidence_acquisition.core.flight.cli campaign --repo-root /r"
    driver = "13 bash /x/scripts/flights/batch/batch_driver.sh"
    lease = "14 python -m speech_aware_evidence_acquisition.core.flight.lease_cli --stage worker"
    server = "15 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8080 -m m.gguf"
    sidecar = "16 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8081 -m m.gguf"
    assert m.flight_alive(tmp_path, [prepare, sidecar]) == []
    assert len(m.flight_alive(tmp_path, [campaign, driver, lease])) == 3
    (tmp_path / "locks").mkdir()
    (tmp_path / "locks" / "flight.lock").write_text("{}")
    assert m.flight_alive(tmp_path, []) == ["flight.lock present"]
    assert m.serving_up([sidecar]) == [] and len(m.serving_up([server, sidecar])) == 1


def test_lock_entry_must_pin_the_runtime_checkpoint(m):
    good = {"models": [{"name": m.LOCK_ENTRY, "status": "COMPLETE",
                        "source": {"files": [{"sha256": m.CHECKPOINT_SHA256}]}}]}
    assert m.lock_entry_state(good) == []
    assert m.lock_entry_state({"models": []})
    bad = json.loads(json.dumps(good))
    bad["models"][0]["source"]["files"][0]["sha256"] = "f" * 64
    assert m.lock_entry_state(bad)


def test_the_gpu_decode_is_the_dev1000_recovery_decode_byte_for_byte(m):
    recovery = json.loads((REPO / "docs/readiness/2026-09-12-slurp-whisper-recovery-v1/preparation-protocol.json")
                          .read_text(encoding="utf-8"))
    assert m.GPU_DECODING == recovery["decoding"]
    cpu = {k: v for k, v in m.CPU_DECODING.items()
           if k not in ("device", "fp16", "batch_size", "cpu_workers", "cpu_thread_limits")}
    assert cpu == {k: v for k, v in recovery["decoding"].items()
                   if k not in ("device", "fp16", "batch_size", "cpu_workers")}
    from speech_aware_evidence_acquisition.core.speech_observation_backend import _validate_protocol

    for decoding in (m.GPU_DECODING, m.CPU_DECODING):
        _validate_protocol(decoding)


@pytest.mark.parametrize("roster", ["fold-a", "fold-b"])
@pytest.mark.parametrize("device", ["gpu", "cpu"])
def test_registration_is_deterministic_and_matches_the_committed_files(m, roster, device):
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    committed = REPO / m.reg_paths(roster, device)["protocol"]
    sources_sha = json.loads(committed.read_text(encoding="utf-8"))["sources"]["sha256"]
    built = m.build_registration(roster, device, sources_sha)
    assert built == m.build_registration(roster, device, sources_sha)
    assert built["protocol_bytes"] == committed.read_bytes()
    assert built["plan_bytes"] == (REPO / m.reg_paths(roster, device)["plan"]).read_bytes()
    plan = ExecutionPlan(**built["plan"]).validate()
    assert plan.protocol_hash == hashlib.sha256(built["protocol_bytes"]).hexdigest()
    assert plan.run_id == m.ROSTERS[roster]["row_id"] and plan.split_identity_hash == m.ROSTERS[roster][
        "split_identity_hash"]
    assert built["protocol"]["output_relpath"].startswith(f"prepared/{plan.run_id}/{plan.attempt_id}/")
    assert "initial_prompt" not in built["protocol"]["decoding"] and "prompt" not in built["protocol"]["decoding"]


# ---------------------------------------------------------------------------- a synthetic checkout


def _git(repo, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env)


class World:
    """A temporary checkout + data root carrying one fake 3-row roster registered as fold-a."""

    def __init__(self, m, root: Path, notes=SIGNED):
        from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

        self.m, self.root = m, root
        self.repo, self.data = root / "repo", root / "data"
        self.repo.mkdir()
        self.data.mkdir()
        ids = ["slurp:train:000001:a", "slurp:train:000002:b", "slurp:train:000003:c"]
        self.split = split_identity_hash(prefixed("slurp", ids))
        items, packets = [], []
        for n, sid in enumerate(ids):
            audio, packet = hashlib.sha256(f"a{n}".encode()).hexdigest(), hashlib.sha256(f"p{n}".encode()).hexdigest()
            items.append({"sample_id": sid, "packet_id": f"slurp/train/{n:06d}/x", "audio_sha256": audio,
                          "media_relpath": f"datasets/slurp/slurp_real/x{n}.flac", "audio_seconds": 1.5 + n,
                          "sample_rate_hz": 16000})
            packets.append({"packet_id": f"slurp/train/{n:06d}/x", "packet_sha256": packet, "audio_sha256": audio})
        dataset = {"split_identity_hash": self.split, "count": 3, "items": items}
        (self.repo / "configs/dataset").mkdir(parents=True)
        (self.repo / "configs/dataset/fake.json").write_text(json.dumps(dataset), encoding="utf-8")
        promotion = self.root / "promotion.json"
        promotion.write_text(json.dumps({"packets": packets}), encoding="utf-8")
        m.PROMOTION = {"path": str(promotion), "sha256": hashlib.sha256(promotion.read_bytes()).hexdigest()}
        m.ROSTERS = {"fold-a": {**m.ROSTERS["fold-a"], "dataset": "configs/dataset/fake.json",
                                "split_identity_hash": self.split, "rows": 3, "planned_audio_seconds": 8}}
        m.REPO_ROOT = self.repo
        inv = REPO / m.CHECKPOINT_RECEIPT["relpath"]
        (self.repo / inv.relative_to(REPO)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inv, self.repo / inv.relative_to(REPO))
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs/exposure-ledger.md").write_text(
            "# Exposure ledger\n\n" + HEADER + _row(m.UMBRELLA_ROW, self.split, notes), encoding="utf-8")
        self.lock = self.root / "lock.json"
        self.lock.write_text(json.dumps({"models": [{"name": m.LOCK_ENTRY, "status": "COMPLETE", "source": {
            "files": [{"sha256": m.CHECKPOINT_SHA256}]}}]}), encoding="utf-8")
        self.sources = m.roster_sources("fold-a", data_root=self.data)
        for device in ("gpu", "cpu"):
            m.write_registration("fold-a", device, self.sources["sha256"])
        _git(self.repo, "init", "-q")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "fake")

    def evaluate(self, device="gpu", processes=()):
        return self.m.evaluate("fold-a", device=device, data_root=self.data, lock_path=self.lock,
                               processes=list(processes))


SERVER = "15 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8080 -m m.gguf"


def test_sources_round_trip_and_write_once(m, tmp_path):
    w = World(m, tmp_path)
    assert w.sources["rows"] == 3 and w.sources["exists"] is False and w.sources["written"] is False
    written = m.roster_sources("fold-a", data_root=w.data, write=True)
    assert written["written"] is True and written["sha256"] == w.sources["sha256"]
    again = m.roster_sources("fold-a", data_root=w.data, write=True)
    assert again["written"] is False and again["exists"] is True
    doc = json.loads((w.data / written["relpath"]).read_text(encoding="utf-8"))
    assert doc["contact_class"] == "model-free" and doc["output"]["split_identity_hash"] == w.split
    assert set(doc["output"]["source_bindings"]["slurp:train:000001:a"]) == {
        "packet_id", "packet_sha256", "source_audio_relpath", "source_audio_sha256", "source_audio_duration_seconds"}


def test_a_promotion_that_disagrees_on_the_audio_is_refused(m, tmp_path):
    w = World(m, tmp_path)
    doc = json.loads(Path(m.PROMOTION["path"]).read_text())
    doc["packets"][0]["audio_sha256"] = "0" * 64
    Path(m.PROMOTION["path"]).write_text(json.dumps(doc))
    m.PROMOTION["sha256"] = hashlib.sha256(Path(m.PROMOTION["path"]).read_bytes()).hexdigest()
    with pytest.raises(m.ToolPassError, match="disagree on the audio"):
        m.roster_sources("fold-a", data_root=w.data)


def test_a_countersigned_idle_clean_world_is_admissible(m, tmp_path):
    w = World(m, tmp_path)
    verdict = w.evaluate()
    assert verdict["admissible"] is True, verdict["refusals"]
    assert verdict["sealed_catalog"] is None


def test_every_refusal(m, tmp_path):
    w = World(m, tmp_path, notes=DRAFT)
    assert any("no root countersignature" in r for r in w.evaluate()["refusals"])
    ledger = w.repo / "docs/exposure-ledger.md"
    ledger.write_text(ledger.read_text().replace(DRAFT, SIGNED))
    _git(w.repo, "commit", "-qam", "sign")
    assert w.evaluate()["admissible"] is True
    # serving up: GPU refused, CPU admitted
    gpu = w.evaluate(processes=[SERVER])
    assert not gpu["admissible"] and any("serving session is up" in r for r in gpu["refusals"])
    assert w.evaluate(device="cpu", processes=[SERVER])["admissible"] is True
    # a generation flight
    assert any("generation flight" in r for r in w.evaluate(
        processes=["9 python -m speech_aware_evidence_acquisition.core.flight.cli worker --x"])["refusals"])
    (w.data / "locks").mkdir()
    (w.data / "locks/flight.lock").write_text("{}")
    assert "flight.lock present" in w.evaluate()["refusals"]
    (w.data / "locks/flight.lock").unlink()
    # a dirty checkout
    (w.repo / "stray.txt").write_text("x")
    assert "the checkout is not clean" in w.evaluate()["refusals"]
    (w.repo / "stray.txt").unlink()
    # the lock without the entry
    w.lock.write_text(json.dumps({"models": []}))
    assert any(m.LOCK_ENTRY in r for r in w.evaluate()["refusals"])
    w.lock.write_text(json.dumps({"models": [{"name": m.LOCK_ENTRY, "status": "COMPLETE", "source": {
        "files": [{"sha256": m.CHECKPOINT_SHA256}]}}]}))
    # a prior unsealed attempt
    attempts = w.data / "attempts" / m.ROSTERS["fold-a"]["row_id"]
    attempts.mkdir(parents=True)
    (attempts / "attempt-x.json").write_text("{}")
    assert any("already exists without a sealed catalog" in r for r in w.evaluate()["refusals"])
    # a sealed catalog of the other device
    shutil.rmtree(w.data / "attempts")
    cpu_catalog = w.data / m.build_registration("fold-a", "cpu", w.sources["sha256"])["protocol"]["output_relpath"]
    cpu_catalog.parent.mkdir(parents=True)
    cpu_catalog.write_text("{}")
    assert any("one pass per roster" in r for r in w.evaluate()["refusals"])


def test_a_drifted_registration_is_refused(m, tmp_path):
    w = World(m, tmp_path)
    path = w.repo / m.reg_paths("fold-a", "gpu")["protocol"]
    path.write_bytes(path.read_bytes().replace(b'"beam_size": 5', b'"beam_size": 4'))
    _git(w.repo, "commit", "-qam", "drift")
    assert "registration files do not re-derive byte-identically" in w.evaluate()["refusals"]


# ---------------------------------------------------------------------------- run: receipt shape, publication, idempotency


def _fake_runner(m, w, calls):
    def runner(config, *, source_root, data_root):
        calls.append(config)
        protocol = json.loads(Path(config["protocol"]["path"]).read_bytes())
        catalog = {"schema": "saea-prepared-speech-observation-catalog-v1", "catalog_id": protocol["catalog_id"],
                   "use_split_identity_hash": config["plan"]["split_identity_hash"], "observations": []}
        path = Path(data_root) / protocol["output_relpath"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(catalog), encoding="utf-8")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"schema": "saea-speech-observation-preparation-receipt-v1", "status": "SEALED",
                "catalog_relpath": protocol["output_relpath"], "catalog_sha256": sha,
                "logical_speech_tool_contacts": 3, "actual_speech_audio_seconds": 7.5, "elapsed_seconds": 1.0}
    return runner


def test_run_publishes_a_byte_identical_catalog_and_a_text_free_receipt(m, tmp_path):
    w = World(m, tmp_path)
    calls = []
    receipt = m.run("fold-a", device="gpu", data_root=w.data, lock_path=w.lock, runner=_fake_runner(m, w, calls),
                    processes=[])
    assert len(calls) == 1
    config = calls[0]
    assert config["ledger_row"]["row_id"] == m.ROSTERS["fold-a"]["row_id"]
    assert config["ledger_row"]["relpath"] == "docs/exposure-ledger.md"
    assert config["plan"]["attempt_id"] == "attempt-slurp-asr-tool-pass-fold-a-gpu-v1"
    published = w.data / m.PUBLISH_ROOT / "fold-a"
    assert (published / "catalog.json").read_bytes() == (w.data / receipt["catalog"]["producer_relpath"]).read_bytes()
    stored = json.loads((published / "receipt.json").read_text())
    assert stored == receipt
    for key in ("model", "decoding", "decoding_config_sha256", "environment", "source_inventory", "split_identity_hash",
                "utterance_count", "wall_seconds", "device_mode", "study_head", "catalog", "execution_plan",
                "runtime_inventory", "exposure_ledger_sha256_at_run", "umbrella_lock_sha256_at_run"):
        assert key in receipt, key
    assert receipt["model"]["checkpoint_sha256"] == m.CHECKPOINT_SHA256
    assert receipt["core_contacts"] == 0 and receipt["utterance_count"] == 3 and receipt["device_mode"] == "gpu"
    assert receipt["source_inventory"]["sha256"] == w.sources["sha256"]
    assert "transcript" not in json.dumps(receipt).replace("hashes and counts only; no utterance text, transcript", "")
    # the source inventory was written once, at run time
    assert (w.data / m.ROSTERS["fold-a"]["sources_relpath"]).exists()
    # idempotent: a second run is the warm path, no new producer call
    again = m.run("fold-a", device="gpu", data_root=w.data, lock_path=w.lock, runner=_fake_runner(m, w, calls),
                    processes=[])
    assert len(calls) == 1 and again["cache"] == "warm" and again["new_contacts"] == 0


def test_run_refuses_before_any_contact(m, tmp_path):
    w = World(m, tmp_path, notes=DRAFT)
    calls = []
    with pytest.raises(m.ToolPassError, match="^REFUSED"):
        m.run("fold-a", device="gpu", data_root=w.data, lock_path=w.lock, runner=_fake_runner(m, w, calls),
                    processes=[])
    assert calls == [] and not (w.data / m.PUBLISH_ROOT).exists()


def test_the_cli_check_exit_codes(m, tmp_path):
    w = World(m, tmp_path, notes=DRAFT)
    rc = m.main(["check", "--roster", "fold-a", "--data-root", str(w.data), "--lock", str(w.lock)])
    assert rc == 3
