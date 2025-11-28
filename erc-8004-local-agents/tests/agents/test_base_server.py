# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""E2E tests for BaseServer with A2A protocol."""

import asyncio
import logging
import os
import threading
import uuid

import httpx
import pytest
from a2a.client import A2AClient
from a2a.types import Message, MessageSendParams, SendMessageRequest, TextPart

from erc_8004_local_agents.agents.base_server import BaseServer
from erc_8004_local_agents.types.types import AgentConfig

logger = logging.getLogger(__name__)


class TestBaseServer:
    """Test suite for BaseServer A2A integration."""

    @pytest.mark.asyncio
    async def test_base_server_e2e(self) -> None:
        """Test that BaseServer can handle A2A requests end-to-end."""
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Load config and set API key
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "configs",
            "agents",
            "agent_00.yaml",
        )
        config = AgentConfig.from_yaml(config_path)

        # Update API key in config
        if config.dspy_config:
            config.dspy_config.api_key = api_key

        # Test server on a different port to avoid conflicts
        test_port = 8001
        test_host = "127.0.0.1"

        # Create server
        server = BaseServer(config, host=test_host, port=test_port)

        # Function to run server in thread
        def run_server():
            server.run()

        # Start server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait for server to start - check agent card endpoint
        logger.info("Waiting for server to start...")
        max_retries = 10
        for i in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://{test_host}:{test_port}/.well-known/agent-card.json"
                    )
                    if response.status_code == 200:
                        logger.info("Server is ready")
                        break
            except Exception:
                if i == max_retries - 1:
                    pytest.fail("Server failed to start")
                await asyncio.sleep(1)

        try:
            # Create A2A client
            endpoint = f"http://{test_host}:{test_port}"
            logger.info(f"Connecting to agent at {endpoint}")

            # Use longer timeout for LLM API calls
            timeout = httpx.Timeout(30.0, read=60.0)
            async with httpx.AsyncClient(timeout=timeout) as http_client:
                a2a_client = A2AClient(
                    url=endpoint,
                    httpx_client=http_client,
                )

                # Send message to agent
                input_text = "World"
                logger.info(f"Sending message: {input_text}")

                # Create proper message and request object
                text_part = TextPart(text=input_text)
                message = Message(
                    messageId=str(uuid.uuid4()),
                    role="user",
                    parts=[text_part],
                )
                request = SendMessageRequest(
                    id=str(uuid.uuid4()), params=MessageSendParams(message=message)
                )
                response = await a2a_client.send_message(request)

                # Verify response
                assert response is not None
                logger.info(f"Received response: {response}")

                # Check that response contains expected greeting
                response_text = str(response)
                assert (
                    "Hello" in response_text or "hello" in response_text.lower()
                ), f"Expected greeting in response, got: {response_text}"

                logger.info(" E2E test passed successfully")

        finally:
            # Note: Server thread will be cleaned up when test process exits
            # since it's a daemon thread
            logger.info("Test cleanup complete")
