from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.moderation_create_response import ModerationCreateResponse

from src.aibot.models.chat import ChatHistory, ChatMessage

from ._params import GPTParams

_client = OpenAI()


async def generate_openai_response(
    messages: list[ChatMessage],
    instruction: str,
    params: GPTParams,
) -> ChatCompletion:
    """Generate a response from OpenAI API.

    Parameters
    ----------
    messages : list[ChatMessage]
        The user's message (and message history).
    instruction : str
        The system instruction.
    params : GPTParams
        The parameters controlling the response.

    Returns
    -------
    ChatCompletion
        The response from the OpenAI API.

    """
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    full_prompt = [{"role": "developer", "content": instruction}, *convo]
    response = _client.chat.completions.create(
        model=params.model,
        messages=full_prompt,
        max_tokens=params.max_tokens,
        temperature=params.temperature,
        top_p=params.top_p,
    )

    return response  # noqa: RET504


async def get_openai_moderation_result(content: str) -> ModerationCreateResponse:
    """Get detailed moderation results from OpenAI.

    Parameters
    ----------
    content : str
        Content to moderate

    Returns
    -------
    ModerationCreateResponse
        Detailed moderation result including categories and scores

    """
    moderation_response = _client.moderations.create(
        model="omni-moderation-latest",
        input=content,
    )
    return moderation_response  # noqa: RET504
