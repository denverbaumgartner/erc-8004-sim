# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""Base executor for A2A agent execution."""

import asyncio
import logging
import uuid
from pathlib import Path

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, TextPart

from erc_8004_local_agents.agents.base import ChainedAgent

logger = logging.getLogger(__name__)

# Create a separate debug log file for server request processing
_debug_log_file = Path("server_requests.log")


def _log_to_file(message: str):
    """Write directly to file to ensure we see server activity."""
    try:
        with open(_debug_log_file, "a") as f:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            f.write(f"{timestamp} - {message}\n")
            f.flush()
    except Exception:
        pass


class BaseExecutor(AgentExecutor):
    """Executor that runs ChainedAgent.process_request for A2A requests."""

    def __init__(self, agent: ChainedAgent):
        """Initialize the executor with a ChainedAgent.

        Args:
            agent: ChainedAgent instance to execute requests
        """
        self.agent = agent
        logger.info(
            f"BaseExecutor initialized with agent: {agent.agent_config.agent_card.name}"
        )

    async def execute(self, context: RequestContext, queue: EventQueue) -> None:
        """Execute the agent request and send response to queue.

        Args:
            context: Request context containing input message
            queue: Event queue to send response
        """
        _log_to_file(
            f"[EXECUTE START] Agent: "
            f"{self.agent.agent_config.agent_card.name}, "
            f"Task: {context.task_id}"
        )
        logger.info(f"Executing request for task: {context.task_id}")

        # Extract input from the message
        if not context.message:
            logger.error("No message in context")
            return

        # Extract text from message parts
        input_text = ""
        if hasattr(context.message, "parts") and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, "text"):
                    input_text += part.text  # type: ignore[attr-defined]
                elif hasattr(part, "root") and hasattr(part.root, "text"):
                    input_text += part.root.text  # type: ignore[attr-defined]

        logger.debug(f"Processing input: {input_text[:100]}...")

        # Extract input_address from message metadata if present
        input_address = None
        if hasattr(context.message, "metadata") and context.message.metadata:
            input_address = context.message.metadata.get("input_address")
        if input_address:
            logger.debug(f"Input address: {input_address}")

        # Update status to show processing
        if input_address:
            self.agent.current_status = f"Responding to {input_address[:10]}..."
            _log_to_file(
                f"[STATUS SET] {self.agent.agent_config.agent_card.name}: "
                f"Responding to {input_address[:10]}..."
            )
            logger.info(
                f"[STATUS] Set agent status to: Responding to {input_address[:10]}..."
            )
        else:
            self.agent.current_status = "Processing request"
            _log_to_file(
                "[STATUS SET] "
                f"{self.agent.agent_config.agent_card.name}: "
                "Processing request"
            )
            logger.info("[STATUS] Set agent status to: Processing request")

        # Process request through ChainedAgent in a thread pool
        # (DSPy agent is synchronous and does blocking I/O)
        agent_response = await asyncio.to_thread(
            self.agent.process_request, input=input_text, input_address=input_address
        )

        logger.debug(f"Agent output: {agent_response.output[:100]}...")

        # Create response message with feedback_auth if present
        text_part = TextPart(text=agent_response.output)
        message_data = {
            "messageId": str(uuid.uuid4()),
            "role": "agent",
            "parts": [text_part],
        }

        # Add feedback_auth to message metadata if present
        if agent_response.feedback_auth:
            message_data["metadata"] = {"feedback_auth": agent_response.feedback_auth}
            logger.debug("Added feedback_auth to response message metadata")

        response_message = Message(**message_data)

        # Enqueue the response event
        await queue.enqueue_event(response_message)

        # Set back to idle after sending response (keeps status visible longer)
        self.agent.current_status = "Idle"
        _log_to_file(
            "[STATUS RESET] " f"{self.agent.agent_config.agent_card.name}: Idle"
        )
        logger.info("[STATUS] Reset agent status to: Idle")

        _log_to_file(
            f"[EXECUTE COMPLETE] Agent: "
            f"{self.agent.agent_config.agent_card.name}, "
            f"Task: {context.task_id}"
        )
        logger.info("Request execution completed")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the executing task.

        Args:
            context: Request context for the task to cancel
            event_queue: Event queue for the task

        Note:
            Currently a no-op as ChainedAgent doesn't support cancellation.
        """
        logger.info(f"Cancel requested for task: {context.task_id}")
        logger.warning("Task cancellation not implemented - tasks run to completion")
