from __future__ import annotations

import os

from discord import Message as DiscordMessage
from discord import MessageType

BOT_NAME = os.environ["BOT_NAME"]
BOT_ID = int(os.environ["BOT_ID"])


class ChatMessage:
    """Represents a single chat message with a role and content.

    Attributes
    ----------
    role : str
        The role of the message sender ("developer", "assistant", or "user").
    content : str | None
        The content of the message. Defaults to None.

    """

    def __init__(
        self,
        role: str,
        content: str | None = None,
    ) -> None:
        self.role = role
        self.content = content

    def format_message(self) -> dict[str, str]:
        """Format the message as a dictionary with "role" and "content" keys.

        Returns
        -------
        dict[str, str]
            A dictionary with "role" and "content" keys.

        """
        return {
            # If self.role matches BOT_NAME, return "assistant",
            # otherwise if self.role is "developer" or "assistant", use that value,
            # otherwise treat it as "user"
            "role": "assistant"
            if self.role == BOT_NAME
            else (self.role if self.role in ("developer", "assistant") else "user"),
            "content": self.content or "",
        }

    @classmethod
    def convert_to_chat_message(
        cls,
        discord_msg: DiscordMessage,
        channel_id: str | None = None,
    ) -> ChatMessage | None:
        """Convert a Discord message to a ChatMessage object.

        Parameters
        ----------
        discord_msg : DiscordMessage
            A message received from Discord.
        channel_id : str | None
            The ID of the channel.

        Returns
        -------
        ChatMessage | None
            A ChatMessage object if the message is valid, otherwise None.

        """
        # Case 1: channel_id exists - create ChatMessage
        if channel_id:
            return cls(role=discord_msg.author.name, content=discord_msg.content)

        # Case 2: thread created by BOT_ID - handle thread_starter_message
        if (
            discord_msg.type == MessageType.thread_starter_message
            and hasattr(discord_msg.channel, "owner_id")
            and discord_msg.channel.owner_id == BOT_ID
            and discord_msg.reference is not None
            and discord_msg.reference.cached_message is not None
        ):
            try:
                field = discord_msg.reference.cached_message.embeds[0].fields[0]
                return cls(role=discord_msg.author.name, content=field.value)
            except (AttributeError, IndexError):
                return None

        # Case 3: message in thread created by BOT_ID
        if hasattr(discord_msg.channel, "owner_id") and discord_msg.channel.owner_id == BOT_ID:
            return cls(role=discord_msg.author.name, content=discord_msg.content)

        return None


class ChatHistory:
    """Manage a collection of chat messages.

    Attributes
    ----------
    chat_msgs : list[ChatMessage]
        A list of ChatMessage objects representing the chat history.

    """

    def __init__(self, chat_msgs: list[ChatMessage]) -> None:
        self.chat_msgs = chat_msgs

    def render_messages(self) -> list[dict[str, str]]:
        """Render the chat messages into a list of dictionaries.

        Returns
        -------
        list[dict[str, str]]
            A list where each dictionary represents a chat message with
            "role" and "content" keys.

        """
        return [message.format_message() for message in self.chat_msgs]
