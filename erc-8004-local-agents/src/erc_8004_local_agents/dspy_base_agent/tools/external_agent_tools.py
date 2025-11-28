# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Factory functions for creating tools that interact with external agents."""

import logging
from typing import Optional

import dspy
from a2a.types import AgentCard
from erc8004 import ERC8004Client

from erc_8004_local_agents.agents.a2a_client import A2AClientWrapper

logger = logging.getLogger(__name__)


class AgentResponseReview(dspy.Signature):
    """Evaluate an AI agent's response to a prompt."""

    prompt: str = dspy.InputField(desc="The original prompt given to the agent.")
    response: str = dspy.InputField(desc="The response from the agent.")
    review_comment: str = dspy.InputField(
        desc=(
            "An optional modifying string for the review signature to guide "
            "the review."
        )
    )
    score: int = dspy.OutputField(
        desc="A score from 0 to 100 evaluating the response quality."
    )
    comment: str = dspy.OutputField(desc="A brief comment explaining the score.")


def _agent_summary_from_agent_card(agent_card: AgentCard) -> str:
    """Generate a human-readable summary of an agent from its agent card.

    Args:
        agent_card: The agent card containing agent metadata

    Returns:
        A formatted text summary of the agent's capabilities
    """
    # Start with basic info
    summary_parts = [
        f"Agent: {agent_card.name}",
        f"Description: {agent_card.description}",
        f"URL: {agent_card.url}",
        f"Version: {agent_card.version}",
    ]

    # Add documentation URL if available
    doc_url = getattr(agent_card, "documentationUrl", None) or getattr(
        agent_card, "documentation_url", None
    )
    if doc_url:
        summary_parts.append(f"Documentation: {doc_url}")

    # Add input/output modes (try both camelCase and snake_case)
    input_modes = getattr(agent_card, "defaultInputModes", None) or getattr(
        agent_card, "default_input_modes", None
    )
    output_modes = getattr(agent_card, "defaultOutputModes", None) or getattr(
        agent_card, "default_output_modes", None
    )

    if input_modes:
        summary_parts.append(f"Input Modes: {', '.join(input_modes)}")
    if output_modes:
        summary_parts.append(f"Output Modes: {', '.join(output_modes)}")

    # Add capabilities
    capabilities = []
    caps = getattr(agent_card, "capabilities", None)
    if caps and getattr(caps, "streaming", False):
        capabilities.append("streaming")
    if capabilities:
        summary_parts.append(f"Capabilities: {', '.join(capabilities)}")

    # Add skills section
    skills = getattr(agent_card, "skills", None) or []
    if skills:
        summary_parts.append("\nSkills:")
        for skill in skills:
            skill_name = getattr(skill, "name", "Unknown")
            skill_desc = getattr(skill, "description", "")
            summary_parts.append(f"  - {skill_name}: {skill_desc}")

            skill_examples = getattr(skill, "examples", None) or []
            if skill_examples:
                examples = ", ".join(
                    f'"{ex}"' for ex in skill_examples[:3]
                )  # Limit to 3 examples
                summary_parts.append(f"    Examples: {examples}")

    return "\n".join(summary_parts)


def create_external_agent_tool(
    a2a_client: A2AClientWrapper,
    input_address: str,
) -> dspy.Tool:
    """Creates a tool to execute a request against a specific, connected agent.

    Args:
        a2a_client: Initialized A2AClientWrapper for the target agent
        input_address: Address of the agent making requests (used for feedback auth)

    Returns:
        A dspy.Tool configured to send messages to the external agent
    """
    # Get agent card from the wrapper
    agent_card = a2a_client.agent_card
    if not agent_card:
        raise ValueError("A2AClientWrapper must be initialized before creating tools")

    async def execute_request(prompt: str) -> str:
        """Submits a request to the external agent.

        Args:
            prompt: The message text to send to the agent

        Returns:
            The text response from the agent
        """
        logger.info(f"Utilizing the execute_request tool... {prompt[:10]}")
        try:
            response = await a2a_client.send_message(
                text=prompt,
                input_address=input_address,
            )

            # Extract text from response
            if hasattr(response, "root") and hasattr(response.root, "result"):
                result = response.root.result  # type: ignore[attr-defined]
                if hasattr(result, "parts"):
                    text_parts = []
                    for part in result.parts:  # type: ignore[attr-defined]
                        if hasattr(part, "text"):
                            # type: ignore[attr-defined,union-attr]
                            text_parts.append(part.text)
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            # type: ignore[attr-defined,union-attr]
                            text_parts.append(part.root.text)
                    if text_parts:
                        return " ".join(text_parts)

            return str(response)

        except Exception as e:
            logger.error(f"Error executing request to {agent_card.name}: {e}")
            return f"Error: {str(e)}"

    agent_name_safe = agent_card.name.replace(" ", "_").replace("-", "_")
    return dspy.Tool(
        func=execute_request,
        name=f"execute_request_to_{agent_name_safe}",
        desc=(
            f"Executes a request to the agent '{agent_card.name}'. "
            f"{_agent_summary_from_agent_card(agent_card)}"
        ),
    )


def create_external_agent_review_tool(
    a2a_client: A2AClientWrapper,
    erc8004_client: ERC8004Client,
    input_address: str,
    agent_id: Optional[int] = None,
    lm: Optional[dspy.LM] = None,
) -> dspy.Tool:
    """Creates a tool to execute a request and submit on-chain feedback.

    Args:
        a2a_client: Initialized A2AClientWrapper for the target agent
        erc8004_client: ERC8004Client for submitting on-chain feedback
        input_address: Address of the agent making requests (used for feedback auth)
        agent_id: Optional on-chain agent ID (only needed if submitting feedback)
        lm: Optional DSPy language model instance for automated review scoring

    Returns:
        A dspy.Tool configured to send messages and submit feedback
    """
    # Get agent card from the wrapper
    agent_card = a2a_client.agent_card
    if not agent_card:
        raise ValueError("A2AClientWrapper must be initialized before creating tools")

    async def execute_and_review(
        prompt: str,
        review_comment: str = "Evaluate the quality and accuracy of this response.",
    ) -> str:
        """Submits a request and provides feedback.

        Args:
            prompt: The message text to send to the agent
            review_comment: Optional guidance for the automated review
                (default: general evaluation)

        Returns:
            A string containing the response and feedback transaction info
        """
        logger.info(f"Utilizing the execute_and_review tool... prompt: {prompt[:10]}")
        try:
            response = await a2a_client.send_message(
                text=prompt,
                input_address=input_address,
            )

            # Extract text from response
            response_text = str(response)
            if hasattr(response, "root") and hasattr(response.root, "result"):
                result = response.root.result  # type: ignore[attr-defined]
                if hasattr(result, "parts"):
                    text_parts = []
                    for part in result.parts:  # type: ignore[attr-defined]
                        if hasattr(part, "text"):
                            # type: ignore[attr-defined,union-attr]
                            text_parts.append(part.text)
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            # type: ignore[attr-defined,union-attr]
                            text_parts.append(part.root.text)
                    if text_parts:
                        response_text = " ".join(text_parts)

                # Check for feedback_auth in metadata
                feedback_auth = None
                if hasattr(result, "metadata") and result.metadata:
                    feedback_auth = result.metadata.get("feedback_auth")
                    logger.info(f"Found feedback_auth in metadata: {feedback_auth}")
                else:
                    logger.warning(
                        "No metadata or feedback_auth in response. "
                        f"result type: {type(result)}, "
                        f"hasattr metadata: {hasattr(result, 'metadata')}"
                    )

                if not feedback_auth:
                    return (
                        f"Response: {response_text}\n"
                        "Feedback: Not available (no feedback_auth provided)"
                    )

                if agent_id is None:
                    return (
                        f"Response: {response_text}\n"
                        "Feedback: Cannot submit (agent_id not available)"
                    )

                # Use LM to review the response and generate score
                if lm is None:
                    logger.warning(
                        "No language model provided for review, using default "
                        "score of 50"
                    )
                    score = 50
                    review_justification = "No LM available for automated review"
                else:
                    logger.info("Using LM to review agent response")
                    try:
                        # Create a predictor with the review signature
                        reviewer = dspy.ChainOfThought(AgentResponseReview)

                        # Run the review with the current LM context
                        with dspy.context(lm=lm):
                            review_result = reviewer(
                                prompt=prompt,
                                response=response_text,
                                review_comment=review_comment,
                            )

                        score = int(review_result.score)
                        review_justification = review_result.comment
                        logger.info(
                            f"LM review complete: score={score}, "
                            f"comment={review_justification}"
                        )
                    except Exception as e:
                        logger.error(f"Error during LM review: {e}")
                        score = 50
                        review_justification = f"Review error: {str(e)}"

                # Submit feedback
                logger.info(
                    f"Submitting feedback for agent_id={agent_id} with "
                    f"score={score}, comment: {review_justification}"
                )
                result = erc8004_client.reputation.give_feedback(
                    agent_id=agent_id,
                    score=score,
                    feedback_auth=feedback_auth,
                )
                logger.info(
                    f"Feedback submitted successfully for agent_id={agent_id}, "
                    f"tx_hash={result['txHash']}"
                )

                return (
                    f"Response: {response_text}\n"
                    f"Review Score: {score}\n"
                    f"Review Comment: {review_justification}\n"
                    f"Feedback submitted: {result['txHash']}"
                )

            return (
                f"Response: {response_text}\n"
                "Feedback: Unable to process response structure"
            )

        except Exception as e:
            logger.error(
                f"Error executing and reviewing request to {agent_card.name}: {e}"
            )
            return f"Error: {str(e)}"

    agent_name_safe = agent_card.name.replace(" ", "_").replace("-", "_")
    return dspy.Tool(
        func=execute_and_review,
        name=f"execute_and_review_request_to_{agent_name_safe}",
        desc=(
            f"Executes a request to the agent '{agent_card.name}' and submits "
            f"on-chain feedback. {_agent_summary_from_agent_card(agent_card)}"
        ),
    )
