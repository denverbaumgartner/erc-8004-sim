# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Test external agent tools configuration and functionality."""

import asyncio
import logging
import os
import threading

import pytest

from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.agents.base_server import BaseServer

logger = logging.getLogger(__name__)


class TestExternalAgentTools:
    """Test suite for external agent tools."""

    @pytest.mark.asyncio
    async def test_configure_external_agent_tools(
        self, base_agent: ChainedAgent, base_agent_01: ChainedAgent
    ) -> None:
        """Test that external agent tools are correctly configured.

        This test verifies that:
        1. Tools are created when peer_agent_ids are configured
        2. The tools are set on the DSPy agent
        """
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Set the URL BEFORE registering (so it's registered with the correct URL)
        test_port = 8003
        test_host = "127.0.0.1"
        base_agent_01.agent_config.agent_card.url = f"http://{test_host}:{test_port}"

        # Register base_agent_01 so it has an agent ID
        logger.info("Registering target agent...")
        base_agent_01.register_agent()
        logger.info(f"Target agent registered with ID: {base_agent_01.agent_id}")

        server = BaseServer(base_agent_01, host=test_host, port=test_port)

        def run_server():
            server.run()

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
            # Configure base_agent with base_agent_01 as a peer
            if not base_agent.agent_config.dspy_config:
                pytest.skip("No DSPy config for base_agent")

            # Clear any existing peer configuration from previous tests
            base_agent.agent_config.dspy_config.peer_agent_ids = []
            base_agent.agent_config.dspy_config.peer_agent_uris = []

            # Add peer agent URI
            peer_uri = f"http://{test_host}:{test_port}"
            base_agent.agent_config.dspy_config.peer_agent_uris = [peer_uri]

            # Verify no tools before configuration
            if base_agent.dspy_agent:
                initial_tools = (
                    base_agent.dspy_agent._tools
                    if hasattr(base_agent.dspy_agent, "_tools")
                    else []
                )
                logger.info(f"Initial tools count: {len(initial_tools)}")

            # Configure tools
            logger.info("Configuring external agent tools...")
            await base_agent.configure_dspy_agent_tools()

            # Verify tools were created
            assert base_agent.dspy_agent is not None, "DSPy agent should exist"

            tools = (
                base_agent.dspy_agent._tools
                if hasattr(base_agent.dspy_agent, "_tools")
                else []
            )
            logger.info(f"Tools after configuration: {len(tools)}")

            # Should have 2 tools per peer agent (execute and execute_and_review)
            assert len(tools) >= 2, f"Expected at least 2 tools, got {len(tools)}"

            # Check tool names
            tool_names = [tool.name for tool in tools]
            logger.info(f"Tool names: {tool_names}")

            # Should have both execute_request and execute_and_review tools
            execute_tools = [
                name for name in tool_names if name and "execute_request_to_" in name
            ]
            review_tools = [
                name
                for name in tool_names
                if name and "execute_and_review_request_to_" in name
            ]

            assert (
                len(execute_tools) >= 1
            ), "Should have at least one execute_request tool"
            assert (
                len(review_tools) >= 1
            ), "Should have at least one execute_and_review tool"

            logger.info("✓ External agent tools configured successfully")

        finally:
            # Don't close session-scoped agents - they're shared across tests
            logger.info("Test cleanup complete")

    @pytest.mark.asyncio
    async def test_external_agent_tool_execution(
        self, base_agent: ChainedAgent, base_agent_01: ChainedAgent
    ) -> None:
        """Test that external agent tools can be executed.

        This test verifies that:
        1. Tools can be invoked successfully
        2. The tool returns a response from the target agent
        """
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Set the URL BEFORE registering (so it's registered with the correct URL)
        test_port = 8004
        test_host = "127.0.0.1"
        base_agent_01.agent_config.agent_card.url = f"http://{test_host}:{test_port}"

        # Register base_agent_01 so it has an agent ID
        logger.info("Registering target agent...")
        base_agent_01.register_agent()
        logger.info(f"Target agent registered with ID: {base_agent_01.agent_id}")

        server = BaseServer(base_agent_01, host=test_host, port=test_port)

        def run_server():
            server.run()

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
            # Configure base_agent with base_agent_01 as a peer
            if not base_agent.agent_config.dspy_config:
                pytest.skip("No DSPy config for base_agent")

            # Clear any existing peer configuration from previous tests
            base_agent.agent_config.dspy_config.peer_agent_ids = []
            base_agent.agent_config.dspy_config.peer_agent_uris = []

            peer_uri = f"http://{test_host}:{test_port}"
            base_agent.agent_config.dspy_config.peer_agent_uris = [peer_uri]

            # Configure tools
            logger.info("Configuring external agent tools...")
            await base_agent.configure_dspy_agent_tools()

            # Get the execute_request tool
            assert base_agent.dspy_agent is not None
            tools = (
                base_agent.dspy_agent._tools
                if hasattr(base_agent.dspy_agent, "_tools")
                else []
            )
            execute_tool = None
            for tool in tools:
                if (
                    tool.name
                    and "execute_request_to_" in tool.name
                    and "review" not in tool.name
                ):
                    execute_tool = tool
                    break

            assert execute_tool is not None, "execute_request tool not found"

            # Execute the tool
            logger.info(f"Executing tool: {execute_tool.name}")
            result = await execute_tool.func(prompt="hello")

            logger.info(f"Tool result: {result}")

            # Verify we got a response
            assert result is not None, "Tool should return a result"
            assert isinstance(result, str), "Tool result should be a string"
            assert len(result) > 0, "Tool result should not be empty"
            assert "Error" not in result, f"Tool execution failed: {result}"

            logger.info("✓ External agent tool executed successfully")

        finally:
            # Don't close session-scoped agents - they're shared across tests
            logger.info("Test cleanup complete")

    @pytest.mark.asyncio
    async def test_external_agent_review_tool_execution(
        self, base_agent: ChainedAgent, base_agent_01: ChainedAgent
    ) -> None:
        """Test that external agent review tools can execute and submit feedback.

        This test verifies that:
        1. Review tools can be invoked successfully
        2. The tool returns a response from the target agent
        3. On-chain feedback is submitted successfully
        """
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Set the URL BEFORE registering (so it's registered with the correct URL)
        test_port = 8005
        test_host = "127.0.0.1"
        base_agent_01.agent_config.agent_card.url = f"http://{test_host}:{test_port}"

        # Register both agents so they have agent IDs
        logger.info("Registering target agent...")
        base_agent_01.register_agent()
        logger.info(f"Target agent registered with ID: {base_agent_01.agent_id}")

        logger.info("Registering source agent...")
        base_agent.register_agent()
        logger.info(f"Source agent registered with ID: {base_agent.agent_id}")

        server = BaseServer(base_agent_01, host=test_host, port=test_port)

        def run_server():
            server.run()

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
            # Configure base_agent with base_agent_01 as a peer using agent ID
            if not base_agent.agent_config.dspy_config:
                pytest.skip("No DSPy config for base_agent")

            # Clear any existing peer configuration from previous tests
            base_agent.agent_config.dspy_config.peer_agent_ids = []
            base_agent.agent_config.dspy_config.peer_agent_uris = []

            # Use peer_agent_ids to ensure we have the agent_id for feedback
            base_agent.agent_config.dspy_config.peer_agent_ids = [  # type: ignore[misc]
                base_agent_01.agent_id
            ]

            # Configure tools
            logger.info("Configuring external agent tools...")
            await base_agent.configure_dspy_agent_tools()

            # Get the review tool
            assert base_agent.dspy_agent is not None
            tools = (
                base_agent.dspy_agent._tools
                if hasattr(base_agent.dspy_agent, "_tools")
                else []
            )
            review_tool = None
            for tool in tools:
                if tool.name and "execute_and_review_request_to_" in tool.name:
                    review_tool = tool
                    break

            assert review_tool is not None, "execute_and_review tool not found"

            # Execute the review tool
            logger.info(f"Executing review tool: {review_tool.name}")
            result = await review_tool.func(
                prompt="What is 2+2?",
                review_comment=(
                    "Evaluate if the response correctly answers the math " "question."
                ),
            )

            logger.info(f"Review tool result: {result}")

            # Verify we got a response
            assert result is not None, "Review tool should return a result"
            assert isinstance(result, str), "Review tool result should be a string"
            assert len(result) > 0, "Review tool result should not be empty"

            # Check that feedback was submitted
            assert "Response:" in result, "Result should contain agent response"
            assert (
                "Feedback submitted:" in result or "Feedback:" in result
            ), "Result should contain feedback status"

            # Verify LM review was performed
            assert (
                "Review Score:" in result
            ), "Result should contain LM-generated review score"
            assert (
                "Review Comment:" in result
            ), "Result should contain LM-generated review comment"

            # If feedback was submitted, verify the transaction hash is present
            if "Feedback submitted:" in result:
                # Extract the part after "Feedback submitted:"
                feedback_part = result.split("Feedback submitted:")[1].strip()
                # Check that we have a transaction hash (valid hex string,
                # with or without 0x prefix)
                # Remove 0x prefix if present for validation
                tx_hash = (
                    feedback_part[2:]
                    if feedback_part.startswith("0x")
                    else feedback_part
                )
                assert (
                    len(tx_hash) == 64
                ), f"Expected 64-char hex string, got length {len(tx_hash)}"
                assert all(
                    c in "0123456789abcdefABCDEF" for c in tx_hash
                ), f"Invalid hex in transaction hash: {tx_hash}"
                logger.info(
                    f"✓ Feedback submitted successfully with txn: {feedback_part}"
                )

                # Extract the LM-generated score from the result
                score_line = [
                    line for line in result.split("\n") if "Review Score:" in line
                ][0]
                lm_score = int(
                    score_line.split("Review Score:")[1].split("\n")[0].strip()
                )
                logger.info(f"LM-generated score: {lm_score}")

                # Verify that the feedback was submitted successfully
                assert base_agent_01.agent_id is not None
                client_address = base_agent.client.get_address()
                assert client_address is not None
                feedback = base_agent.client.reputation.read_feedback(
                    base_agent_01.agent_id, client_address, 1
                )
                assert feedback is not None, "Feedback should be present"
                assert (
                    feedback["score"] == lm_score
                ), f"Feedback score should be {lm_score} (LM-generated)"
                assert (
                    0 <= feedback["score"] <= 100
                ), "Feedback score should be between 0 and 100"
                assert feedback["isRevoked"] is False, "Feedback should not be revoked"
                logger.info(f"✓ Feedback verified successfully: {feedback}")
            else:
                logger.warning(f"Feedback not submitted: {result}")

            logger.info("✓ External agent review tool executed successfully")

        finally:
            # Don't close session-scoped agents - they're shared across tests
            logger.info("Test cleanup complete")
