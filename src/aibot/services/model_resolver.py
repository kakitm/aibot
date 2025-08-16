import json
from pathlib import Path
from typing import Any

from discord import app_commands

from src.aibot.logger import logger
from src.aibot.services.provider import ProviderManager, ProviderType


class ModelConfig:
    """Model configuration class."""

    def __init__(self, config_dict: dict[str, Any]) -> None:
        """Initialize model config from dictionary.

        Parameters
        ----------
        config_dict : dict[str, Any]
            Model configuration dictionary from JSON.

        """
        self.id: str = config_dict["id"]
        self.display_name: str = config_dict["display_name"]
        self.provider: ProviderType = config_dict["provider"]
        self.params: dict[str, Any] = config_dict["params"]


class ModelResolver:
    """Resolves model selection for Discord commands based on configuration."""

    _config_cache: dict[str, Any] | None = None
    _instance: "ModelResolver | None" = None

    def __new__(cls) -> "ModelResolver":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ModelResolver":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_config(self) -> dict[str, Any]:
        """Load model configuration from JSON file."""
        if self._config_cache is not None:
            return self._config_cache

        current_path = Path(__file__).resolve()
        config_path = None

        for parent in current_path.parents:
            if (parent / "pyproject.toml").exists():
                config_path = parent / "resources" / "llm-models.json"
                break

        if config_path is None or not config_path.exists():
            msg = "llm-models.json not found"
            logger.error(msg)
            raise FileNotFoundError(msg)

        with config_path.open() as f:
            self._config_cache = json.load(f)

        return self._config_cache

    def get_models_for_command(self, command_name: str) -> list[ModelConfig]:
        """Get available models for a specific command.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.

        Returns
        -------
        list[ModelConfig]
            List of available models for the command.

        """
        config = self._load_config()
        command_key = f"{command_name}_models"

        if command_key in config:
            return [ModelConfig(model_dict) for model_dict in config[command_key]]

        # Return empty list if no specific models for command
        return []

    def get_default_models(self) -> list[ModelConfig]:
        """Get default models.

        Returns
        -------
        list[ModelConfig]
            List of default models.

        """
        config = self._load_config()
        return [ModelConfig(model_dict) for model_dict in config.get("default_models", [])]

    def resolve_model_for_command(
        self,
        command_name: str,
        selected_model_id: str | None = None,
    ) -> ModelConfig:
        """Resolve the appropriate model for a command based on selection logic.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.
        selected_model_id : str | None
            Optionally selected model ID from UI choices.

        Returns
        -------
        ModelConfig
            The resolved model configuration.

        """
        command_models = self.get_models_for_command(command_name)
        provider_manager = ProviderManager.get_instance()
        current_provider = provider_manager.get_provider()

        # If specific model is selected from UI choices, use it
        if selected_model_id is not None and command_models:
            for model in command_models:
                if model.id == selected_model_id:
                    return model

        # If command has specific models
        if command_models and len(command_models) == 1:
            # Single model - check provider compatibility
            model = command_models[0]
            if model.provider == current_provider:
                return model
            # Provider mismatch - fallback to default
            return self._get_default_model_for_provider(current_provider)

        # No command-specific models - use default for current provider
        return self._get_default_model_for_provider(current_provider)

    def _get_default_model_for_provider(self, provider: ProviderType) -> ModelConfig:
        """Get default model for specified provider.

        Parameters
        ----------
        provider : ProviderType
            The provider type.

        Returns
        -------
        ModelConfig
            Default model for the provider.

        """
        default_models = self.get_default_models()

        # Find model matching provider
        for model in default_models:
            if model.provider == provider:
                return model

        # This should not happen with proper configuration
        msg = "No default models available"
        logger.error(msg)
        raise ValueError(msg)

    def get_choices_for_command(self, command_name: str) -> list[app_commands.Choice[str]]:
        """Get Discord app_commands choices for a command.

        Parameters
        ----------
        command_name : str
            The name of the Discord command.

        Returns
        -------
        list[app_commands.Choice[str]]
            List of choices for the command.

        """
        command_models = self.get_models_for_command(command_name)
        return [
            app_commands.Choice(name=model.display_name, value=model.id)
            for model in command_models
        ]


def get_model_choices(command_name: str) -> list[app_commands.Choice[str]]:
    """Get model choices for use with @app_commands.choices() decorator.

    This function provides a convenient way to get model choices for commands
    that need to use the @app_commands.choices() decorator.

    Parameters
    ----------
    command_name : str
        The name of the Discord command.

    Returns
    -------
    list[app_commands.Choice[str]]
        List of choices for use with @app_commands.choices().

    Examples
    --------
    >>> @app_commands.choices(model=get_model_choices("key_name"))
    ... async def some_command(interaction: Interaction, model: str | None = None):
    ...     # model parameter will have choices automatically applied
    ...     pass

    """
    resolver = ModelResolver.get_instance()
    return resolver.get_choices_for_command(command_name)
