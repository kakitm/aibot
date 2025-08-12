import anthropic
from anthropic.types import Message as AnthropicMessage

from src.aibot.models.chat import ChatHistory, ChatMessage

from ._params import ClaudeParams

client = anthropic.Anthropic()


async def generate_anthropic_response(
    messages: ChatMessage | list[ChatMessage],
    instruction: str,
    params: ClaudeParams,
) -> AnthropicMessage:
    """Generate a response from Anthropic API.

    Parameters
    ----------
    messages : ChatMessage | list[ChatMessage]
        The user's message (and message history).
    instruction : str
        The system instruction.
    params : ClaudeParams
        The parameters controlling the response.

    Returns
    -------
    AnthropicMessage
        The response from the Anthropic API.

    """
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    response = client.messages.create(
        model=params.model,
        messages=convo,
        max_tokens=params.max_tokens,
        system=instruction,
        temperature=params.temperature,
        top_p=params.top_p,
    )

    return response  # noqa: RET504
