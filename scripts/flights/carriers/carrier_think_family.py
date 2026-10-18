"""Shared identities of the carrier base package on the Thinking core (P3.2 packets, P3.3 all-off + direct baselines; owner rulings 302 A, 306 A, 333 B).

One module, imported by the derive, writer, mint, reader, chain, dry-run and test scripts, so no id is spelled twice. Model-free. It follows the NX-T R2b
package form (``nxt_r2b_family``) and re-uses what R2b re-used: ``thinking_system_family`` (the Thinking model fragment, serving session, packet root and the
registered thinking knobs), ``tfrl_family`` (the GPU-plan margin) and ``recovery`` (the generic rec1 mechanism). Their files are not changed.

WHAT THE PACKAGE IS. For each carrier in the owner's order (A2T, E21, E22; rulings 302 A and 306 A) three HELD cells, all derived from the registered Instruct
all-off cells by config alone:

  ``smoke``   the four-row form smoke (the carrier's own four-row prefix), flown first and signed off by the machine sign-off (owner ruling 314 A)
  ``alloff``  the consumption module with every component off (compiles to the carrier's direct layer) on the Thinking core
  ``direct``  the carrier's DIRECT baseline: the ``direct-only`` phase program of the shared controller (same harness, same executor, same FlightRuntime)

``alloff`` and ``direct`` are REQUEST-IDENTICAL by construction (the Instruct byte proof ``module_equivalence_proof --at a2t0 / e210 / e220`` carries over: the
Thinking derivation changes the same leaves in both), so the pair is the carrier's in-chain A/A on the Thinking core: it measures the carrier's own null on the
Thinking base and the baseline numbers (the A2T paper column; Earnings Whisper-normalised WER beside saea-scoring-v1) in one back-to-back chain.

THE THINKING KNOBS are the SLURP lock's, unchanged: reasoning budget 3,072 + answer reserve 1,024 = completion cap 4,096, ``drop-reasoning-v1``, the model
fragment ``q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`` (np4 x 24,576), the resident session of the SLURP lock
(swap target ``think-budget-np4``) -- the carrier cells ride the SAME session as the SLURP lock, so no new serving geometry, fragment or Windows task exists.

GPU CEILING. A direct-only unit is ONE contact; ``cost = units x seconds per contact / 4 slots / 3600``, with the SLURP-measured seconds per contact
(``carrier_think_spec.json``: A2T 59 s, Earnings 64 s), registered ``ceil_0.1( expected x 1.3 )``. A bound, never a target.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLIGHTS = HERE.parent
for _dir in (HERE, FLIGHTS / "direct", FLIGHTS / "tfrl", FLIGHTS / "lib", FLIGHTS / "nx"):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import thinking_system_family as tsf  # noqa: E402
import tfrl_family as tf  # noqa: E402
import recovery as rcv  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
SPEC_PATH = HERE / "carrier_think_spec.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
if SPEC.get("schema") != "saea-carrier-think-spec-v1":
    raise ValueError("carrier_think_spec.json has the wrong schema")

DATE = SPEC["date"]
SLUG = SPEC["slug"]                                              # carrier-base-thinking
PKG_NAME = f"{SLUG}-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
SHORT = "carrierthink"
DECISION_ID = f"{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
LEDGER_MARK = "## Cell CARRIER-BASE-THINKING: the carrier all-off + direct baselines on the Thinking core (A2T, E21, E22; smoke, all-off, direct each)"
OWNER_RULINGS = ("owner rulings 302 A, 306 A, 307 and 333 B (carriers A2T -> E21 -> E22, all-off and direct baselines only, Thinking core, after NX-T R3 and before the "
                 "decoding column), the P3.2 / P3.3 rows of the P3 programme (owner decision 299 A) and the coordinator brief of 2026-10-18")
CARRIERS = tuple(SPEC["order"])
CARRIER_SPEC = {c: SPEC["carriers"][c] for c in CARRIERS}
KINDS = ("smoke", "alloff", "direct")
ARM_KINDS = ("alloff", "direct")

# ---- the Thinking core: the SLURP lock's, re-used unchanged ---------------------------------------------------------------------
THINK_MODEL, THINK_SESSION, THINK_SWAP_TARGET = tsf.THINK_MODEL, tsf.THINK_SESSION, tsf.THINK_SWAP_TARGET
THINK_PACKET_ROOT = tsf.THINK_PACKET_ROOT
THINKING_KNOBS = json.loads(json.dumps(tsf.THINKING_KNOBS))
BUDGET, RESERVE, CAP = tsf.THINK_BUDGET_TOKENS, tsf.THINK_ANSWER_RESERVE_TOKENS, tsf.THINK_MAX_TOKENS
SLOT_TOKENS, SLOTS = tsf.SLOT_TOKENS, tsf.THINK_SLOTS
PROMPT_LIMIT = tsf.PROMPT_LIMIT_THINKING                         # 17,406
FALLBACK_PER_CONTACT = 1                                         # core.reasoning_knobs.FALLBACK_CONTACTS_PER_ROW_DIRECT: one answer-only re-ask per contact
CONTACTS_PER_UNIT = 1                                            # the direct-only program makes exactly one contact per unit
SMOKE_GPU_HOURS = float(SPEC["cost"]["smoke_gpu_hours"])
GPU_MARGIN, GPU_ROUND_H = float(SPEC["cost"]["margin"]), float(SPEC["cost"]["round_h"])
COST = SPEC["cost"]
FIT_OBS = SPEC["fit_observations"]

# ---- packet roots and receipts (P3.2) -------------------------------------------------------------------------------------------
ZERO = "0" * 64
#: ONE Thinking packet root, extended ADDITIVELY per roster under its own promotion receipt (the Fold B / DEV / test-sample precedent). The window packets of
#: Earnings are promoted into it too: a packet id is the audio digest, so the root needs no carrier directory.
A2T_PROMOTION_NAME = CARRIER_SPEC["a2t"]["packets"]["promotion_receipt_name"]
A2T_PROMOTION_RECEIPT = f"{THINK_PACKET_ROOT}/{A2T_PROMOTION_NAME}"


#: The Thinking-identity window-inventory pins (carrier_think_windows.py pins --write): a data file beside the family, NOT inside a readiness package.
WINDOW_PINS_PATH = HERE / "carrier_think_window_pins_v1.json"


def packets_spec(carrier: str) -> dict:
    return CARRIER_SPEC[carrier]["packets"]


def window_artifact_relpath(carrier: str, smoke: bool) -> str:
    """The Thinking window-packets artifact (the Earnings 'promotion receipt'): ``analysis/<encode run>/window-feature-packets.json``."""

    p = packets_spec(carrier)
    return f"analysis/{p['smoke_encode_run_id' if smoke else 'encode_run_id']}/window-feature-packets.json"


def window_inventory_relpath(carrier: str, smoke: bool) -> str:
    """The Thinking-identity window inventory (full roster, or the four-window smoke subset): both artifacts of ONE model-free run id."""

    p = packets_spec(carrier)
    return f"analysis/{p['inventory_run_id']}/" + ("window-inventory-smoke-4.json" if smoke else "window-inventory.json")


# ---- cells --------------------------------------------------------------------------------------------------------------------
def cell_key(carrier: str, kind: str) -> str:
    return f"{carrier}-{kind}"


def _stem(carrier: str, kind: str) -> str:
    return f"carrier-think-base-{carrier}-" + ("smoke-4" if kind == "smoke" else kind)


def source_experiment_name(carrier: str, kind: str) -> str:
    return CARRIER_SPEC[carrier]["source"]["smoke" if kind == "smoke" else "arm"]


def source_experiment(carrier: str, kind: str, root: Path = REPO_ROOT) -> dict:
    return json.loads((Path(root) / "configs" / "experiment" / f"{source_experiment_name(carrier, kind)}.json").read_text(encoding="utf-8"))


def source_baseline_name(carrier: str, kind: str, root: Path = REPO_ROOT) -> str:
    return source_experiment(carrier, kind, root)["cells"][0]["baseline_fragment"]


def ceil_tenth(value: float) -> float:
    return round(math.ceil(round(value / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def seconds_per_contact(carrier: str) -> float:
    return float(COST["seconds_per_contact"][carrier])


def source_units(carrier: str, kind: str, root: Path = REPO_ROOT) -> int:
    """Contacts of the direct-only program = the source cell's registered generation calls (rows for A2T, windows for Earnings)."""

    return int(source_experiment(carrier, kind, root)["family_budget"]["generation_calls_cap"])


def expected_gpu_hours(carrier: str, units: int) -> float:
    """units x contacts per unit x seconds per contact / slots / 3600 (unrounded)."""

    return units * CONTACTS_PER_UNIT * seconds_per_contact(carrier) / float(COST["slots"]) / 3600.0


def planned_gpu_hours(carrier: str, units: int) -> float:
    return ceil_tenth(expected_gpu_hours(carrier, units) * GPU_MARGIN)


def envelope_gpu_hours(carrier: str, units: int) -> float:
    """The upper envelope: every contact reasons to the budget (Instruct latency + decode increment x budget)."""

    s = float(COST["instruct_contact_seconds"][carrier]) + float(COST["envelope_decode_s_per_token"]) * int(COST["envelope_budget_tokens"])
    return units * CONTACTS_PER_UNIT * s / float(COST["slots"]) / 3600.0


def envelope_seconds(carrier: str) -> float:
    return float(COST["instruct_contact_seconds"][carrier]) + float(COST["envelope_decode_s_per_token"]) * int(COST["envelope_budget_tokens"])


def has_fit(carrier: str) -> bool:
    return CARRIER_SPEC[carrier]["fit"] is not None


def fit_contact_cap(carrier: str, units: int) -> int:
    f = CARRIER_SPEC[carrier]["fit"]
    return 0 if f is None else int(f["base"]) + int(f["per_row"]) * units


# ---- recovery (rec1; generic mechanism, data-driven exactly as NX-T R2b) --------------------------------------------------------------
REC = rcv.REC
PREDECESSOR_SNAPSHOT = {cell_key(c, k): f"{PACKAGE}/predecessor-snapshot-{c}-{k}-rec1-v1.json" for c in CARRIERS for k in KINDS}
RECOVERY_INPUT = {cell_key(c, k): f"{PACKAGE}/recovery-input-{c}-{k}-v1.json" for c in CARRIERS for k in KINDS}
RECOVERY_INPUT_KEYS = ("recovered_at", "ledger_title", "agent", "reason", "root_cause", "fix", "decision")


def build_recovery(inputs: dict, snap: dict) -> dict:
    missing = [k for k in RECOVERY_INPUT_KEYS if not inputs.get(k)]
    if missing:
        raise ValueError(f"the recovery input misses {missing}")
    fit = snap.get("fit") or {}
    calls, audio = snap["actual_calls"], snap["actual_audio_seconds"]
    return {
        "recovery_index": 1, "recovered_at": inputs["recovered_at"], "ledger_title": inputs["ledger_title"], "agent": inputs["agent"],
        "registered_at_utc": None, "base_commit": None, "worktree": None, "branch": None,
        "predecessor_attempt_id": snap["attempt_id"], "predecessor_fit_run_id": fit.get("run_id"), "predecessor_fit_attempt_id": fit.get("attempt_id"),
        "fit_predecessor_phrase": (f"no attempt record was opened for it, its prepared directory holds {fit.get('prepared_request_fit_envelopes', 0):,} "
                                   "request-fit envelopes preserved unread on the data root"),
        "predecessor_state": (f"{snap['state']}; {calls:,} calls / {audio:.2f} speech-seconds realised per its attempt record (reserved "
                              f"{snap['reserved_calls']:,} / {snap['reserved_audio_seconds']:,.0f}); preserved unread."),
        "predecessors": [rcv.predecessor_from_snapshot(snap)],
        "reason": inputs["reason"], "root_cause": inputs["root_cause"],
        "amendment": (f"RECOVERY {inputs['recovered_at']} (the cell's single one; {inputs['decision']}). The generation budget is run-cumulative across the "
                      f"attempts of the run id, so the rec1 plan carries the original plan plus the failed attempt's recorded spend ({calls:,} calls, {audio:g} "
                      "speech-seconds, read from the attempt record into the predecessor snapshot). The FIT cap is structural and unchanged. A cell with a FIT "
                      "identity takes the rec1 marker on its FIT run and attempt ids too; the generation run id is unchanged. The registered GPU-hour ceiling does not change."),
        "fix": inputs["fix"],
        "unchanged": "Unchanged: every other cell of the package (sealed, signed off, not re-flown) and every registered knob, roster, prompt, geometry, cap and GPU-hour ceiling.",
        "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
        "fit_cap_rule": "The FIT cap is structural: units x program contacts x endpoints per contact.",
    }


def _load_recoveries(root: Path = REPO_ROOT) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, rel in RECOVERY_INPUT.items():
        path = Path(root) / rel
        if path.is_file():
            out[key] = build_recovery(json.loads(path.read_text(encoding="utf-8")), rcv.load_snapshot(Path(root) / PREDECESSOR_SNAPSHOT[key]))
    return out


RECOVERIES: dict[str, dict] = _load_recoveries()
for _rec in RECOVERIES.values():
    rcv.validate_recovery(_rec)


def recovery(key: str) -> dict | None:
    return RECOVERIES.get(key)


def rec_suffix(key: str) -> str:
    return rcv.rec_suffix(RECOVERIES, key)


def predecessor_spend(key: str) -> tuple[int, float]:
    return rcv.predecessor_spend(RECOVERIES, key)


def cumulative_budget(key: str, original_calls: int, original_audio: float) -> tuple[int, int]:
    return rcv.cumulative_budget(RECOVERIES, key, original_calls, original_audio)


def _spec(carrier: str, kind: str) -> dict:
    key = cell_key(carrier, kind)
    stem = _stem(carrier, kind)
    up = stem.upper()
    rec, rec_up = rec_suffix(key), rec_suffix(key).upper()
    units = source_units(carrier, kind)
    c = CARRIER_SPEC[carrier]
    return {
        "key": key, "carrier": carrier, "kind": kind, "units": units, "label": c["label"],
        "role": {"smoke": f"{c['label']} four-row form smoke on the Thinking core",
                 "alloff": f"{c['label']} consumption-module ALL-OFF arm on the Thinking core",
                 "direct": f"{c['label']} DIRECT baseline (the direct-only phase program) on the Thinking core"}[kind],
        "gpu_hours": SMOKE_GPU_HOURS if kind == "smoke" else planned_gpu_hours(carrier, units),
        "cell": f"{stem}-v1", "baseline": f"{stem}-baseline-v1",
        "run": f"SAEA-{up}-V1",
        "fit_run": f"SAEA-{up}-FIT{rec_up}-V1" if has_fit(carrier) else None,
        "attempt": f"attempt-{stem}-generation{rec}-v1",
        "fit_attempt": f"attempt-{stem}-fit{rec}-v1" if has_fit(carrier) else None,
        "model": THINK_MODEL, "session": THINK_SESSION,
        "prefix": f"{carrier}-{kind}-",
        # An ARM flies as a campaign cell. A smoke flies as an `engineering` driver step (A2T: no campaign plan) or, in the E35 form of the Earnings
        # carriers, as a one-call `cell` step with its own campaign plan.
        "campaign": (None if kind == "smoke" and c["batch"]["smoke_form"] == "engineering" else f"configs/campaign/{stem}-v1.json"),
        "source_experiment": source_experiment_name(carrier, kind),
    }


CELLS = {cell_key(c, k): _spec(c, k) for c in CARRIERS for k in KINDS}
ALL_KEYS = tuple(CELLS)
ARM_KEYS = tuple(k for k in ALL_KEYS if CELLS[k]["kind"] in ARM_KINDS)


def cells_of(carrier: str) -> list[dict]:
    return [CELLS[cell_key(carrier, k)] for k in KINDS]


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(key: str, plan_kind: str) -> str:
    return rcv.plan_file_name(CELLS[key]["prefix"], plan_kind, key in RECOVERIES)


def superseded_plan_file_names(key: str) -> list[str]:
    return rcv.superseded_plan_file_names(CELLS[key]["prefix"], key in RECOVERIES)


def plan_kinds(key: str) -> tuple[str, ...]:
    return ("generation", "fit") if CELLS[key]["fit_run"] else ("generation",)


def read_run_id(carrier: str) -> str:
    return f"SAEA-CARRIER-THINK-BASE-{carrier.upper()}-READ-V1"


def analysis_root(carrier: str) -> str:
    return f"analysis/{read_run_id(carrier)}"


def signoff_conditions_path(carrier: str) -> str:
    return f"{PACKAGE}/signoff-conditions-{carrier}-v1.json"


def signoff_marker(carrier: str) -> str:
    return f"/home/chao/{SHORT}-{carrier}-decode-signoff.marker"


SMOKE_TABLE_SCHEMA = "saea-carrier-think-base-smoke-v1"
READ_SCHEMA = "saea-carrier-think-base-read-v1"


# ---- ids, budgets, text --------------------------------------------------------------------------------------------------------------
def generation_calls_original(key: str) -> int:
    s = CELLS[key]
    return s["units"] * (CONTACTS_PER_UNIT + FALLBACK_PER_CONTACT)


def generation_calls(key: str) -> int:
    return cumulative_budget(key, generation_calls_original(key), 0)[0]


def audio_cap_original(key: str, root: Path = REPO_ROOT) -> int:
    s = CELLS[key]
    base = int(source_experiment(s["carrier"], s["kind"], root)["family_budget"]["repeated_speech_audio_seconds_cap"])
    return base * (CONTACTS_PER_UNIT + FALLBACK_PER_CONTACT)


def audio_cap(key: str, root: Path = REPO_ROOT) -> int:
    return cumulative_budget(key, 0, audio_cap_original(key, root))[1]


def fit_cap(key: str) -> int:
    s = CELLS[key]
    return fit_contact_cap(s["carrier"], s["units"]) if s["fit_run"] else 0


def eligible_run_ids() -> list[str]:
    """Each cell's generation run id then its first-registration FIT run id (A2T only), in chain order; a recovered cell's rec1 FIT run id is appended last."""

    out: list[str] = []
    for key in ALL_KEYS:
        s, rec = CELLS[key], recovery(key)
        out.append(s["run"])
        if s["fit_run"]:
            out.append(rec["predecessor_fit_run_id"] if rec else s["fit_run"])
    out += [CELLS[k]["fit_run"] for k in ALL_KEYS if recovery(k) and CELLS[k]["fit_run"]]
    return out


def eligible_attempt_ids() -> list[str]:
    out: list[str] = []
    for key in ALL_KEYS:
        s, rec = CELLS[key], recovery(key)
        if rec:
            out += [rec["predecessor_attempt_id"]] + ([rec["predecessor_fit_attempt_id"]] if s["fit_run"] else [])
        out.append(s["attempt"])
        if s["fit_run"]:
            out.append(s["fit_attempt"])
    return out


def think_model_text() -> str:
    return ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, "
            f"c{SLOTS * SLOT_TOKENS} np{SLOTS} x {SLOT_TOKENS:,} max{CAP} (reasoning budget {BUDGET}, answer reserve {RESERVE}, cap {CAP}), q8_0 KV, "
            f"--reasoning-format deepseek, reasoning_context_policy {tsf.REASONING_CONTEXT_POLICY} (model fragment {THINK_MODEL}); its own promoted speech "
            "packets; direct-only phase program, one contact per unit; no tool authority")


def fit_proof(carrier: str) -> dict:
    """The context-fit proof of one carrier at the Thinking cap, from the sealed Instruct prompt observations (numbers only)."""

    obs = FIT_OBS[carrier]
    prompt_max = int(obs["prompt_tokens_max"])
    checks = {"observed_prompt_max_fits": prompt_max <= PROMPT_LIMIT, "slot_holds_prompt_plus_cap": prompt_max + CAP <= SLOT_TOKENS}
    return {"carrier": carrier, "slot_tokens": SLOT_TOKENS, "slots": SLOTS, "reserve_tokens": tsf.RESERVE_TOKENS, "special_reserve_tokens": tsf.SPECIAL_RESERVE,
            "completion_cap": CAP, "prompt_limit_tokens": PROMPT_LIMIT, "observed": json.loads(json.dumps(obs)),
            "observed_headroom_tokens": PROMPT_LIMIT - prompt_max, "limit_basis": FIT_OBS["limit_basis"], "checks": checks, "ok": all(checks.values())}


def signoff_conditions(carrier: str) -> dict:
    """The machine sign-off conditions (owner ruling 314 A; ``scripts/flights/batch/smoke_signoff.py``) of one carrier's smoke."""

    return {
        "schema": "saea-smoke-signoff-conditions-v1",
        "_note": (f"Carrier base ({carrier}) machine sign-off conditions (owner ruling 314 A), emitted by carrier_think_derive_cells.py from carrier_think_spec.json. The smoke's job is to "
                  "show that the single contact of every unit closes within the cap (no cap hit, no empty answer, no length finish, no reasoning marker in delivered content), that the "
                  "measured seconds per contact is no more than 1.3x the registered figure, and that no contact is unattributed. The node is a think node: no no-think node exists."),
        "package": PKG_NAME, "ruling": "owner ruling 314 A of 2026-10-14", "table_schema": SMOKE_TABLE_SCHEMA,
        "table_relpath": f"{analysis_root(carrier)}/smoke-decode-cost.json",
        "expected_arms": ["smoke"], "min_contacts_per_node": 1, "no_think_nodes": {},
        "no_think_max": {"contacts_with_reasoning_chars": 0, "marker_in_content": 0, "reasoning_chars_mean": 0},
        "every_node_max": {"cap_hits": 0, "empty_content": 0, "finish_reason_length": 0, "marker_in_content": 0},
        "arm_mix": {"max_ratio": 1.3, "measured_key": "seconds_per_contact_measured", "registered_key": "seconds_per_contact_registered"},
        "extras": [{"id": "unattributed-contacts", "path": "unattributed_contacts", "op": "==", "value": 0}],
    }


def roster_label(carrier: str, kind: str) -> str:
    """The exposure row's 'speech carrier + split' column. The gate (contracts.gate_exposure) requires it to name EXACTLY ONE carrier lock key, so the lock key leads."""

    c = CARRIER_SPEC[carrier]
    units = CELLS[cell_key(carrier, kind)]["units"]
    split = {"a2t": "A2T-PAIRED-400-V1", "e21": "discovery", "e22": "dev"}[carrier]
    return f"{c['carrier_lock_key']} {split} {'four-' + c['unit_kind'][:-1] + ' smoke' if kind == 'smoke' else 'full roster'} {units}"


__all__ = [name for name in globals() if not name.startswith("_")]
