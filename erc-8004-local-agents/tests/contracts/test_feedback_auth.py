# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""E2E tests for feedback_auth in A2A message responses."""

import asyncio
import logging
import os
import threading

import pytest

from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.agents.base_server import BaseServer

logger = logging.getLogger(__name__)


class TestFeedbackAuthE2E:
    """Test suite for feedback_auth in A2A responses."""

    @pytest.mark.asyncio
    async def test_feedback_auth_with_fixtures(
        self, base_agent: ChainedAgent, base_agent_01: ChainedAgent
    ) -> None:
        """Test that feedback_auth is included when sending between agents."""
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Update API keys in both agents
        if base_agent.dspy_agent and base_agent.agent_config.dspy_config:
            base_agent.agent_config.dspy_config.api_key = api_key
        if base_agent_01.dspy_agent and base_agent_01.agent_config.dspy_config:
            base_agent_01.agent_config.dspy_config.api_key = api_key

        # Register the server agent so it can issue feedback_auth tokens
        logger.info("Registering server agent...")
        base_agent_01.register_agent()
        logger.info(f"Server agent registered with ID: {base_agent_01.agent_id}")

        # Test server on specific port
        test_port = 8001
        test_host = "127.0.0.1"

        # Update agent card URL to match where server will actually run
        base_agent_01.agent_config.agent_card.url = f"http://{test_host}:{test_port}"

        # Create server using base_agent_01 instance (preserves agent_id)
        server = BaseServer(base_agent_01, host=test_host, port=test_port)

        # Function to run server in thread
        def run_server():
            server.run()

        # Start server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait for server to start
        logger.info("Waiting for server to start...")
        max_retries = 20
        for i in range(max_retries):
            try:
                import httpx

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
                await asyncio.sleep(0.5)

        try:
            # Send message from base_agent (client) to base_agent_01 (server)
            endpoint = f"http://{test_host}:{test_port}"
            input_text = "Hello"
            logger.info(
                f"Sending message from {base_agent.agent_config.wallet_config.address}"
            )

            response = await base_agent.send_message_to_agent(
                endpoint=endpoint,
                text=input_text,
            )

            # Verify response
            assert response is not None
            logger.info(f"Received response type: {type(response)}")

            # Check for feedback_auth in response message metadata
            feedback_auth = None
            if hasattr(response, "root") and hasattr(response.root, "result"):
                result = response.root.result
                # Check metadata for feedback_auth
                if hasattr(result, "metadata") and result.metadata:
                    feedback_auth = result.metadata.get("feedback_auth")

            if feedback_auth:
                logger.info(f"✓ Received feedback_auth: {feedback_auth}")
                assert isinstance(feedback_auth, str)
                assert feedback_auth.startswith("0x")
                logger.info("✓ feedback_auth validation passed")
            else:
                logger.warning("No feedback_auth in response - this is unexpected")
                # Log the response structure for debugging
                logger.info(f"Response structure: {response}")
                if hasattr(response, "root"):
                    logger.info(f"Response root: {response.root}")
                    if hasattr(response.root, "result"):
                        logger.info(
                            f"Response metadata: {response.root.result.metadata}"
                        )
                pytest.fail("Expected feedback_auth in response but none was found")

            # Clean up
            await base_agent.close()

            logger.info("✓ E2E feedback_auth test passed successfully")

        finally:
            logger.info("Test cleanup complete")
