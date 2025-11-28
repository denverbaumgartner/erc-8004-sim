# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Base agent class for DSPy agents."""

import logging
from abc import abstractmethod

import dspy

from .types import DSPyAgentConfig, DSPyModelConfig

logger = logging.getLogger(__name__)


class BaseAgent(dspy.Module):
    """Abstract base class for all DSPy agents."""

    def __init__(self, config: DSPyAgentConfig):
        """Initialize the base agent.

        Args:
            config: Agent configuration
        """
        super().__init__()
        logger.info(
            f"Initializing BaseAgent: {config.name} (type: {config.agent_type})"
        )
        self.config = config

        logger.info(f"Configuring main LM: {config.main_model.model}")
        self.lm = self._configure_lm(config.main_model, config.api_key)

        logger.info(f"Configuring adapter LM: {config.adapter_model.model}")
        self.adapter_lm = self._configure_lm(config.adapter_model, config.api_key)

        logger.info(f"Configuring cache for main LM: {config.main_model.model}")
        self._cache_state = self._configure_cache(config.main_model)

        self._tools: list[dspy.Tool] = []
        self._agent: dspy.Module | None = None
        logger.info(f"BaseAgent initialized: {config.name}")

    def _configure_lm(self, model_config: DSPyModelConfig, api_key: str) -> dspy.LM:
        """Configure a language model.

        Args:
            model_config: Model configuration
            api_key: API key for the model

        Returns:
            Configured LM instance
        """
        logger.debug(
            f"Creating LM instance - model: {model_config.model}, "
            f"temperature: {model_config.temperature}, "
            f"max_tokens: {model_config.max_tokens}"
        )
        lm = dspy.LM(
            model=model_config.model,
            api_key=api_key,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            cache=model_config.cache,
        )
        logger.debug(
            f"LM instance created successfully for model: {model_config.model}"
        )
        return lm

    def _configure_cache(self, model_config: DSPyModelConfig) -> bool:
        """Configure caching for the language model.

        Args:
            model_config: Model configuration

        Returns:
            Caching configuration
        """
        dspy.configure_cache(
            enable_disk_cache=model_config.cache,
            enable_memory_cache=model_config.cache,
        )
        logger.info(
            f"Caching configured for model: {model_config.model} to "
            f"{model_config.cache}"
        )
        return model_config.cache

    def set_tools(self, tools: list[dspy.Tool]) -> None:
        """Set the tools for the agent.

        Args:
            tools: List of DSPy tools
        """
        logger.info(f"Setting {len(tools)} tool(s) for agent: {self.config.name}")
        for tool in tools:
            logger.debug(f"  - Tool: {tool.name} - {tool.desc}")

        self._tools = tools
        logger.debug("Creating agent module with tools...")
        self._agent = self._create_agent()
        logger.info(f"Agent module created successfully for: {self.config.name}")

    @abstractmethod
    def _create_signature(self) -> type[dspy.Signature]:
        """Create the signature for the agent.

        Returns:
            Signature class
        """
        pass

    @abstractmethod
    def _create_agent_module(self, signature: type[dspy.Signature]) -> dspy.Module:
        """Create the agent module with the given signature.

        Args:
            signature: Signature class

        Returns:
            Agent module instance
        """
        pass

    def _create_agent(self) -> dspy.Module:
        """Create the agent module.

        Returns:
            Agent module instance
        """
        logger.debug("Creating agent signature...")
        signature = self._create_signature()
        logger.debug(f"Signature created: {signature.__name__}")

        logger.debug("Creating agent module from signature...")
        agent_module = self._create_agent_module(signature)
        logger.debug(f"Agent module created: {type(agent_module).__name__}")

        return agent_module

    @abstractmethod
    def forward(self, input: str) -> dspy.Prediction:
        """Forward pass for the agent.

        Args:
            input: Input string for the agent

        Returns:
            Prediction result
        """
        pass

    def __call__(self, input: str) -> dspy.Prediction:
        """Call the agent.

        Args:
            input: Input string for the agent

        Returns:
            Prediction result
        """
        logger.info(f"Calling agent: {self.config.name}")
        logger.debug(f"Input: {input}")

        if not self._agent:
            logger.error("Agent not ready - tools not set")
            raise Exception("Agent not ready. Call set_tools first.")

        logger.debug(f"Setting LM context to: {self.lm.model}")
        with dspy.context(lm=self.lm):
            logger.debug("Executing forward pass...")
            result = self.forward(input=input)
            logger.info(f"Agent call completed successfully for: {self.config.name}")
            logger.debug(f"Result type: {type(result).__name__}")

            return result
