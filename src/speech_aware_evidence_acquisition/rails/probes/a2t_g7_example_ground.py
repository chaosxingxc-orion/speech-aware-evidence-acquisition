"""Pure control-plane core for the G7 construction-example family sweep."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
import re
from typing import Callable, Iterable, Sequence


ASSESSMENT_SUPPORT = "support"
ASSESSMENT_CONTRADICT = "contradict"
ASSESSMENT_UNCERTAIN = "uncertain"
_ASSESSMENT_STATUSES = frozenset(
    {ASSESSMENT_SUPPORT, ASSESSMENT_CONTRADICT, ASSESSMENT_UNCERTAIN}
)
_EMPTY_OBSERVATION = "No reliable observation was available."
_EVIDENCE_ID = re.compile(r"o1")
MAX_OBSERVATION_ASCII_BYTES = 1_024
SLOT_TOKENS = 32_768
OPERATIONAL_HEADROOM_TOKENS = 8_192
MAX_PROMPT_PLUS_COMPLETION_TOKENS = SLOT_TOKENS - OPERATIONAL_HEADROOM_TOKENS


class G7ExampleGroundError(ValueError):
    """Raised when a G7 construction or prompt violates the frozen protocol."""


@dataclass(frozen=True)
class Observation:
    text: str
    valid: bool


@dataclass(frozen=True)
class AssessmentRecord:
    tool_name: str
    status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class FamilyAssessment:
    family_tag: str
    strict_valid: bool
    tolerant_valid: bool
    records: tuple[AssessmentRecord, ...]
    invalid_record_count: int
    canonical_json: str


@dataclass(frozen=True)
class EvidenceContext:
    contact_id: str
    stage: str
    uses_audio: bool
    observation: str
    family_tag: str
    family_bundle_text: str
    tool_names: tuple[str, ...]
    instruction: str


@dataclass(frozen=True)
class NormalizedAssessment:
    family_tag: str
    tool_name: str
    status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionSheet:
    assessments: tuple[NormalizedAssessment, ...]
    text: str


@dataclass(frozen=True)
class ResolveContext:
    contact_id: str
    stage: str
    uses_audio: bool
    observation: str
    assessments: tuple[NormalizedAssessment, ...]
    tool_names: tuple[str, ...]
    execution_sheet: str
    instruction: str


@dataclass(frozen=True)
class PromptFit:
    contact_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    remaining_tokens: int


@dataclass(frozen=True)
class WorkflowResult:
    sample_id: str
    observation: Observation
    family_assessments: tuple[FamilyAssessment, ...]
    resolve_context: ResolveContext
    final_response_text: str


def parse_observation(text: str, tool_names: Iterable[str]) -> Observation:
    """Validate a bounded plain-English observation without repairing it."""
    valid = isinstance(text, str) and bool(text.strip())
    if valid:
        try:
            encoded = text.encode("ascii")
        except UnicodeEncodeError:
            valid = False
        else:
            valid = len(encoded) <= MAX_OBSERVATION_ASCII_BYTES
    folded = text.casefold() if isinstance(text, str) else ""
    if valid and any(name.casefold() in folded for name in tool_names):
        valid = False
    return Observation(text=text.strip() if valid else _EMPTY_OBSERVATION, valid=valid)


def _remove_exact_fence(text: str) -> tuple[str, bool]:
    if text.startswith("```json\n") and text.endswith("\n```"):
        return text[len("```json\n") : -len("\n```")], True
    return text, False


def _record(value: object, allowed: frozenset[str]) -> AssessmentRecord | None:
    if not isinstance(value, dict):
        return None
    name = value.get("tool_name")
    status = value.get("status")
    evidence = value.get("evidence")
    if name not in allowed or status not in _ASSESSMENT_STATUSES:
        return None
    if (
        not isinstance(evidence, list)
        or len(evidence) > 1
        or not all(
            isinstance(item, str) and _EVIDENCE_ID.fullmatch(item) is not None
            for item in evidence
        )
    ):
        return None
    return AssessmentRecord(name, status, tuple(evidence))


def parse_family_assessment(
    raw: str, *, family_tag: str, family_tool_names: Sequence[str]
) -> FamilyAssessment:
    """Parse nonfinal evidence prospectively, retaining valid sibling records."""
    body, fenced = _remove_exact_fence(raw)
    try:
        payload = json.loads(body)
    except (TypeError, json.JSONDecodeError):
        payload = None
    allowed = frozenset(family_tool_names)
    records: list[AssessmentRecord] = []
    invalid = 0
    tolerant = isinstance(payload, dict)
    values: object = [] if payload == {} else payload.get("assessments") if tolerant else None
    if not isinstance(values, list):
        tolerant = False
        values = []
    seen: set[str] = set()
    for value in values:
        row = _record(value, allowed)
        if row is None or row.tool_name in seen:
            invalid += 1
            continue
        seen.add(row.tool_name)
        records.append(row)
    strict = (
        tolerant
        and not fenced
        and isinstance(payload, dict)
        and set(payload) == {"assessments"}
        and invalid == 0
        and all(isinstance(item, dict) and set(item) == {"tool_name", "status", "evidence"} for item in values)
    )
    canonical = json.dumps(
        {"assessments": [row.__dict__ | {"evidence": list(row.evidence)} for row in records]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return FamilyAssessment(family_tag, strict, tolerant, tuple(records), invalid, canonical)


class G7ExampleGround:
    """Construct the fixed 28-family, 152-tool contact contexts without I/O."""

    def __init__(self, bundles: Sequence[object]) -> None:
        if len(bundles) != 28:
            raise G7ExampleGroundError("G7 requires exactly 28 family bundles")
        self.bundles = tuple(bundles)
        tags = tuple(str(bundle.family_tag) for bundle in bundles)
        if len(set(tags)) != 28:
            raise G7ExampleGroundError("family tags must be unique")
        names = tuple(name for bundle in bundles for name in bundle.tool_names)
        if len(names) != 152 or len(set(names)) != 152:
            raise G7ExampleGroundError("G7 requires exactly 152 unique tools")
        self.tool_names = names

    def build_evidence_contexts(self, observation: Observation) -> tuple[EvidenceContext, ...]:
        return tuple(
            EvidenceContext(
                contact_id=f"g7-evidence-{bundle.family_tag}",
                stage="EVIDENCE",
                uses_audio=True,
                observation=observation.text,
                family_tag=bundle.family_tag,
                family_bundle_text=bundle.text,
                tool_names=tuple(bundle.tool_names),
                instruction=(
                    "Assess every named family tool. Return exactly one JSON object with key "
                    "assessments. Each assessment uses exact keys tool_name, status, evidence. "
                    "status is exactly support, contradict, or uncertain. evidence is a JSON "
                    "list containing only the available OBS ID o1; use [] when it does not "
                    "applies. Example: {\"assessments\":[{\"tool_name\":\""
                    f"{bundle.tool_names[0]}\",\"status\":\"uncertain\",\"evidence\":[]}}]}}. "
                    "Do not infer, alias, correct, cross families, or fill parameter values."
                ),
            )
            for bundle in self.bundles
        )

    def build_execution_sheet(self, parsed: Sequence[FamilyAssessment]) -> ExecutionSheet:
        if len(parsed) != 28:
            raise G7ExampleGroundError("one assessment is required for every family")
        rows: list[NormalizedAssessment] = []
        lines: list[str] = []
        for bundle, assessment in zip(self.bundles, parsed, strict=True):
            if assessment.family_tag != bundle.family_tag:
                raise G7ExampleGroundError("assessment family order is not frozen")
            explicit = {row.tool_name: row for row in assessment.records}
            for tool in bundle.tools:
                found = explicit.get(tool.tool_name)
                status = found.status if found else ASSESSMENT_UNCERTAIN
                evidence = found.evidence if found else ()
                rows.append(NormalizedAssessment(bundle.family_tag, tool.tool_name, status, evidence))
                skeletons = "/".join(",".join(keys) for keys in tool.legal_key_skeletons)
                types = ",".join(f"{key}:{kind}" for key, kind in tool.types) or "-"
                normalized_evidence = ",".join(evidence) or "-"
                status_code = {
                    ASSESSMENT_SUPPORT: "S",
                    ASSESSMENT_CONTRADICT: "C",
                    ASSESSMENT_UNCERTAIN: "U",
                }[status]
                lines.append(
                    f"{tool.tool_name}={status_code}|{normalized_evidence}|"
                    f"{tool.operation}|keys:{skeletons}|types:{types}"
                )
        if len(rows) != 152:
            raise G7ExampleGroundError("execution sheet lost registered tools")
        return ExecutionSheet(tuple(rows), "\n".join(lines))

    def build_resolve_context(
        self, observation: Observation, parsed: Sequence[FamilyAssessment]
    ) -> ResolveContext:
        sheet = self.build_execution_sheet(parsed)
        return ResolveContext(
            contact_id="g7-resolve",
            stage="RESOLVE",
            uses_audio=True,
            observation=observation.text,
            assessments=sheet.assessments,
            tool_names=self.tool_names,
            execution_sheet=sheet.text,
            instruction=(
                "Use the original complete-dialogue audio, the observation, this all-tool "
                "execution sheet, and all normalized assessments. No cumulative raw history. "
                "Sheet codes mean S=support, C=contradict, U=uncertain. Assessments are advisory; "
                "C and U never remove a tool. Select an exact listed legal key skeleton and its "
                "types. Bind values only from the original audio or OBS. Preserve exact JSON "
                "value types, spelling, and requested call order. Never copy a construction "
                "example, registry default, or placeholder. "
                "Return only the unchanged official tool-call JSON array. Every array item "
                "must be an object with exactly the keys name and arguments; arguments must "
                "be one JSON object. Preserve multiple calls when requested. No prose, fence, "
                "metadata, placeholder, repair, or extra key is allowed."
            ),
        )

    def measure_prompt(
        self,
        *,
        contact_id: str,
        text: str,
        token_counter: Callable[[str], int],
        completion_tokens: int,
        speech_feature_tokens: int = 0,
    ) -> PromptFit:
        prompt = token_counter(text) + speech_feature_tokens
        total = prompt + completion_tokens
        remaining = SLOT_TOKENS - total
        if total > MAX_PROMPT_PLUS_COMPLETION_TOKENS:
            raise G7ExampleGroundError(
                "prompt is refused because it would leave less than 8192 operational tokens"
            )
        return PromptFit(contact_id, prompt, completion_tokens, total, remaining)


def execute_g7_workflows(
    *,
    sample_ids: Sequence[str],
    bundles: Sequence[object],
    invoke_contact: Callable[[str, str, object], str],
) -> tuple[WorkflowResult, ...]:
    """Execute independent sample workflows with exactly two active requests.

    This pure driver owns no transport. Each sample remains on one worker while
    OBS, 28 independent family assessments, and RESOLVE run in causal order.
    """
    core = G7ExampleGround(bundles)

    def run_one(sample_id: str) -> WorkflowResult:
        obs_raw = invoke_contact(
            sample_id,
            "OBS",
            {
                "contact_id": "g7-obs",
                "uses_audio": True,
                "instruction": (
                    "Describe the complete spoken request in bounded plain English. "
                    "Do not name tools or produce a final answer."
                ),
            },
        )
        observation = parse_observation(obs_raw, core.tool_names)
        contexts = core.build_evidence_contexts(observation)
        assessments = tuple(
            parse_family_assessment(
                invoke_contact(sample_id, "EVIDENCE", context),
                family_tag=context.family_tag,
                family_tool_names=context.tool_names,
            )
            for context in contexts
        )
        resolve = core.build_resolve_context(observation, assessments)
        final = invoke_contact(sample_id, "RESOLVE", resolve)
        return WorkflowResult(sample_id, observation, assessments, resolve, final)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="g7-sample") as pool:
        futures = [pool.submit(run_one, sample_id) for sample_id in sample_ids]
        return tuple(future.result() for future in futures)


def build_trace_documents(result: WorkflowResult) -> dict[str, object]:
    """Render separately hashable OBS, ORG, SUPPLY, and USE documents."""
    families = [
        {
            "family_tag": row.family_tag,
            "strict_valid": row.strict_valid,
            "tolerant_valid": row.tolerant_valid,
            "invalid_record_count": row.invalid_record_count,
            "normalized_assessment_sha256": __import__("hashlib")
            .sha256(row.canonical_json.encode("ascii"))
            .hexdigest(),
        }
        for row in result.family_assessments
    ]
    return {
        "obs_state": {
            "sample_id": result.sample_id,
            "valid": result.observation.valid,
            "text": result.observation.text,
        },
        "org_assessments": {"sample_id": result.sample_id, "families": families},
        "supply_sheet": {
            "sample_id": result.sample_id,
            "tool_count": len(result.resolve_context.tool_names),
            "tool_names": list(result.resolve_context.tool_names),
            "execution_sheet": result.resolve_context.execution_sheet,
        },
        "use_final": {
            "sample_id": result.sample_id,
            "response_text": result.final_response_text,
        },
    }
