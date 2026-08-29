"""Custom DeepEval judge for Nosana's OpenAI-compatible endpoint.

Guardrail: Nosana's glm-4.7-flash is a reasoning model — its default output
mixes reasoning text with JSON, which breaks DeepEval's JSON parser roughly
1 tile in N. The endpoint DOES accept `response_format=json_object`, though,
which forces the server itself to return valid JSON.

Enabling json_mode at the model wrapper level makes DeepEval hit the json-
enforced code path for every schema-driven call — accuracy (GEval) and
answer relevancy both use structured output internally.
"""
from __future__ import annotations

from deepeval.models import OpenAIModel


class NosanaJudge(OpenAIModel):
    """OpenAIModel subclass — same wire protocol, json_object mode always on."""

    def supports_json_mode(self) -> bool:
        return True

    def supports_structured_outputs(self) -> bool:
        # Nosana doesn't do OpenAI's beta.parse with Pydantic schemas —
        # only the response_format={"type":"json_object"} escape hatch.
        return False

    def get_model_name(self) -> str:
        return self.name
