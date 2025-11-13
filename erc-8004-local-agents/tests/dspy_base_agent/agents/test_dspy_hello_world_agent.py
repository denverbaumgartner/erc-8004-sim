# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""E2E tests for DSPy HelloWorld agent."""

import logging
import os

import pytest

from erc_8004_local_agents.dspy_base_agent import (
    AgentFactory,
    DSPyAgentConfig,
    DSPyModelConfig,
)

# Configure logging for the test
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


class TestHelloWorldAgent:
    """Test suite for HelloWorldAgent."""

    def test_hello_world_agent_greets_user(self) -> None:
        """Test that the HelloWorldAgent can greet a user."""
        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Create agent configuration
        config = DSPyAgentConfig(
            agent_type="hello_world",
            name="HelloWorld Agent",
            description="A simple agent that says hello.",
            main_model=DSPyModelConfig(
                model="openrouter/google/gemini-2.5-flash",
                temperature=0.7,
                max_tokens=15000,
            ),
            adapter_model=DSPyModelConfig(
                model="openrouter/google/gemini-2.5-flash",
                temperature=0.7,
                max_tokens=15000,
            ),
            api_key=api_key,
            tools=["hello_world_tool"],
        )

        # Create agent using AgentFactory (no client needed for hello_world_tool)
        hello_agent = AgentFactory.create_agent(config, client=None)

        # Verify agent is created properly
        assert hello_agent is not None
        assert hello_agent.config.name == "HelloWorld Agent"
        assert len(hello_agent._tools) == 1

        # Run the agent
        result = hello_agent(input="World")

        # Verify the result
        assert result is not None
        assert hasattr(result, "output")
        assert "Hello" in result.output or "hello" in result.output.lower()
