"""Render the P-EMB-4R flight receipt README from the landed evidence.

Every number in the generated tables comes from the flight receipt / state on
the data root, so the README can never drift from what actually happened. The
narrative prose lives here, in this script, and is reviewed with it.

NOTHING here reads a result: it consumes only counts, hashes, latencies,
dims, session records, budget totals and CONSTRUCTION metadata
(candidate-set SIZES, mean top-1 retrieval cosines -- the gold-free winner
proxy the registration itself mandates be disclosed). No gold is loaded and
no accuracy/recall/vote quantity is computed or printed.

Usage: render_readme.py <archive-dir> <attempt-id> <study-commit>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    dest = Path(sys.argv[1])
    attempt = sys.argv[2]
    commit = sys.argv[3]

    receipt = json.loads((dest / "flight-receipt.json").read_text(encoding="utf-8"))
    vec = json.loads((dest / "vector-manifest-summary.json").read_text(encoding="utf-8"))
    rplan_path = dest / "retrieval-plan-summary.json"
    rplan = json.loads(rplan_path.read_text(encoding="utf-8")) if rplan_path.is_file() else None
    cdec_path = dest / "c-decode-summary.json"
    cdec = json.loads(cdec_path.read_text(encoding="utf-8")) if cdec_path.is_file() else None

    gpu = receipt["gpu_accounting"]
    dur = receipt["durable_actual"]
    ceil = receipt["registered_ceilings"]
    sweeps = receipt.get("sweeps") or {}
    gates = receipt["gates"]
    det = receipt["determinism_samples"]

    out: list[str] = []
    w = out.append

    w("# P-EMB-4R multi-model kNN retrieval routing — FLIGHT RECEIPT (2026-08-20)")
    w("")
    w("Registered probe `SAEA-PROBE-pemb4r-4100`, execution profile `bounded-discovery-probe`.")
    w("Preregistration: `docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md`. Machinery:")
    w("`rails.probes.pemb4r_flight` (landed at `a407d03`), flown at study commit")
    w(f"`{commit[:7]}`, tree clean throughout.")
    w("")
    if receipt.get("c_decode_blocked"):
        w("**All seven embedding arms and the retrieval plan flew. C-DECODE did NOT** — it was refused")
        w("fail-closed because it would have breached the registered metered-audio ceiling. Zero")
        w("frozen-core contacts were made. See §6 for the arithmetic and the proof.")
        w("")
    w("**This flight produced no read.** Every vector and the retrieval plan")
    w("were written to the data root for the separately-registered one-shot read mission")
    w("(`analysis.pemb4r_read`) and were never scored here. Everything in this directory is")
    w("operational, structural, or CONSTRUCTION metadata: contact counts, dims, per-vector sha256,")
    w("latencies, session pins, budget totals, candidate-set SIZES and the gold-free winner proxy the")
    w("registration itself requires be disclosed. No accuracy, no recall, no vote, no gold comparison.")
    w("The frozen 60's devel gold was never loaded — machine-checked at every entry point by")
    w("`rails.probes.pemb4r_flight.assert_never_accesses_frozen_60_gold`, an AST guard scoped to")
    w("`.scenario`/`.action`/`.entities`/`.intent`.")
    w("")
    w("| Field | Value |")
    w("|---|---|")
    w("| Run id | `SAEA-PROBE-pemb4r-4100` |")
    w(f"| Attempt | `{attempt}` |")
    w(f"| Status | `{receipt['status']}` |")
    w(f"| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb4r-4100/{attempt}` |")
    w(f"| Study commit | `{commit[:7]}`, tree clean at takeoff and at landing |")
    w(f"| Config hash | `{receipt['config_hash']}` |")
    w(f"| Protocol hash | `{receipt['protocol_hash']}` (= this run's config hash) |")
    w(f"| Binding config sha256 | `{receipt['binding_config_sha256']}` (pinned `a193f634…ce17a`) |")
    w(f"| Bank manifest sha256 | `{receipt['bank']['sha256']}` (pinned `5f488951…f5b112`) |")
    w(f"| Split identity | `{receipt['split_identity_hash']}` |")
    w(f"| Umbrella lock sha256 | `{receipt['umbrella_lock_sha256']}` |")
    w(f"| Attempts | **one**; {dur['calls']} contacts spent |")
    w("")

    w("## 1. Spend against the registered ceilings")
    w("")
    w("| Basis | Actual | Registered ceiling | Headroom |")
    w("|---|---|---|---|")
    w(f"| Model/tool calls | **{dur['calls']}** | {ceil['model_calls']} | {ceil['model_calls'] - dur['calls']} |")
    w(f"| Metered speech audio-seconds | **{dur['audio_seconds']:.3f}** | {ceil['speech_audio_seconds']} | {ceil['speech_audio_seconds'] - dur['audio_seconds']:.3f} |")
    w(f"| GPU-h — per-call measured-equivalent | **{gpu['measured_equivalent_hours']:.4f}** | {ceil['gpu_hours']} | {ceil['gpu_hours'] - gpu['measured_equivalent_hours']:.4f} |")
    w(f"| GPU-h — GPU-active occupancy | **{gpu['gpu_active_hours']:.4f}** | {ceil['gpu_hours']} | {ceil['gpu_hours'] - gpu['gpu_active_hours']:.4f} |")
    w(f"| GPU-h — server-alive wall | {gpu['server_alive_wall_hours']:.4f} | *recorded, never gates* | — |")
    w("")
    w("The GPU accounting basis is the P-CORR-F section-8 pre-read adjudication ruling, carried")
    w("forward verbatim by `rails.probes.pemb4r_flight.assert_gpu_hours_within_ceiling`: the ceiling is")
    w("checked against **per-call measured-equivalent** and **GPU-active occupancy**; server-alive wall")
    w("is recorded but never gates. That ruling's own FORWARD RULE was applied literally — see §6.")
    w("")

    w("## 2. Arms flown")
    w("")
    w("Each model embeds its own 900-row key bank exactly ONCE; the two arms of a model share it.")
    w("")
    w("| Arm | Model | Query | Dim | Bank contacts | Query contacts | Mean latency (s) |")
    w("|---|---|---|---|---|---|---|")
    arm_meta = {
        "a-lco3": ("lco3", "audio"), "t-lco3": ("lco3", "T0 transcript"),
        "a-lco7": ("lco7", "audio"), "t-lco7": ("lco7", "T0 transcript"),
        "a-glap": ("glap", "audio"), "t-glap": ("glap", "T0 transcript"),
        "t-qw": ("qw", "T0 transcript"),
    }
    seen_bank: set[str] = set()
    for arm_id in ("a-lco3", "t-lco3", "a-lco7", "t-lco7", "a-glap", "t-glap", "t-qw"):
        model, kind = arm_meta[arm_id]
        st = receipt["arm_status_final"].get(arm_id, {})
        if not st.get("complete"):
            w(f"| {arm_id.upper()} | {model} | {kind} | — | — | — | **NOT FLOWN** — {st.get('dropped_reason')} |")
            continue
        bank_block = sweeps.get(f"bank:{model}", {})
        bank_cell = str(bank_block.get("contacts_flown", "—")) if model not in seen_bank else "(shared)"
        seen_bank.add(model)
        arm_block = sweeps.get(arm_id, {})
        w(
            f"| {arm_id.upper()} | {model} | {kind} | {st.get('dims')} | {bank_cell} | "
            f"{arm_block.get('contacts_flown', '—')} | {arm_block.get('mean_latency_seconds', '—')} |"
        )
    w("")
    w("Per-model bank vector sets (sha256-verified on every load):")
    w("")
    w("| Model | Bank vectors | Dim | Distinct vector sha256 |")
    w("|---|---|---|---|")
    for model, block in sorted(vec["bank_vectors_by_model"].items()):
        if not block.get("present"):
            w(f"| {model} | — | — | **absent** |")
            continue
        w(f"| {model} | {block['count']} | {block['dims']} | {block['distinct_vector_sha256']} |")
    w("")

    w("## 3. Gates")
    w("")
    w("| Gate | Outcome |")
    w("|---|---|")
    a = gates.get("a_lco7_server_sanity")
    if a:
        w(f"| (a) LCO-7B server sanity | `{a['status']}` — measured dim **{a['measured_dim']}**, GGUF-declared {a['declared_dim']}, agree = {a['declared_matches_measured']} |")
    else:
        w("| (a) LCO-7B server sanity | not recorded |")
    b = gates.get("b_glap_import_and_audio_sanity")
    if b:
        w(f"| (b) GLAP import + audio-path sanity | `{b['status']}` — {b['detail']} |")
    for model in ("lco3", "lco7"):
        c = gates.get(f"c_pooling_differ_{model}")
        if c:
            w(
                f"| (c) POOLING-DIFFER [{model}] | `pooling_override_present = {c['pooling_override_present']}` "
                f"— 2 boots, 2 contacts, dim {c['dims']}; scope tag applies to {list(c['scope']['scoped_arm_ids'])} |"
            )
        else:
            w(f"| (c) POOLING-DIFFER [{model}] | not run (model dropped) |")
    d = gates.get("d_encode_only")
    w(f"| (d) encode-only machine check | `{d['status']}` over {len(d['checked_modules'])} pinned modules, including `rails.probes.pemb4r_flight` |")
    e = gates.get("e_cascade_source")
    w(f"| (e) cascade/T0 source | `{e['status']}` — {e['transcript_count']}/60 T0 transcripts, registry sha256 `{e['registry_sha256'][:16]}…` |")
    w("")

    w("## 4. Determinism samples (sha256 equality only)")
    w("")
    w("| Session | Kind | Dim | Byte-identical | Contacts |")
    w("|---|---|---|---|---|")
    for key in ("lco3", "lco7", "qw"):
        block = det.get(key)
        if not block:
            w(f"| {key} | — | — | *not run* | 0 |")
            continue
        w(f"| {block['server_session']} | {block['kind']} | {block.get('dims')} | **{block['byte_identical']}** | {block['contacts']} |")
    cd = det.get("c_decode")
    if cd:
        w(f"| q4km-core (C-DECODE resend, `-np {cd['parallelism_np']}`) | generation | — | **{cd['byte_identical']}** | {cd['contacts']} |")
    w("")
    w("Every jitter vector pair is persisted on the data root (`<model>-jitter-vectors.json` in the run")
    w("dir) so `analysis.pemb4r_read` can derive the measured repeat-δ the registration's own")
    w("argmax-stability statement needs. This flight evaluated no tolerance. Two facts the read must")
    w("carry: GLAP is in-process with no server session at all, so registration section 6's")
    w("per-server-session rule does not reach it — **GLAP has no measured repeat-δ, and `t-glap` is the")
    w("winner arm**; and the planned C-DECODE identical-prompt resend at `-np 4` was never flown,")
    w("because C-DECODE was never flown (§6), so this flight contributes **no** generation-side")
    w("determinism evidence and the P-CORR-F resend-divergence finding stands unre-tested here.")
    w("")

    if rplan:
        w("## 5. Retrieval plan (flight-side, gold-free)")
        w("")
        w(f"- Written to `$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb4r-4100/retrieval-plan/retrieval_plan.json`")
        w(f"- **sha256 `{rplan['retrieval_plan_sha256']}`**, schema `{rplan['schema']}`, K primary {rplan['k_primary']}")
        w(f"- **Winner arm: `{rplan['winner_arm_id']}`** — selected by the GOLD-FREE proxy the machinery")
        w(f"  documents as a judgment call: *{rplan['winner_selection_rule']}*")
        w("")
        w("Retrieval is a PURE function of already-flown vectors plus the bank's own TRAIN-split VALUE")
        w("metadata, so it runs flight-side by the machinery's own design (registration section 3 item 8).")
        w("`analysis.pemb4r_read.verify_retrieval_plan_document` independently RE-DERIVES the same")
        w("retrieval from the same vectors and compares it field-by-field rather than trusting this")
        w("artifact.")
        w("")
        w("Per-sample candidate-set SIZE distribution — construction metadata (how many DISTINCT labels")
        w("each retrieved set carries), never which label is right:")
        w("")
        w("| Arm | mean top-1 cosine | K=5 sizes | K=3 sizes |")
        w("|---|---|---|---|")
        for arm_id, block in sorted(rplan["per_arm"].items()):
            k5 = ", ".join(f"{k}→{v}" for k, v in sorted(block["candidate_set_size_distribution_k5"].items()))
            k3 = ", ".join(f"{k}→{v}" for k, v in sorted(block["candidate_set_size_distribution_k3"].items()))
            mark = " **(winner)**" if arm_id == rplan["winner_arm_id"] else ""
            w(f"| {arm_id}{mark} | {block['mean_top1_cosine']:.6f} | {k5} | {k3} |")
        w("")

    blocked = receipt.get("c_decode_blocked")
    if blocked:
        arith = blocked["arithmetic"]
        w("## 6. C-DECODE — NOT FLOWN, registered ceiling would have been breached")
        w("")
        w(f"**Status: `{blocked['status']}`. Contacts made: {blocked['contacts_made']}.**")
        w("")
        w("The seven embedding arms and the retrieval plan are complete. C-DECODE is not, and was")
        w("refused fail-closed rather than flown over the registered metered-audio ceiling.")
        w("")
        w("**Why the transcript modality does not help.** `rails.core_client.FrozenCoreClient.complete()`")
        w("resolves `audio_seconds` from the payload BINDING for the named sample — including on the")
        w("text-only branch (`audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]`) —")
        w("and `core.model.adapter` charges exactly that per request, before the request leaves the")
        w("process. A C-DECODE pass over the frozen 60 therefore meters a **full corpus audio pass on")
        w("either modality**: the request is still, honestly, about that bound sample's `speech_ref`.")
        w("Neither the coordinator-ratified budget-forced text fallback nor the winner arm happening to")
        w("be a text arm (it is, `t-glap`) can reduce it.")
        w("")
        w("| Quantity | Seconds |")
        w("|---|---|")
        w(f"| Already spent (7 arms + 12 gate contacts) | {arith['already_spent_audio_seconds']:.3f} |")
        w(f"| C-DECODE, 60 requests | {arith['c_decode_60_requests_seconds']:.3f} |")
        w(f"| C-DECODE determinism resend, 1 request | {arith['c_decode_determinism_resend_seconds']:.3f} |")
        w(f"| **Total if C-DECODE flew** | **{arith['total_if_c_decode_flies']:.3f}** |")
        w(f"| Registered ceiling | {arith['registered_ceiling_seconds']} |")
        w(f"| **Over by** | **{arith['over_by_seconds']:.3f}** |")
        w(f"| Headroom remaining | {arith['headroom_remaining_seconds']:.3f} |")
        w(f"| Requests affordable | {arith['requests_affordable_of_60']} of 60 |")
        w("")
        w(f"**Registration gap.** {blocked['registration_gap']}")
        w("")
        w(f"**Action taken.** {blocked['action_taken']}")
        w("")
        w(f"**What would unblock it.** {blocked['what_would_unblock']}")
        w("")
        w("**Proof that zero frozen-core contacts were made:**")
        w("")
        for line in blocked["evidence_of_zero_contacts"]:
            w(f"- {line}")
        w("- `session-q4km-core.server.log` carries **0** `POST /v1/chat/completions` lines across its")
        w("  49 lines: the session loaded the pinned q4km GGUF set, sat idle, and was torn down.")
        w("")
        w("The q4km session was spawned before the refusal surfaced (the refusal comes from")
        w("`FrozenCoreClient.__init__`, which runs after `start_session`), so its receipt and log are")
        w("landed here in full. It is torn down, its port is free, and the GPU is idle — see")
        w("`postflight.log`.")
        w("")
        cg = receipt.get("c_decode_gate") or {}
        w("**The P-CORR-F §8 forward rule was applied and is worth recording on its own.** The FULL")
        w("frozen-core gate — `assert_model_touch_allowed(plan, full_hash=True)`, including the q4km")
        w("GGUF attestation — ran BEFORE any server was spawned, together with the payload binding and")
        w(f"the whole `load_split(\"devel\")` media pass. It completed in **{cg.get('seconds')} s**")
        w("(`ran_before_spawn: true`), and the q4km session that followed loaded in **3.8 s** and was")
        w("resident for ~2 s. P-CORR-F's own attempt paid 959 s of cold GGUF hashing *while the server")
        w("held VRAM idle*, which is what put its Measure A over ceiling. Ordering the work this way")
        w("kept server-alive wall for the core session to seconds instead of minutes.")
        w("")
        w("### 6a. Coordinator pre-contact ruling, recorded verbatim")
        w("")
        ruling = receipt.get("coordinator_pre_contact_ruling") or {}
        w(f"Recorded in this attempt's flight state at `{ruling.get('recorded_at')}`, when zero C-DECODE")
        w("generation contacts existed. The `cdecode` stage refuses fail-closed unless this block is")
        w("present and matches verbatim, so its presence is the flight-side record that the ruling")
        w("preceded the contacts.")
        w("")
        w("> " + str(ruling.get("text", "")))
        w("")
        w("The condition it keys on (`budget_forced`) **did not fire**: the gold-free winner proxy chose")
        w("`t-glap`, a text arm, so the intended modality was already the transcript one. A separate,")
        w("unconditional fact is recorded in `c_decode_modality_decision`: the consumed P-FEW FS-NONE")
        w("comparator is **audio**-modality, so any transcript-modality C-DECODE mixes the")
        w("retrieval-shrunk label space with an observation change — independent of `budget_forced`.")
        w("")

    if cdec:
        dec = receipt.get("c_decode_modality_decision", {})
        w("## 6. C-DECODE")
        w("")
        w(f"- {cdec['n_rows']} closed-set generation calls on the pinned q4km core, plus one identical-prompt resend.")
        w(f"- Winner arm `{cdec['winner_arm_id']}`; presented modality **`{cdec['c_decode_query_kind']}`**.")
        w(f"- Generation server parallelism: **`-np {receipt['c_decode']['core_client_cost'] and dec.get('parallelism_np', '')}`** — see the table below.")
        w("")
        w("| Quantity | Value |")
        w("|---|---|")
        w(f"| Rows | {cdec['n_rows']} |")
        w(f"| Candidate-set sizes | {', '.join(f'{k}→{v}' for k, v in sorted(cdec['candidate_set_size_distribution'].items()))} |")
        w(f"| Response length (chars) | min {cdec['response_char_length']['min']}, mean {cdec['response_char_length']['mean']:.1f}, max {cdec['response_char_length']['max']} |")
        w(f"| Closed-set mapping outcomes (format health, never accuracy) | {', '.join(f'{k}→{v}' for k, v in sorted(cdec['closed_set_mapping_outcome_counts'].items()))} |")
        w(f"| Mapping fallbacks | {cdec['closed_set_mapping_fallback_count']} |")
        w("")
        if dec:
            w(f"**Modality decision.** {dec['reason']}")
            w("")

    corrections = receipt.get("corrections") or []
    if corrections:
        w("## 6b. Corrections to the landed evidence")
        w("")
        w("A defect that had already written a false number into this receipt, repaired in place and")
        w("disclosed rather than left standing. The launcher source archived under `launcher/` carries")
        w("the fix; its module docstring additionally lists two further defects the (unexercised)")
        w("C-DECODE path still has, so a follow-on fixes them deliberately.")
        w("")
        for c in corrections:
            w(f"- **`{c['field']}`**: recorded `{c['recorded_value']}` → corrected to `{c['corrected_value']}`.")
            w(f"  {c['reason']}")
            w(f"  *Scope:* {c['scope']}")
        w("")

    w("## 7. Documented deviations")
    w("")
    w("1. **POOLING-DIFFER ran sequentially, not concurrently.** The machinery's own")
    w("   `run_pooling_differ_gate` takes a LIVE `last_client` and a LIVE `mean_client` at the same")
    w("   instant — two resident llama-server sessions over the same weights. For LCO-7B that is")
    w("   2 × ~12.6 GB against 23.1 GB of free VRAM on this host: an OOM, not a gate. The archived")
    w("   P-EMB-3M precedent was carried instead (boot `last`, embed the synthetic clip, tear down,")
    w("   boot `mean`, embed the SAME clip, tear down, byte-compare the persisted vectors). The")
    w("   computation is identical — `last_vector.values == mean_vector.values`, the machinery's own")
    w("   one-line verdict — and the machinery was not modified; only the concurrency was.")
    w("2. **`planned_speech_audio_seconds` was declared at the registered ceiling (700), not at the")
    w("   machinery's own 547 default.** 547 is exactly three metered passes and admits no fourth;")
    w("   whether C-DECODE needed a fourth was not knowable until the gold-free winner resolved, and")
    w("   the launcher must not pre-empt that. Declaring the registered cell let the decision be made")
    w("   on measured remaining budget. It never authorized more than the registration already did —")
    w("   and in the event the ceiling refused anyway (§6).")
    w("3. **LCO-7B's `expected_dim` came from its GGUF header, read offline.** `EmbeddingClient`")
    w("   enforces a strict dim equality and LCO-7B has no proven-dim probe in this codebase, so the")
    w("   header's `qwen2vl.embedding_length = 3584` was read model-free in preflight purely to")
    w("   construct the client. The gate's verdict still came from the LIVE sanity embed's returned")
    w("   vector, which measured **3584** — agreement recorded in gate (a).")
    w("4. **No process-wide `SAEA_FEAT_CACHE_DIR`.** This flight runs two different audio encoders over")
    w("   the same 60 clips, so each session was handed its own `LLAMA_MTMD_FEAT_CACHE_DIR`")
    w("   (`slurp-lco3b`, warm from P-EMB-3M; `slurp-lco7b`, cold; `slurp-q4km` for the core). The")
    w("   launcher refuses to start if a process-wide override is set.")
    w("")
    w("## 8. Files")
    w("")
    w("| File | What it is |")
    w("|---|---|")
    w("| `README.md` | this receipt |")
    w("| `launcher/` | every file that produced the flight (env, identity, GLAP loader, launcher, wrappers, gates) |")
    w("| `preflight-pytest.log` | the full suite, run once on a quiet machine before any contact |")
    w("| `preflight-bank-binding-check.log` | bank double-derivation + binding/registry/ledger pins, model-free |")
    w("| `preflight-syntax-check.log` | instrument syntax + dry composition, zero contact |")
    w("| `preflight-rehearsal.log` | full launcher rehearsal against a TEMP root and MOCK clients |")
    w("| `takeoff-state.log` | takeoff environment probe (GPU, caches, ports, absent run dir, assets) |")
    w("| `flight.log` | operational flight log (contact index, kind, id, latency, dim, response LENGTH) |")
    w("| `flight-receipt.json` | the launcher's own receipt |")
    w("| `flight-state.json` | the staged flight state every stage extended |")
    w("| `execution-plan.json` | the validated `ExecutionPlan` |")
    w("| `config-values.json` | the hashed config-values bundle |")
    w("| `attempt-state.json` | the durable attempt record |")
    w("| `session-*.receipt.json` / `session-*.server.log` | every llama-server session's pins and own log |")
    w("| `vector-manifest-summary.json` | per-model bank and per-arm query manifests: counts, dims, per-vector sha256 — never a component |")
    w("| `retrieval-plan-summary.json` | the plan's hash, winner, rule and candidate-set SIZE distributions |")
    w("| `c-decode-summary.json` | C-DECODE row/format counts — no response body (absent: C-DECODE not flown) |")
    w("| `c-decode-ceiling-arithmetic.log` | the model-free arithmetic that refused C-DECODE (§6) |")
    w("| `postflight.log` | post-flight structural verification |")
    w("| `MANIFEST.sha256` | sha256 over every file above |")
    w("")
    w("Vectors, the retrieval plan body, and every C-DECODE response stay on the data root")
    w("(`$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb4r-4100/` and the run dir), per the")
    w("registration's own \"vectors/bank manifests on the data root, hashes only in Git\".")
    w("")

    (dest / "README.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"README.md written: {len(out)} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
