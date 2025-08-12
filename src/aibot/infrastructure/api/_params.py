from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClaudeParams:
    """Parameters for Claude (Anthropic) API calls.

    Attributes
    ----------
    model : str
        The Claude model to use.
    max_tokens : int
        The maximum number of tokens to generate.
    temperature : float
        The temperature parameter for response randomness.
    top_p : float
        The top_p parameter for nucleus sampling.

    """

    model: str
    max_tokens: int
    temperature: float
    top_p: float


@dataclass
class GeminiParams:
    """Parameters for Gemini (Google) API calls.

    Attributes
    ----------
    model : str
        The Gemini model to use.
    max_tokens : int
        The maximum number of tokens to generate.
    temperature : float
        The temperature parameter for response randomness.
    top_p : float
        The top_p parameter for nucleus sampling.

    """

    model: str
    max_tokens: int
    temperature: float
    top_p: float


@dataclass
class GPTParams:
    """Parameters for GPT (OpenAI) API calls.

    Attributes
    ----------
    model : str
        The GPT model to use.
    max_tokens : int
        The maximum number of tokens to generate.
    temperature : float
        The temperature parameter for response randomness.
    top_p : float
        The top_p parameter for nucleus sampling.

    """

    model: str
    max_tokens: int
    temperature: float
    top_p: float


# Type alias for any of the parameter classes
ParamsUnion = ClaudeParams | GeminiParams | GPTParams
