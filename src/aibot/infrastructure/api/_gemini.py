from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse

from src.aibot.models.chat import ChatHistory, ChatMessage

from ._params import GeminiParams

_client = genai.Client()


async def generate_gemini_response(
    messages: list[ChatMessage],
    instruction: str,
    params: GeminiParams,
) -> GenerateContentResponse:
    """Generate a response from Gemini API.

    Parameters
    ----------
    messages : list[ChatMessage]
        The user's message (and message history).
    instruction : str
        The system instruction.
    params : GeminiParams
        The parameters controlling the response.

    Returns
    -------
    GenerateContentResponse
        The response from the Gemini API.

    """
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    contents = "\n".join([msg["content"] for msg in convo if msg["content"]])
    response = _client.models.generate_content(
        model=params.model,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=params.temperature,
            top_p=params.top_p,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        contents=contents,
    )

    return response  # noqa: RET504
