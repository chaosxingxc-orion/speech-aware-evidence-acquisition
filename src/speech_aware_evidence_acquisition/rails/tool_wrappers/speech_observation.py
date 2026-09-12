"""Read prepared speech evidence without contacting its neural producer."""


def read_prepared_speech_observation(catalog, context):
    """Select exact source-bound ASR evidence; the next Solver owns the answer."""
    from ..tools import ToolResult

    return ToolResult(
        tool_id="saea-tool-prepared-speech-observation-v1",
        result=catalog.select(context=context),
    )
