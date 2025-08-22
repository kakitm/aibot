import os

from anthropic.types import Message as AnthropicMessage
from google.genai.types import GenerateContentResponse
from openai.types.chat import ChatCompletion

from src.aibot.logger import logger
from src.aibot.models.chat import ChatMessage
from src.aibot.services.model_resolver import ModelConfig

from ._anthropic import generate_anthropic_response
from ._gemini import generate_gemini_response
from ._openai import generate_openai_response
from ._params import ClaudeParams, GeminiParams, GPTParams, ParamsUnion

# Type alias for any LLM response
LLMResponse = AnthropicMessage | GenerateContentResponse | ChatCompletion


class ResponseFactory:
    """Singleton factory for creating chat messages from LLM responses.

    This factory is responsible for:
    1. Converting ModelConfig to provider-specific parameters
    2. Calling appropriate LLM provider
    3. Converting LLM response to ChatMessage

    """

    _instance: "ResponseFactory | None" = None

    def __new__(cls) -> "ResponseFactory":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ResponseFactory":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_api_key(self, provider: str) -> str:
        """Get API key for the specified provider.

        Parameters
        ----------
        provider : str
            The provider name (anthropic, google, openai).

        Returns
        -------
        str
            The API key.

        Raises
        ------
        ValueError
            If API key is not found.

        """
        # Handle special case for Google provider which uses GEMINI_API_KEY
        if provider == "google":
            env_key = os.getenv("GEMINI_API_KEY")
        else:
            env_key = os.getenv(f"{provider.upper()}_API_KEY")

        if env_key:
            return env_key

        expected_key = "GEMINI_API_KEY" if provider == "google" else f"{provider.upper()}_API_KEY"
        msg = f"No API key found for {provider}. Expected environment variable: {expected_key}"
        raise ValueError(msg)

    def _create_chat_message(self, response: LLMResponse) -> ChatMessage:
        """Convert LLM response to ChatMessage.

        Parameters
        ----------
        response : LLMResponse
            The LLM response object.

        Returns
        -------
        ChatMessage
            The converted chat message.

        Raises
        ------
        ValueError
            If content extraction fails.

        """
        try:
            content: str | None = None

            if isinstance(response, AnthropicMessage):
                content = response.content[0].text
            elif isinstance(response, GenerateContentResponse):
                content = response.text
            elif isinstance(response, ChatCompletion):
                content = response.choices[0].message.content

            if content is None:
                msg = f"Failed to extract content from {type(response).__name__}"
                logger.error(msg)

            return ChatMessage(role="assistant", content=content)

        except Exception as e:
            msg = f"Failed to extract content from {type(response).__name__}: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e

    def _create_provider_params(self, model_config: ModelConfig) -> ParamsUnion:
        """Convert ModelConfig to provider-specific parameters.

        Parameters
        ----------
        model_config : ModelConfig
            The model configuration.

        Returns
        -------
        ParamsUnion
            Provider-specific parameters object.

        Raises
        ------
        ValueError
            If provider is not supported.

        """
        provider = model_config.provider
        model_id = model_config.id
        params = model_config.params

        if provider == "anthropic":
            return ClaudeParams(
                model=model_id,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"],
                top_p=params["top_p"],
            )
        if provider == "google":
            return GeminiParams(
                model=model_id,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"],
                top_p=params["top_p"],
            )
        if provider == "openai":
            return GPTParams(
                model=model_id,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"],
                top_p=params["top_p"],
            )

        msg = f"Unsupported provider: {provider}"
        raise TypeError(msg)

    async def generate_llm_response(
        self,
        messages: ChatMessage | list[ChatMessage],
        instruction: str,
        model_config: ModelConfig,
    ) -> ChatMessage:
        """Generate a response using the appropriate LLM provider.

        Parameters
        ----------
        messages : ChatMessage | list[ChatMessage]
            Input messages for the LLM.
        instruction : str
            System instruction for the LLM.
        model_config : ModelConfig
            Model configuration to use.

        Returns
        -------
        ChatMessage
            Generated response from LLM.

        Raises
        ------
        ValueError
            If provider is not supported or API call fails.

        """
        provider_params = self._create_provider_params(model_config)

        try:
            response: LLMResponse
            if isinstance(provider_params, ClaudeParams):
                response = await generate_anthropic_response(
                    messages,
                    instruction,
                    provider_params,
                )
            elif isinstance(provider_params, GeminiParams):
                response = await generate_gemini_response(messages, instruction, provider_params)
            elif isinstance(provider_params, GPTParams):
                response = await generate_openai_response(messages, instruction, provider_params)
            else:
                msg = f"Unsupported provider params type: {type(provider_params)}"
                logger.error(msg)

            return self._create_chat_message(response)

        except Exception as e:
            logger.error("Failed to generate LLM response with model %s: %s", model_config.id, e)
            raise
