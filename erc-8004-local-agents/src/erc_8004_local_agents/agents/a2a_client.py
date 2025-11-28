# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4

# external packages
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class A2AClientWrapper:
    """Wrapper around A2AClient that simplifies agent-to-agent communication.

    This wrapper handles agent card resolution and provides simplified methods for
    sending messages. It only supports text messages; for file/data parts, use the
    underlying A2AClient directly.
    """

    def __init__(self, endpoint: str, httpx_client: httpx.AsyncClient):
        """Initialize the A2A client wrapper.

        Args:
            endpoint: Base URL of the target agent
            httpx_client: Shared httpx.AsyncClient instance for HTTP requests
        """
        self.endpoint = endpoint
        self.httpx_client = httpx_client
        self._agent_card: Optional[AgentCard] = None
        self._client: Optional[A2AClient] = None

    async def _ensure_initialized(self) -> None:
        """Fetch agent card and initialize A2AClient if not already done."""
        if self._client is not None:
            return

        # Fetch agent card from /.well-known/agent.json
        resolver = A2ACardResolver(
            httpx_client=self.httpx_client,
            base_url=self.endpoint,
        )

        try:
            logger.info(
                f"Fetching agent card from: {self.endpoint}{AGENT_CARD_WELL_KNOWN_PATH}"
            )
            self._agent_card = await resolver.get_agent_card()
            logger.info(f"Successfully fetched agent card for {self.endpoint}")

            # Initialize A2AClient with the agent card
            self._client = A2AClient(
                httpx_client=self.httpx_client,
                agent_card=self._agent_card,
            )
            logger.info("A2AClient initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize A2A client for {self.endpoint}: {e}")
            raise RuntimeError(
                f"Failed to fetch agent card from {self.endpoint}"
            ) from e

    async def send_message(
        self,
        text: str,
        task_id: Optional[str] = None,
        context_id: Optional[str] = None,
        input_address: Optional[str] = None,
    ) -> SendMessageResponse:
        """Send a text message to the agent.

        Args:
            text: Message text content
            task_id: Optional task ID for multi-turn conversations
            context_id: Optional context ID for conversation continuity
            input_address: Optional address of the client sending the message

        Returns:
            SendMessageResponse object containing the agent's response
        """
        await self._ensure_initialized()
        assert self._client is not None

        # Construct message parameters
        message_data: Dict[str, Any] = {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "message_id": uuid4().hex,
        }

        # Add task_id if provided
        if task_id is not None:
            message_data["task_id"] = task_id

        # Add context_id if provided
        if context_id is not None:
            message_data["context_id"] = context_id

        # Add input_address in metadata if provided
        if input_address is not None:
            message_data["metadata"] = {"input_address": input_address}

        # Create request
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=Message(**message_data)),
        )

        # Send message
        response = await self._client.send_message(request)
        return response

    async def send_message_streaming(
        self,
        text: str,
        task_id: Optional[str] = None,
        context_id: Optional[str] = None,
        input_address: Optional[str] = None,
    ) -> AsyncIterator:
        """Send a text message to the agent and stream the response.

        Args:
            text: Message text content
            task_id: Optional task ID for multi-turn conversations
            context_id: Optional context ID for conversation continuity
            input_address: Optional address of the client sending the message

        Returns:
            Async iterator yielding response chunks
        """
        await self._ensure_initialized()
        assert self._client is not None

        # Construct message parameters (same as send_message)
        message_data: Dict[str, Any] = {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "message_id": uuid4().hex,
        }

        # Add task_id if provided
        if task_id is not None:
            message_data["task_id"] = task_id

        # Add context_id if provided
        if context_id is not None:
            message_data["context_id"] = context_id

        # Add input_address in metadata if provided
        if input_address is not None:
            message_data["metadata"] = {"input_address": input_address}

        # Create streaming request
        request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=Message(**message_data)),
        )

        # Return streaming response
        return self._client.send_message_streaming(request)

    @property
    def agent_card(self) -> Optional[AgentCard]:
        """Get the cached agent card, if available."""
        return self._agent_card

    @property
    def client(self) -> Optional[A2AClient]:
        """Get the underlying A2AClient, if initialized."""
        return self._client
