"""Carrier base on the Thinking core (P3.2 packets, P3.3 all-off + direct): model-free, synthetic and tmp-rooted.

The generators are checked against the registered Instruct source cells in a temporary overlay root (nothing is written to the repository, no ledger row is appended to
the real ledger, nothing is flipped or flown). Shell scripts are syntax-checked and the queue hook is exercised with fake commands.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "carriers", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "flights" / "batch", REPO / "scripts" / "analysis", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import carrier_think_derive_cells as dc  # noqa: E402
import carrier_think_family as fam  # noqa: E402
import carrier_think_packets as a2tp  # noqa: E402
import carrier_think_packets_write_registration as pw  # noqa: E402
import carrier_think_queue as cq  # noqa: E402
import carrier_think_read as reader  # noqa: E402
import carrier_think_windows as win  # noqa: E402
import carrier_think_write_registration as wr  # noqa: E402
import smoke_signoff  # noqa: E402

CP = REPO / "scripts" / "flights" / "carriers"
HAVE_BASH = shutil.which("bash") is not None


@pytest.fixture(scope="module")
def overlay(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("overlay")
    need = {"experiment": set(), "baseline": set(), "dataset": set(), "model": {fam.THINK_MODEL}}
    for carrier in fam.CARRIERS:
        for kind in ("smoke", "arm"):
            exp = json.loads((REPO / "configs" / "experiment" / f"{fam.CARRIER_SPEC[carrier]['source'][kind]}.json").read_text(encoding="utf-8"))
            cell = exp["cells"][0]
            need["experiment"].add(fam.CARRIER_SPEC[carrier]["source"][kind])
            need["baseline"].add(cell["baseline_fragment"])
            need["dataset"].add(cell["dataset_fragment"])
            need["model"].add(cell["model_fragment"])
    for kind, names in need.items():
        for name in names:
            dest = root / "configs" / kind / f"{name}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / "configs" / kind / f"{name}.json", dest)
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "exposure-ledger.md").write_text("# ledger\n", encoding="utf-8")
    dc.derive(write=True, root=root)
    return root


def js(root: Path, rel: str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def test_ids_are_unique_and_ordered():
    assert fam.CARRIERS == ("a2t", "e21", "e22")
    assert len(fam.ALL_KEYS) == 9
    for field in ("cell", "baseline", "run", "attempt"):
        assert len({fam.CELLS[k][field] for k in fam.ALL_KEYS}) == 9
    assert [k for k in fam.ALL_KEYS if fam.CELLS[k]["fit_run"]] == ["a2t-smoke", "a2t-alloff", "a2t-direct"]
    assert fam.eligible_run_ids()[0] == fam.CELLS["a2t-smoke"]["run"] and len(fam.eligible_run_ids()) == 12


def test_cost_arithmetic():
    assert fam.planned_gpu_hours("a2t", 400) == 2.2
    assert fam.planned_gpu_hours("e21", 1593) == 9.3
    assert fam.planned_gpu_hours("e22", 451) == 2.7
    assert fam.CELLS["a2t-smoke"]["gpu_hours"] == 0.5
    assert fam.envelope_gpu_hours("e21", 1593) > fam.expected_gpu_hours("e21", 1593)


def test_fit_proofs_hold_at_the_thinking_cap():
    for c in fam.CARRIERS:
        assert fam.fit_proof(c)["ok"]
    assert fam.PROMPT_LIMIT == 17406 and fam.CAP == 4096


def test_signoff_conditions_validate():
    for c in fam.CARRIERS:
        smoke_signoff.validate_conditions(fam.signoff_conditions(c))


def test_derive_moves_only_the_declared_leaves_and_the_arms_are_request_identical(overlay):
    proof = dc.prove(overlay)
    for c in fam.CARRIERS:
        assert all(dc._starts(k, dc.IDENTITY_ONLY) for k in proof[c]["alloff_vs_direct_moved_identity_leaves"])
        assert "decoding_params.thinking_budget_tokens" in proof[c]["alloff_vs_instruct_source"]["moved"]


def test_baselines_carry_the_thinking_geometry_and_zero_sentinels(overlay):
    a2t = js(overlay, "configs/baseline/carrier-think-base-a2t-alloff-baseline-v1.json")
    assert a2t["serving_geometry"] == {"max_tokens": 4096, "slot_tokens": 24576, "slots": 4}
    assert a2t["speech_packet_promotion_receipt"] == fam.A2T_PROMOTION_RECEIPT
    assert a2t["speech_packet_promotion_receipt_sha256"] == fam.ZERO
    assert a2t["live_phase_fit"]["contact_cap"] == 1201
    e21 = js(overlay, "configs/baseline/carrier-think-base-e21-direct-baseline-v1.json")
    assert e21["serving_geometry"]["max_tokens"] == 4096 and e21["ojw_workflow_timeout_seconds"] == 43200
    assert e21["prepared_window_feature_packets"]["sha256"] == fam.ZERO
    assert "live_phase_fit" not in e21


def test_experiments_use_the_lock_session_and_a_fallback_ceiling(overlay):
    for k in fam.ALL_KEYS:
        d = js(overlay, f"configs/experiment/{fam.CELLS[k]['cell']}.json")
        assert d["cells"][0]["model_fragment"] == fam.THINK_MODEL and d["service_session"] == fam.THINK_SESSION
        assert d["execution_plan"]["planned_model_calls"] == 2 * fam.CELLS[k]["units"]
        assert d["cells"][0]["readiness"]["state"] == "held"
        assert ("consumption_module_declaration" in d) == (fam.CELLS[k]["kind"] != "direct")


def test_writer_builds_the_package_and_the_rows_name_one_carrier_lock_key(overlay):
    res = wr.write_package(overlay, "abc1234", "2026-10-18T12:00:00+00:00", derive=False, append_ledger=True)
    assert res["rows"] == 15
    text = (overlay / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    for key in ("audio2tool", "earnings21-original", "earnings22-original"):
        assert key in text
    texts = js(overlay, f"{fam.PACKAGE}/countersign-row-texts-v1.json")["rows"]
    assert len(texts) == 15 and sum("-READ-" in r for r in texts) == 3
    draft = js(overlay, f"{fam.PACKAGE}/root-admission-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["eligible_run_ids"] == fam.eligible_run_ids()
    assert wr.write_package(overlay, "abc1234", "2026-10-18T12:00:00+00:00", derive=False, append_ledger=True).get("ledger_appended") is False


def test_queue_steps_and_ids(tmp_path):
    a = cq.queue_steps("a2t", "smoke")
    assert a[0]["kind"] == "engineering" and a[0]["campaign_plan"] is None and a[0]["smoke_cell"] == a[0]["cell"]
    arms = cq.queue_steps("e21", "arms")
    assert [s["cell"] for s in arms] == [fam.CELLS["e21-alloff"]["cell"], fam.CELLS["e21-direct"]["cell"]]
    assert arms[0]["expected_rows"] == 44 and arms[0]["fit_run_id"] is None
    assert cq.queue_steps("e22", "smoke")[0]["kind"] == "cell"
    assert len(cq.close_ids("a2t")) == 6 and len(cq.close_ids("e21")) == 3
    assert cq.sealed_state("a2t-smoke", str(tmp_path)) == "none"


def _trace(path: Path, contacts):
    rows = []
    for n, c in enumerate(contacts, 1):
        p = f"flight-{n:04d}"
        rows += [{"channel": "MODEL_REQUEST", "record_id": f"{p}/request", "payload": {"payload": {"decoding_params": {"max_tokens": 4096, "thinking_budget_tokens": 3072}}}},
                 {"channel": "MODEL_RESPONSE", "record_id": f"{p}/response", "payload": {"text": c.get("text", "answer")}},
                 {"channel": "MODEL_WIRE_RESPONSE", "record_id": f"{p}/wire-response", "payload": {"finish_reason": "stop"}},
                 {"channel": "COST", "record_id": f"{p}/cost", "payload": {"completion_tokens": c.get("ct", 900), "finish_reason": "stop", "forced_close": False,
                                                                           "latency_seconds": c.get("lat", 50.0), "prompt_tokens": 3000, "reasoning_chars": 100}}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_smoke_reader_and_machine_signoff(tmp_path):
    key = fam.cell_key("a2t", "smoke")
    s = fam.CELLS[key]
    d = tmp_path / "runs" / s["run"] / s["attempt"]
    d.mkdir(parents=True)
    (d / f"{s['run']}.run-manifest.json").write_text(json.dumps({"status": "COMPLETED"}), encoding="utf-8")
    _trace(d / f"{s['run']}.trace.jsonl", [{} for _ in range(4)])
    table = reader.smoke_stage("a2t", tmp_path)
    assert table["arms"]["smoke"]["core"]["contacts"] == 4
    cond = fam.signoff_conditions("a2t")
    assert all(x["ok"] for x in smoke_signoff.evaluate(cond, table))
    _trace(d / f"{s['run']}.trace.jsonl", [{"ct": 4096}, {}, {}, {}])
    bad = smoke_signoff.evaluate(cond, reader.smoke_stage("a2t", tmp_path))
    assert any(not x["ok"] and "cap_hits" in x["id"] for x in bad)
    _trace(d / f"{s['run']}.trace.jsonl", [{"text": "<think>x"}, {}, {}, {}])
    assert any(not x["ok"] and "marker" in x["id"] for x in smoke_signoff.evaluate(cond, reader.smoke_stage("a2t", tmp_path)))
    _trace(d / f"{s['run']}.trace.jsonl", [{"lat": 200.0}] * 4)
    assert any(not x["ok"] and "arm-mix" in x["id"] for x in smoke_signoff.evaluate(cond, reader.smoke_stage("a2t", tmp_path)))


def test_window_rekey_changes_only_identity_and_reproduces_its_own_bytes():
    def row(n):
        return {"request_key": f"s#w000{n}", "payload_sha256": "p" * 63 + str(n), "encoding_key_sha256": "x", "source_provenance": {"sample_id": "s", "sha256": f"{n:064x}", "audio_seconds": 90.0}}
    out = {"schema": "saea-window-feature-inventory-v1", "state": "inputs-verified-features-not-materialized", "encoder_identity": {"a": "1"}, "request_count": 4, "unique_audio_count": 4,
           "batches": [{"name": "B", "requests": [row(n) for n in range(1, 5)]}],
           "encoding_inputs": [{"audio_sha256": f"{n:064x}", "audio_byte_count": 10, "encoding_key_sha256": "x", "requests": [{"batch": "B", "request_key": f"s#w000{n}"}]} for n in range(1, 5)]}
    own = {"a": "1"}
    for r in out["batches"][0]["requests"]:
        r["encoding_key_sha256"] = win.digest({"encoder_identity": own, "audio_sha256": r["source_provenance"]["sha256"]})
    for e in out["encoding_inputs"]:
        e["encoding_key_sha256"] = win.digest({"encoder_identity": own, "audio_sha256": e["audio_sha256"]})
    src, _raw, sha = win.artifact_of(out)
    assert win.rekey(src, own)[2] == sha
    new = {"a": "2"}
    art, _r, sha2 = win.rekey(src, new)
    assert sha2 != sha and art["output"]["encoder_identity"] == new
    assert art["output"]["batches"][0]["requests"][0]["payload_sha256"] == out["batches"][0]["requests"][0]["payload_sha256"]
    sub = win.subset(art, sample_ids=["s"], per_call_limit=2, batch_name="SMOKE")[0]
    assert sub["output"]["request_count"] == 2 and sub["output"]["batches"][0]["name"] == "SMOKE"


def test_the_committed_window_pins_cover_both_earnings_carriers():
    pins = json.loads(fam.WINDOW_PINS_PATH.read_text(encoding="utf-8"))
    for c in ("e21", "e22"):
        assert len(pins[c]["full"]["sha256"]) == 64 and pins[c]["smoke"]["unit_count"] == 4
        assert pins[c]["full"]["relpath"] == fam.window_inventory_relpath(c, False)
    assert pins["identity"]["decoder_gguf_sha256"].startswith("afdaeff6")


def test_packets_rows(tmp_path):
    specs = pw.pass_specs()
    assert len(specs) == 7 and [s["carrier"] for s in specs] == ["a2t", "e21", "e21", "e21", "e22", "e22", "e22"]
    assert all(("audio2tool" in s["carrier_text"] or "earnings2" in s["carrier_text"]) for s in specs)
    assert specs[0]["contacts"] == 400 and specs[3]["contacts"] == 1593


def test_a2t_driver_helpers(tmp_path):
    assert a2tp.packet_id({"sample_id": "tier1_direct:000069"}) == "tier1_direct/000069"
    with pytest.raises(SystemExit):
        a2tp.packet_id({"sample_id": "../x:1"})
    roster = a2tp.load_roster()
    assert len(a2tp.stage_items(roster, "smoke")) == 4 and len(a2tp.stage_items(roster, "full")) == 400
    ledger = tmp_path / "l.md"
    cols = "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n" + "| " + " | ".join("---" for _ in range(15)) + " |\n"
    row = f"| 2026-10-18 | {a2tp.RUN_ID} | bounded-discovery-probe | s | m | audio2tool x | discovery | h | no | 400 | 2761 | 0.5 | i | a | {{}} |\n"
    ledger.write_text(cols + row.format("DRAFT at x"), encoding="utf-8")
    assert a2tp.ledger_state(ledger, expected_calls=400, expected_seconds=2761)["countersigned"] is False
    ledger.write_text(cols + row.format("REGISTERED BEFORE CONTACT (root countersigned t)"), encoding="utf-8")
    assert a2tp.ledger_state(ledger, expected_calls=400, expected_seconds=2761)["countersigned"] is True


@pytest.mark.skipif(not HAVE_BASH, reason="bash required")
@pytest.mark.parametrize("script", ["batch_chain_carrier_think.sh", "batch_chain_carrier_packets.sh", "carrier_think_flip.sh", "carrier_think_repin_cell.sh", "carrier_think_read.sh",
                                    "carrier_think_packets_gpu.sh", "../batch/queue/queue_carriers_after.sh", "../batch/queue/chain_carrierthink.sh", "../batch/queue/chain_carrierpackets.sh"])
def test_shell_scripts_parse(script):
    assert subprocess.run(["bash", "-n", str(CP / script)], capture_output=True, text=True).returncode == 0


def _hook(tmp_path, *, pred_rc="0", flip_log, flip_rc=0, opt="--register", packets_cmd="true"):
    main = tmp_path / "main"
    main.mkdir()
    for c in (["git", "init", "-q"], ["git", "config", "user.name", "t"], ["git", "config", "user.email", "t@t"], ["git", "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(c, cwd=main, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=main, capture_output=True, text=True).stdout.strip()
    chain = tmp_path / "pred.out"
    chain.write_text(f"CHAIN_X_EXIT rc={pred_rc} 2026-10-21T10:00:00Z\n", encoding="utf-8")
    log, fc, out = tmp_path / "flip.out", tmp_path / "fc.txt", tmp_path / "q.out"
    log.write_text(flip_log, encoding="utf-8")
    fc.write_text(head + "\n", encoding="utf-8")
    env = dict(os.environ, CARRIER_HOOK_MAIN=str(main), CARRIER_HOOK_OUT=str(out), CARRIER_HOOK_POLL_SECONDS="1", CARRIER_HOOK_MAX_WAIT_SECONDS="3", CARRIER_HOOK_SETTLE_SECONDS="0",
               CARRIER_HOOK_DATA=str(tmp_path / "data"), CARRIER_HOOK_FLIP_LOG=str(log), CARRIER_HOOK_FLIGHT_COMMIT=str(fc), CARRIER_HOOK_ALIVE_CMD="true",
               CARRIER_HOOK_PACKETS_CMD=packets_cmd, CARRIER_HOOK_REGISTER_CMD="true", CARRIER_HOOK_FLIP_CMD=f"exit {flip_rc}", CARRIER_HOOK_START_CMD=f"echo started > {tmp_path}/started")
    r = subprocess.run(["bash", str(CP / ".." / "batch" / "queue" / "queue_carriers_after.sh"), str(chain), "CHAIN_X_EXIT", "2026-10-21T08:00:00Z", opt], env=env, capture_output=True, text=True)
    return r.returncode, (tmp_path / "started").exists(), out.read_text(encoding="utf-8") if out.exists() else ""


GOOD = "== gate\n" + "check: PASS\n" * 9 + "repin exit 1 (1 = its internal check refused the dirty tree, expected)\nFLIP_CHAIN_DONE x\n"


@pytest.mark.skipif(not HAVE_BASH or not shutil.which("git"), reason="bash and git required")
def test_hook_launches_and_ignores_the_informational_refused_line(tmp_path):
    rc, started, log = _hook(tmp_path, flip_log=GOOD)
    assert (rc, started) == (0, True), log


@pytest.mark.skipif(not HAVE_BASH or not shutil.which("git"), reason="bash and git required")
@pytest.mark.parametrize("log,why", [(GOOD + "REFUSED: gate\n", "refused"), ("== gate\ncheck: PASS\nFLIP_CHAIN_DONE x\n", "too few passes"), (GOOD.replace("FLIP_CHAIN_DONE", "x"), "not done")])
def test_hook_refuses_a_bad_flip(tmp_path, log, why):
    rc, started, _ = _hook(tmp_path, flip_log=log)
    assert (rc, started) == (9, False), why


@pytest.mark.skipif(not HAVE_BASH or not shutil.which("git"), reason="bash and git required")
def test_hook_refuses_after_a_failed_predecessor_and_when_packets_are_missing(tmp_path):
    assert _hook(tmp_path / "a", pred_rc="1", flip_log=GOOD)[:2] == (9, False) if (tmp_path / "a").mkdir() is None else True
    (tmp_path / "b").mkdir()
    assert _hook(tmp_path / "b", flip_log=GOOD, packets_cmd="false")[:2] == (9, False)
