# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""HelloWorld agent implementation."""

import logging

import dspy

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class HelloWorldSignature(dspy.Signature):
    """Respond to the user's input to the best of your ability."""

    input: str = dspy.InputField()
    output: str = dspy.OutputField()


class HelloWorldAgent(BaseAgent):
    """Simple agent that responds to user input."""

    def _create_signature(self) -> type[dspy.Signature]:
        """Create the HelloWorld signature.

        Returns:
            HelloWorldSignature class
        """
        logger.debug("HelloWorldAgent: Creating HelloWorldSignature")
        return HelloWorldSignature

    def _create_agent_module(self, signature: type[dspy.Signature]) -> dspy.Module:
        """Create a ReAct agent with the signature and tools.

        Args:
            signature: Signature class

        Returns:
            ReAct module instance
        """
        logger.debug(
            f"HelloWorldAgent: Creating ReAct module with {len(self._tools)} tool(s)"
        )
        logger.debug(f"Using signature: {signature.__name__}")
        react_module = dspy.ReAct(signature, tools=self._tools)
        logger.debug("HelloWorldAgent: ReAct module created successfully")
        return react_module

    def forward(self, input: str) -> dspy.Prediction:
        """Forward pass for greeting a user.

        Args:
            input: Input string for the agent

        Returns:
            Prediction with output
        """
        logger.info(f"HelloWorldAgent: Starting forward pass with input: {input}")
        logger.debug("Calling internal ReAct agent...")
        result = self._agent(input=input)
        logger.info("HelloWorldAgent: Forward pass completed")
        logger.debug(
            "Result fields: "
            f"{list(result.keys()) if hasattr(result, 'keys') else 'N/A'}"
        )
        return result
