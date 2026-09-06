"""Probe-protocol manifest (P0.C): frozen prompt templates + probe specs.

``PROBES`` is the declarative record of each sampled reproduction probe
(plan R1–R5): its arms, which template files each arm uses, the scorer that
reads its outputs, and the pre-registered sampling design. ``build_manifest``
hashes every referenced template byte-exactly; an ExecutionPlan's protocol
hash binds to the SHA-256 of the generated ``manifest.json`` blob. Editing a
template after its probe has run is forbidden — add a new file and a new
probe entry instead.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROBE_MANIFEST_VERSION = "probe-manifest-v1"

_SEED = 20260807

PROBES: dict[str, dict] = {
    "R1-audio2tool-direct": {
        "arms": {"direct": ["r1_audio2tool_direct.txt"]},
        "scorer": "a2t-scorer-v1 (toolcall_scoring)",
        "sampling": {"seed": _SEED, "design": "50 per tier x 8 tiers = 400 items"},
        "sample_receipt": "r1-audio2tool-sample.json",
        "success": "tier rank order preserved; per-tier |delta| <= 5pp vs published Qwen-3-Omni-30B row",
        "profile": "baseline-reproduction",
    },
    "R1-audio2tool-official-protocol": {
        "arms": {"direct": ["r1_audio2tool_official.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {"seed": _SEED, "design": "the SAME frozen 400 as R1-audio2tool-direct"},
        "sample_receipt": "r1-audio2tool-sample.json",
        "success": (
            "three outcomes: PASS = per-tier official tool accuracy |delta| <= 5pp vs the "
            "published Qwen3-Omni-30B row on tiers 1, 2, 5 and 6 with the tier rank order "
            "preserved; CONSISTENT-WITHIN-NOISE = the paper value inside the tier's Wilson "
            "CI90 (n=50) on those tiers but outside 5pp; FAIL otherwise"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "The README's own fidelity caveat, discharged: R1's templates were this "
            "repository's reconstruction of an unreleased protocol, and the caveat says R1 "
            "re-runs under the released prompts with a NEW manifest entry once they appear. "
            "They appeared on 2026-09-03 (github.com/audio2tool/Audio2Tool, MIT, commit "
            "b9d5383ca30945fbafb965a04bea40117e1e8a82). This is that entry: the template "
            "below is the release's own system message shape and the run adds the release's "
            "user-turn sentence after the audio (configs/baseline/"
            "a2t-direct-official-protocol.json). r1_audio2tool_direct.txt is UNCHANGED and "
            "stays the reconstruction R1/A0/A0' flew."
        ),
    },
    "R1-audio2tool-official-tier1-population": {
        "arms": {"direct": ["r1_audio2tool_official.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {
            "seed": 20260803,
            "design": (
                "500 of the 2,146 tier-1 queries of the RELEASE's own population (first "
                "successful speaker of every query_* directory), drawn uniformly without "
                "replacement"
            ),
        },
        "sample_receipt": "a2t-tier1-official-population-500.json",
        "success": (
            "three outcomes on the owner's 2026-09-04 alignment standard: ALIGNED = "
            "official tier-1 tool accuracy within 3 pp of the published 92.4 or better; "
            "CONSISTENT-WITHIN-NOISE = 92.4 inside the Wilson CI90 at n = 500 but outside "
            "3 pp; FAIL otherwise"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "Same template and same request as R1-audio2tool-official-protocol; only the "
            "POPULATION differs. The 2026-09-04 replication verdict ranked the roster "
            "first among the remaining Tier-1 suspects because the release evaluates the "
            "first successful speaker of every query of a tier while the frozen 400 is 50 "
            "mixed-speaker rows per tier. The receipt named above carries the 489 sample "
            "ids of that draw which no earlier receipt covers; the other 11 resolve "
            "through r1-audio2tool-sample.json and the two 104-row post-seal AgentLoop "
            "scoring receipts."
        ),
    },
    "R1-audio2tool-official-protocol-yaml": {
        "arms": {"direct": ["r1_audio2tool_official_yaml.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {"seed": _SEED, "design": "the SAME frozen 400 as R1-audio2tool-direct"},
        "sample_receipt": "r1-audio2tool-sample.json",
        "success": (
            "reported as a paired contrast against the sealed R-official-raw manifest on "
            "the same 400 rows, plus the same three-outcome alignment rule on tiers 1, 2, "
            "5 and 6"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "The released code has TWO spellings of the same four-sentence system prompt: "
            "the adapter's hard-coded default separates them with single spaces (flown as "
            "r1_audio2tool_official.txt) and configs/example_config.yaml carries them as a "
            "YAML block scalar, newline-separated with a trailing newline, which "
            "run_benchmark.py passes to the adapter whenever a config file is used. This "
            "template is that second spelling; it differs from r1_audio2tool_official.txt "
            "in whitespace alone (identical under str.split()). r1_audio2tool_official.txt "
            "is UNCHANGED and stays what the sealed R-official-raw cell flew."
        ),
    },
    "R1-audio2tool-official-tier258-population": {
        "arms": {"direct": ["r1_audio2tool_official.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {
            "seed": 20260803,
            "design": (
                "500 queries from each of the released tier2_parametric (3,160), "
                "tier5_needle (2,146) and tier8_intent_blending (821) populations -- the "
                "first recording the released loader resolves in every query_* directory "
                "-- drawn uniformly without replacement per tier"
            ),
        },
        "sample_receipt": "a2t-tier258-official-population-1500.json",
        "success": (
            "three outcomes per tier on the owner's 2026-09-04 alignment standard: "
            "ALIGNED = official tool accuracy within 3 pp of the published row (tier 2 "
            "84.6, tier 5 90.6, tier 8 41.7) or better; CONSISTENT-WITHIN-NOISE = the "
            "paper value inside the Wilson CI90 at n = 500 but outside 3 pp; FAIL "
            "otherwise. Reported against the Qwen-2.5-Omni-7B and "
            "weakest-published-SpeechLM floors whatever the outcome"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "Same template and same request as R1-audio2tool-official-tier1-population; "
            "only the tiers and the stratification differ. The 2026-09-04 tier-1 "
            "official-population verdict left tiers 2, 5 and 8 undecided on the frozen "
            "400: 74.0 / 78.0 / 34.0 against a published 84.6 / 90.6 / 41.7, all inside "
            "a CI90 of about +/-11 pp at n = 50. This draw takes 500 queries from each "
            "of those three tiers' own released populations. The receipt named above "
            "carries the 1,423 sample ids of that draw which no earlier receipt covers; "
            "the other 77 resolve through r1-audio2tool-sample.json and the two 104-row "
            "post-seal AgentLoop scoring receipts."
        ),
    },
    "R1-audio2tool-official-tier3467-population": {
        "arms": {"direct": ["r1_audio2tool_official.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {
            "seed": 20260803,
            "design": (
                "500 queries from each of the released tier3_multi_intent (2,146), "
                "tier4_implicit (2,132), tier6_correction (2,146) and tier7_multiturn "
                "(2,092 after this repository's two identity exclusions of the released "
                "2,146) populations -- the first recording the released loader resolves "
                "in every query_* directory, which on tier 7 is the FIRST user turn's "
                "wav -- drawn uniformly without replacement per tier"
            ),
        },
        "sample_receipt": "a2t-tier3467-official-population-2000.json",
        "success": (
            "three outcomes per tier on the owner's 2026-09-04 alignment standard: "
            "ALIGNED = official tool accuracy within 3 pp of the published row (tier 3 "
            "74.7, tier 4 33.4, tier 6 81.5, tier 7 54.6) or better; "
            "CONSISTENT-WITHIN-NOISE = the paper value inside the Wilson CI90 at n = 500 "
            "but outside 3 pp; FAIL otherwise. Reported against the Qwen-2.5-Omni-7B and "
            "weakest-published-SpeechLM floors whatever the outcome"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "Same template and same request as R1-audio2tool-official-tier258-population; "
            "only the tiers differ. The frozen 400 placed all four of these tiers inside "
            "the owner's 3-point band at n = 50 -- tier 3 72.0 against 74.7, tier 4 28.0 "
            "against 33.4, tier 6 84.0 against 81.5, tier 7 58.0 against 54.6 -- with a "
            "CI90 of about +/-11 pp, which cannot decide a 3-point rule either way. This "
            "draw takes 500 queries from each of those four tiers' own released "
            "populations and completes the eight-tier table at one resolution. The "
            "receipt named above carries the 1,954 sample ids of that draw which no "
            "earlier receipt covers; the other 46 resolve through "
            "r1-audio2tool-sample.json and the two 104-row post-seal AgentLoop scoring "
            "receipts."
        ),
    },
    "R1-audio2tool-org1-domain-grouped": {
        "arms": {"direct": ["r1_audio2tool_official_grouped.txt"]},
        "scorer": "a2t-scorer-official-b9d5383c (the pinned Audio2Tool release's own metrics.py)",
        "sampling": {
            "seed": 20260803,
            "design": (
                "no new draw: the UNION of the three sealed official-population rosters "
                "-- tier 1 (500), tiers 2/5/8 (1,500) and tiers 3/4/6/7 (2,000) = 4,000 "
                "rows -- reused id for id, so every row is paired with its own sealed "
                "official-protocol output"
            ),
        },
        "success": (
            "pooled paired delta on official tool accuracy against the sealed "
            "official-protocol outputs of the same 4,000 rows (10,000 replicates "
            "stratified by tier, seed 20260903, CI90, exact sign test): ADMITTED = CI90 "
            "lower bound above 0 AND the gain concentrated on smart_home cross-domain "
            "twins; NULL = CI90 contains 0; HARMFUL = CI90 upper bound below 0"
        ),
        "profile": "baseline-reproduction",
        "note": (
            "The pinned release ships TWO registry renderers. The sealed cells flew "
            "format_tools_compact, which drops the registry's domain and category "
            "columns; this template's fill is format_tools_for_prompt(tools, "
            "include_constraints=False), which groups the same 152 rows by domain. No "
            "system in the published Table 3 was run with it (the HF adapter hard-codes "
            "the compact form), so this is an ORGANIZATION of the same registry, never a "
            "claim about the paper's protocol. The template file's bytes are IDENTICAL "
            "to r1_audio2tool_official.txt -- only the fill differs -- and "
            "r1_audio2tool_official.txt is UNCHANGED. No sample_receipt: this roster's "
            "4,000 ids are already bound by a2t-tier1-official-population-500.json, "
            "a2t-tier258-official-population-1500.json, "
            "a2t-tier3467-official-population-2000.json, r1-audio2tool-sample.json and "
            "the two 104-row post-seal AgentLoop scoring receipts, and a receipt that "
            "repeated them would be refused as a duplicate."
        ),
    },
    "R2-bba-cascade-vs-direct": {
        "arms": {
            "direct": ["r2_bba_direct.txt"],
            "self_cascade": ["shared_transcribe.txt", "r2_bba_cascade_answer.txt"],
        },
        "scorer": "deterministic: normalized match of text after final 'Answer:' vs official_answer",
        "sampling": {"seed": _SEED, "design": "50 x 4 BBH categories = 200 items, paired arms"},
        "sample_receipt": "r2-bba-sample.json",
        "success": "cascade > direct, paired-significant (McNemar)",
        "profile": "bounded-discovery-probe",
    },
    "SLURP-DEV1000-CLOSED-LIST-DIRECT": {
        "arms": {"direct": ["slurp_direct_closed_list.txt"]},
        "scorer": (
            "slurp-slu-official (the real, unmodified official evaluate.py at pinned commit "
            "8eb16545762be97ace75334109d73824217311f1 in ~/.venvs/slurp-official-eval, "
            "--average micro), run through core.scoring_batch"
        ),
        "sampling": {
            "seed": 20260823,
            "design": (
                "no new draw: the frozen DEV-1000 roster the sealed 2026-08-25 "
                "SAEA-DEV1000-BASELINE-LOCK arms already flew, reused id-for-id"
            ),
        },
        "sample_receipt": "DEV-1000.json",
        "success": (
            "protocol alignment, not a threshold: this arm becomes the study's SLURP direct "
            "baseline regardless of outcome, because it is the one that matches the published "
            "prompt-only protocol (He & Garner arXiv:2305.13512 put the intent inventory IN the "
            "prompt). Reported as the official-metric table beside the sealed M0 comparator, the "
            "locked BLEND arm and the published brackets, with a paired per-sample contrast."
        ),
        "profile": "baseline-reproduction",
        "note": (
            "The template's fixed half is byte-identical to rails.adapters.slurp._INSTRUCTION and "
            "its {tool_schemas} fill (slurp-label-inventory) renders the UNCHANGED "
            "render_slurp_ontology task contract followed by the compact closed inventory, so the "
            "rendered instruction is the sealed DEV-1000 M0 instruction (sha256 cef52789...86b8, "
            "5,747 chars) plus a pure 1,836-char suffix and nothing else. Correction to the "
            "premise of the 2026-09-04 audit's caveat 4: the sealed M0 prompt DID carry the 18 "
            "scenarios, the 46 actions and the 55 entity types; what it never carried is the "
            "60-pair scenario/action intent inventory, which is what this template adds."
        ),
    },
    "SLURP-CONSUMPTION-KU-S1": {
        "arms": {
            "direct_evidence": ["slurp_phase_direct.txt", "slurp_phase_evidence.txt"]
        },
        "scorer": (
            "slurp-slu-official (the same pinned official evaluate.py as "
            "SLURP-DEV1000-CLOSED-LIST-DIRECT), run through core.scoring_batch"
        ),
        "sampling": {
            "seed": 20260823,
            "design": (
                "the same DEV-1000 roster KU-S1c and the closed-list comparator "
                "flew, id-for-id"
            ),
        },
        "sample_receipt": "DEV-1000.json",
        "success": (
            "Preregistered in docs/readiness/"
            "2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md and unchanged "
            "by E6: the decision population is the unexposed NEW500 and the "
            "comparator is the one-contact closed-list direct arm, with KU-S1c's own "
            "draft row quoted as the contact-matched and control-turn-matched view"
        ),
        "profile": "bounded-discovery-probe",
        "note": (
            "Cell KU-S1 of the 2026-09-05 three-dimension experiment program: the "
            "SLURP consumption dimension's RETRIEVAL cell, unblocked by enabler E6. "
            "Neither template is the system message -- that stays the closed-list "
            "instruction, byte-identical to the sealed SLURP direct baseline's and to "
            "KU-S1c's. They are the two per-phase CONTROL turns of "
            "phase-direct-evidence-alpha-blend-v1. The retrieved values are NOT in "
            "either template and never can be: E6 removed the "
            "fold-a-packet-into-the-instruction path, and the supply travels the "
            "successor QueryState as typed content blocks instead. Measured against "
            "the FULL slurp-kb-size-full snapshot (23,267 protected payloads, content "
            "dimension included): 0 collisions for either template."
        ),
    },
    "SLURP-PHASE-DIRECT-ONLY": {
        "arms": {"direct": ["slurp_phase_direct.txt"]},
        "scorer": (
            "slurp-slu-official (the same pinned official evaluate.py as "
            "SLURP-DEV1000-CLOSED-LIST-DIRECT), run through core.scoring_batch"
        ),
        "sampling": {
            "seed": 20260823,
            "design": (
                "no new draw: the four DEV-1000 rows the sealed closed-list wiring "
                "proof already flew, reused id-for-id"
            ),
        },
        "sample_receipt": "DEV-1000.json",
        "success": (
            "a wiring gate, not a threshold: 4 of 4 contacts, exactly one phase in the "
            "run_phases receipt, one sealed outputs row per sample, a phases file whose "
            "sha256 the seal receipt records, and every declared scorer running to "
            "completion over the complete manifest"
        ),
        "profile": "bounded-discovery-probe",
        "note": (
            "E1/MF-5. This template is NOT the system message -- that stays the closed-list "
            "instruction (slurp_direct_closed_list.txt). It is the per-phase CONTROL turn of "
            "phase-direct-only-v1, which rails.core_client._agent_history appends to the "
            "payload's history, and is the ONE thing this cell adds to the sealed closed-list "
            "direct arm's request. configs/baseline/slurp-phase-direct-only-v1.json."
        ),
    },
    "A2T-PHASE-SELECT-THEN-FILL": {
        "arms": {"select_then_fill": ["a2t_phase_select.txt", "a2t_phase_fill.txt"]},
        "scorer": "a2t-toolcall and a2t-toolcall-v2, run through core.scoring_batch",
        "sampling": {
            "seed": _SEED,
            "design": (
                "no new draw: the four frozen-400 rows the sealed calibration wiring proof "
                "already flew, reused id-for-id"
            ),
        },
        "sample_receipt": "r1-audio2tool-sample.json",
        "success": (
            "a wiring gate, not a threshold: 8 of 8 contacts, exactly two phases in the "
            "run_phases receipt, ONE sealed outputs row per sample carrying the fill phase's "
            "text, both summaries in the phases file, and every declared scorer running to "
            "completion over the complete manifest"
        ),
        "profile": "bounded-discovery-probe",
        "note": (
            "E1/MF-5. Neither template is the system message -- that stays the adapter's own "
            "legacy registry instruction, exactly as the sealed P0-legacy-packets cell sent it. "
            "These two are the per-phase CONTROL turns of phase-select-then-fill-v1, and they "
            "carry NO registry fill on purpose: rails.runner refuses a contact instruction "
            "containing any facet or value text of the bound knowledge snapshot, and the "
            "compact registry rendering contains several. configs/baseline/"
            "a2t-phase-select-then-fill-v1.json."
        ),
    },
    "R3-airbench-slurp-ic": {
        "arms": {
            "direct": ["r3_airbench_ic_direct.txt"],
            "self_cascade": ["shared_transcribe.txt", "r3_airbench_ic_cascade_answer.txt"],
        },
        "scorer": "deterministic: choice-letter match against gold choice",
        "sampling": {"seed": _SEED, "design": "200 of the AIR-Bench 1k SLURP-IC items, paired arms"},
        "success": "cascade > direct; absolute rows recorded to baseline wiki",
        "profile": "bounded-discovery-probe",
        "status": "BLOCKED: AIR-Bench data not on disk; acquisition needs the umbrella lock path",
    },
    "R4-context-dose": {
        "arms": {
            "no_context": ["r4_transcribe_nocontext.txt"],
            "matched_context": ["r4_transcribe_with_context.txt"],
            "mismatched_context": ["r4_transcribe_with_context.txt"],
        },
        "runtime_binding": (
            "2026-08-08 Route-1 retarget: under the R0 core driver the arm instructions are the "
            "task_instruction fields of configs/baseline/{bare-core,fixed-legal-context,"
            "mismatched-evidence}.json (bound into protocol_hash via config_hash); the r4_*.txt "
            "templates above are the design-time reference, not runtime-wired. The mismatched arm's "
            "instruction was equalized to the matched arm's on 2026-08-08 (a design-leak fix: the "
            "negative-control explanation must never reach the model)."
        ),
        "scorer": "frozen scoring stack (asr-wer + cost); per-entity-class WER deferred until an owner-pinned wer_tags adapter exists",
        "sampling": {
            "seed": _SEED,
            "design": (
                "Route 1 (2026-08-08): e21 discovery carrier (e22 dev subset10 has no registered "
                "ConEC evidence layer). Mini-arm revision (same day, after the smoke measured "
                "RTF~0.57): seeded 10-of-44 subset of the frozen discovery split; segmented "
                "execution per the owner's agentic long-form directive (segments receipt derives "
                "from this parent receipt via scripts/build_segments.py)"
            ),
        },
        "sample_receipt": "r4-e21-sub10-sample.json",
        "success": "WER monotone in evidence quality (Siskos direction): matched < no-context and matched < mismatched",
        "profile": "bounded-discovery-probe",
        "note": "matched arm uses the call's own ConEC contexts layer; mismatched arm uses the deterministic rotation derangement; oracle/gold evidence hard-raises on the runtime path",
    },
    "R5-vab-oneshot": {
        "arms": {
            "zero_shot": ["r5_vab_zeroshot.txt"],
            "one_shot": ["r5_vab_oneshot.txt"],
        },
        "scorer": "a2t-scorer-v1 components (tool selection / structure); semantic PF only via pinned local judge if unavoidable",
        "sampling": {"seed": _SEED, "design": "50 per EN complex stratum (parallel/seqdep/multi-turn); strata under 50 taken whole = 140 items, paired arms"},
        "sample_receipt": "r5-vab-sample.json",
        "success": "one-shot > zero-shot; magnitude compared to published +10-17pp",
        "profile": "bounded-discovery-probe",
    },
}

SAMPLING_POLICY = (
    "Each carrier is sampled exactly once, by scripts/build_probe_samples.py "
    "(seeded, order-independent, metadata-only); the receipt under "
    "docs/receipts/probe-samples/ is frozen and every later experiment on that "
    "carrier resolves its items through the binding in this manifest — never "
    "through a fresh draw. Adding a carrier means adding a new receipt through "
    "the same script and regenerating this manifest; changing an existing "
    "receipt requires owner approval and a new probe entry. R4 draws from the "
    "already-frozen dev subset10 split receipt (docs/receipts/splits.json); "
    "R3 has no sample yet (data acquisition blocked)."
)

DECODE_DISCIPLINE = {
    "temperature": 0,
    "note": "greedy decoding for all scoring arms; sampling-based arms (R7 n-best) get their own entry when designed",
}


def _load_verified_receipt(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"sample receipt missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    from .sampling import split_identity_hash

    recomputed = split_identity_hash([item["key"] for item in payload["items"]])
    if recomputed != payload["split_identity_hash"]:
        raise ValueError(
            f"split_identity_hash mismatch in {path.name}: receipt says "
            f"{payload['split_identity_hash'][:16]}…, items hash to {recomputed[:16]}…"
        )
    return payload


def build_manifest(templates_dir: Path, receipts_dir: Path) -> dict:
    referenced = sorted(
        {
            template
            for probe in PROBES.values()
            for templates in probe["arms"].values()
            for template in templates
        }
    )
    hashes: dict[str, dict[str, str]] = {}
    for name in referenced:
        path = templates_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"referenced template missing: {path}")
        hashes[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    samples: dict[str, dict] = {}
    for probe_name, probe in PROBES.items():
        receipt_name = probe.get("sample_receipt")
        if receipt_name is None:
            continue
        payload = _load_verified_receipt(receipts_dir / receipt_name)
        samples[probe_name] = {
            "receipt": receipt_name,
            "split_identity_hash": payload["split_identity_hash"],
            "n_items": len(payload["items"]),
            "seed": payload["seed"],
            "split_role": payload["split_role"],
        }

    return {
        "manifest_version": PROBE_MANIFEST_VERSION,
        "decode": DECODE_DISCIPLINE,
        "sampling_policy": SAMPLING_POLICY,
        "templates": hashes,
        "samples": samples,
        "probes": PROBES,
    }


def write_manifest(templates_dir: Path, receipts_dir: Path, out_path: Path) -> dict:
    manifest = build_manifest(templates_dir, receipts_dir)
    out_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
