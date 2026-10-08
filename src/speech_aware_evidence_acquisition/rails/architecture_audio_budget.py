"""Model-free whole-utterance audio adequacy for manual architecture generation.

This derives the complete legal contact ceiling; it neither grants spend nor
changes a registered plan. Capacity, graph and historical READ validators do
not call this generation-only precontact guard.
"""
from collections.abc import Mapping, Sequence
import math


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def manual_architecture_audio_budget_applies(values):
    """Identify generation scope without touching unrelated carrier samples."""
    return (bool(values.get("architecture_member"))
            and values.get("family_budget", {}).get("official_complete_scoring_jobs") == 1)


def derive_manual_architecture_audio_budget(values, duration_rows=None):
    """Return the exact duration-only bound, independently of the registered cap.

    Omitted rows use the composed, source-pinned runtime-view metadata. Runtime
    preflight supplies its actual adapter-loaded sample durations instead.
    Only explicit manual architecture generation cells are in scope.
    """
    if not manual_architecture_audio_budget_applies(values):
        return None
    _require(values.get("carrier_lock_key") == "slurp", "Manual audio adequacy supports whole-utterance SLURP only")
    _require(values.get("prepared_execution_units") is None
             and values.get("prepared_speech_observations") in (None, {})
             and values.get("live_speech_observations") in (None, {})
             and type(values.get("native_contact_fit", {}).get("max_speech_packets", 1)) is int
             and values.get("native_contact_fit", {}).get("max_speech_packets", 1) == 1,
             "Manual audio adequacy requires known whole-utterance, single-packet semantics")
    populations = values.get("populations")
    _require(isinstance(populations, list) and len(populations) == 1 and isinstance(populations[0], Mapping),
             "Manual audio adequacy requires one configured roster")
    ids = populations[0].get("ids")
    _require(isinstance(ids, list) and bool(ids) and all(isinstance(sid, str) and sid for sid in ids)
             and len(set(ids)) == len(ids)
             and type(values.get("population", {}).get("count")) is int
             and values["population"]["count"] == len(ids), "Manual audio roster count or identities differ")
    rows = values.get("items") if duration_rows is None else duration_rows
    _require(isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)) and bool(rows),
             "Manual audio duration metadata is missing")
    durations = {}
    for row in rows:
        _require(isinstance(row, Mapping), "Manual audio duration row must be a mapping")
        sid, seconds = row.get("sample_id"), row.get("audio_seconds")
        _require(isinstance(sid, str) and bool(sid) and sid not in durations,
                 "Manual audio duration identities are missing or duplicated")
        _require(type(seconds) in (int, float) and seconds > 0,
                 "Manual audio duration must be finite and positive")
        try:
            duration = float(seconds)
        except OverflowError as error:
            raise ValueError("Manual audio duration is not finite") from error
        _require(math.isfinite(duration), "Manual audio duration must be finite and positive")
        durations[sid] = duration
    _require(set(durations) == set(ids), "Manual audio duration roster differs from configured samples")
    from .controllers import default_phase_program
    from .native_episode_config import load_native_episode_config
    native = load_native_episode_config(values, default_phase_program(values["policy"]))
    _require(native is not None and type(native.max_contacts) is int and native.max_contacts > 0,
             "Manual audio adequacy requires parsed native contact bounds")
    try:
        seconds = math.fsum(float(durations[sid]) * native.max_contacts for sid in ids)
    except OverflowError as error:
        raise ValueError("Manual cumulative audio duration is not finite") from error
    _require(math.isfinite(seconds), "Manual cumulative audio duration is not finite")
    return {
        "schema": "saea-manual-whole-utterance-audio-budget-v1",
        "sample_count": len(ids),
        "max_contacts_per_sample": native.max_contacts,
        "required_audio_seconds": seconds,
        "required_integer_audio_seconds": math.ceil(seconds),
    }


def require_manual_architecture_audio_budget(values, duration_rows=None):
    """Refuse an inadequate registered generation cap without changing any bytes."""
    report = derive_manual_architecture_audio_budget(values, duration_rows)
    if report is None:
        return None
    registered = values.get("execution_plan", {}).get("planned_speech_audio_seconds")
    _require(type(registered) is int and registered > 0,
             "Registered cumulative speech-audio cap must be a positive integer")
    _require(registered >= report["required_integer_audio_seconds"],
             f"Registered cumulative speech-audio budget {registered} is below the complete legal bound "
             f"{report['required_integer_audio_seconds']}")
    return report
