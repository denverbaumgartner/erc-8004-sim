# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0
"""Test feedback agent functionality."""

import asyncio
import logging
import os
import threading

import pytest

logger = logging.getLogger(__name__)


async def wait_for_server(host: str, port: int, max_retries: int = 20) -> bool:
    """Wait for server to be ready by checking agent card endpoint."""
    for i in range(max_retries):
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{host}:{port}/.well-known/agent-card.json"
                )
                if response.status_code == 200:
                    return True
        except Exception:
            if i == max_retries - 1:
                return False
            await asyncio.sleep(0.5)
    return False


class TestFeedbackAgent:
    """Test suite for feedback agent."""

    @pytest.mark.asyncio
    async def test_feedback_agent_workflow(
        self,
        agent_factory,
        server_factory,
    ) -> None:
        """Test that feedback agent can interact with agents and provide feedback.

        This test verifies the complete workflow:
        1. Feedback agent uses random_number tool to select an agent
        2. Executes a request to the selected agent
        3. Receives feedback authorization string
        4. Submits feedback using give_feedback tool

        Args:
            agent_factory: Agent factory with all instantiated agents
            server_factory: Server factory with all agent servers
        """
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Get agents from factory
        base_agent = agent_factory["agent_00"]["agent"]
        base_agent_01 = agent_factory["agent_01"]["agent"]
        feedback_agent = agent_factory["agent_03"]["agent"]
        logger.info(
            "Feedback agent setup with initial tools: "
            f"{feedback_agent.dspy_agent._tools}"
        )

        # Get servers from factory
        server1 = server_factory["agent_00"]
        server2 = server_factory["agent_01"]

        # Register both target agents
        logger.info("Registering target agents...")
        base_agent.register_agent()
        base_agent_01.register_agent()
        logger.info(
            f"Target agents registered: {base_agent.agent_id}, {base_agent_01.agent_id}"
        )

        # Register feedback agent
        logger.info("Registering feedback agent...")
        feedback_agent.register_agent()
        logger.info(f"Feedback agent registered: {feedback_agent.agent_id}")

        # Start servers in background threads
        logger.info("Starting servers...")
        threads = []
        for server in [server1, server2]:
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            threads.append(thread)

        # Wait for servers to be ready
        logger.info("Waiting for servers to start...")
        tasks = [
            wait_for_server(server1.host, server1.port),
            wait_for_server(server2.host, server2.port),
        ]
        results = await asyncio.gather(*tasks)

        if not all(results):
            pytest.fail("Not all servers started successfully")
        logger.info("Both servers ready!")

        try:
            # Configure feedback agent with peer agents
            if not feedback_agent.agent_config.dspy_config:
                pytest.skip("No DSPy config for feedback agent")

            # Configure peer agent IDs
            feedback_agent.agent_config.dspy_config.peer_agent_ids = [
                base_agent.agent_id,
                base_agent_01.agent_id,
            ]

            # Configure external agent tools
            logger.info("Configuring feedback agent tools...")
            await feedback_agent.configure_dspy_agent_tools()

            # Verify tools were created
            assert feedback_agent.dspy_agent is not None, "DSPy agent should exist"
            tools = (
                feedback_agent.dspy_agent._tools
                if hasattr(feedback_agent.dspy_agent, "_tools")
                else []
            )
            logger.info(f"Feedback agent has {len(tools)} tools configured")

            # Should have: random_number, give_feedback, and 2 execute_request
            # tools per peer
            tool_names = [tool.name for tool in tools]
            logger.info(f"Tool names: {tool_names}")

            assert "random_number" in tool_names, "Should have random_number tool"
            assert "give_feedback" in tool_names, "Should have give_feedback tool"

            execute_tools = [
                name for name in tool_names if "execute_request_to_" in name
            ]
            assert (
                len(execute_tools) >= 2
            ), f"Should have at least 2 execute_request tools, got {len(execute_tools)}"

            # Run the feedback agent
            logger.info("Running feedback agent workflow...")
            num_peers = len(feedback_agent.agent_config.dspy_config.peer_agent_ids)
            result = await feedback_agent.dspy_agent.aforward(
                input=(
                    f"Please select one of the {num_peers} agents and provide "
                    "feedback on their response to: What is 2+2?"
                )
            )

            logger.info(f"Feedback agent result: {result}")

            # Verify we got output
            assert result is not None, "Feedback agent should return a result"
            assert hasattr(result, "output"), "Result should have output field"
            assert len(result.output) > 0, "Result output should not be empty"

            logger.info("Feedback agent workflow completed successfully")
            logger.info(f"Summary: {result.output}")

            # Verify feedback was submitted on-chain
            logger.info("Verifying on-chain feedback submission...")

            # Give the blockchain a moment to finalize the transaction
            await asyncio.sleep(0.5)

            # Check both target agents to see which one received feedback
            feedback_found = False
            for target_agent, target_name in [
                (base_agent, "agent_00"),
                (base_agent_01, "agent_01"),
            ]:
                logger.info(
                    f"Checking feedback for {target_name} "
                    f"(agent_id={target_agent.agent_id})"
                )
                all_feedback = feedback_agent.client.reputation.read_all_feedback(
                    target_agent.agent_id
                )
                logger.info(f"Feedback data for {target_name}: {all_feedback}")

                if len(all_feedback["scores"]) > 0:
                    logger.info(
                        f"Found {len(all_feedback['scores'])} feedback(s) for "
                        f"{target_name}"
                    )
                    logger.info(f"  Scores: {all_feedback['scores']}")
                    feedback_found = True
                    logger.info(f"✓ On-chain feedback verified for {target_name}")
                    break
                else:
                    logger.info(
                        f"No feedback found for {target_name} "
                        f"(agent_id={target_agent.agent_id})"
                    )

            assert (
                feedback_found
            ), "Feedback should have been submitted to at least one agent"

        finally:
            # Clean up
            await feedback_agent.close()
            logger.info("Test cleanup complete")
