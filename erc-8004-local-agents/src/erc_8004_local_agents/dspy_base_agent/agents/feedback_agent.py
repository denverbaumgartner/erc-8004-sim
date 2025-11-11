"""HelloWorld agent implementation."""

import logging

import dspy

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class FeedbackAgentSignature(dspy.Signature):
    """You are a feedback agent. You have access to several tools that enable you to
    interact with agents and provide feedback.

    CRITICAL REQUIREMENT - AGENT DIVERSITY:
    You have multiple 'execute_and_review_request_to_...' tools available
    (e.g., execute_and_review_request_to_Test).
    Each tool corresponds to a DIFFERENT agent. In loops, you MUST vary which
    agent you review:
    - Loop 1: Use the FIRST available execute_and_review tool
    - Loop 2: Use the SECOND available execute_and_review tool
    - Loop 3: Use the THIRD available execute_and_review tool
    - Then cycle back or continue rotating through different agents

    DO NOT use the same execute_and_review tool in consecutive iterations.
    ALWAYS select a DIFFERENT execute_and_review_request_to_... tool than you
    used last time.

    Your workflow should be:
    1. List all available execute_and_review_request_to_... tools
    2. Select a DIFFERENT tool than previous iterations (rotate through them)
    3. Use that specific execute_and_review_request_to_... tool, which
       will:
       - Send the prompt to that agent
       - Automatically submit feedback with the score you provide
    4. The score should reflect the response quality

    Return back the summary including WHICH SPECIFIC AGENT you reviewed and
    the outcome.
    """

    input: str = dspy.InputField()
    output: str = dspy.OutputField()


class FeedbackAgent(BaseAgent):
    """Feedback agent that provides feedback to agents."""

    def _create_signature(self) -> type[dspy.Signature]:
        """Create the FeedbackAgent signature.

        Returns:
            FeedbackAgentSignature class
        """
        logger.debug("FeedbackAgent: Creating FeedbackAgentSignature")
        return FeedbackAgentSignature

    def _create_agent_module(self, signature: type[dspy.Signature]) -> dspy.Module:
        """Create a ReAct agent with the signature and tools.

        Args:
            signature: Signature class

        Returns:
            ReAct module instance
        """
        logger.debug(
            f"FeedbackAgent: Creating ReAct module with {len(self._tools)} tool(s)"
        )
        logger.debug(f"Using signature: {signature.__name__}")
        react_module = dspy.ReAct(signature, tools=self._tools)
        logger.debug("FeedbackAgent: ReAct module created successfully")
        return react_module

    def forward(self, input: str) -> dspy.Prediction:
        """Forward pass for providing feedback to an agent.

        Args:
            input: Input string for the agent

        Returns:
            Prediction with output
        """
        logger.info(f"FeedbackAgent: Starting forward pass with input: {input}")
        logger.debug("Calling internal ReAct agent...")
        result = self._agent(input=input)
        logger.info("FeedbackAgent: Forward pass completed")
        logger.debug(
            "Result fields: "
            f"{list(result.keys()) if hasattr(result, 'keys') else 'N/A'}"
        )
        return result

    async def aforward(self, input: str) -> dspy.Prediction:
        """Async forward pass for providing feedback to an agent.

        Args:
            input: Input string for the agent

        Returns:
            Prediction with output
        """
        logger.info(f"FeedbackAgent: Starting async forward pass with input: {input}")

        if not self._agent:
            logger.error("Agent not ready - tools not set")
            raise Exception("Agent not ready. Call set_tools first.")

        logger.debug(f"Setting LM context to: {self.lm.model}")
        with dspy.context(lm=self.lm):
            logger.debug("Calling internal ReAct agent asynchronously...")
            result = await self._agent.acall(input=input)
            logger.info("FeedbackAgent: Async forward pass completed")
            logger.debug(
                "Result fields: "
                f"{list(result.keys()) if hasattr(result, 'keys') else 'N/A'}"
            )
            return result
