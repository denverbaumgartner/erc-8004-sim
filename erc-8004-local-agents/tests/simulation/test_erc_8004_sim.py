# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""Test ERC-8004 agent simulation workflow."""

# system packages
import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict

# external packages
import polars as pl
import pytest

# internal packages
from erc_8004_local_agents.data.decoder import process_event_logs
from erc_8004_local_agents.data.evm_export import save_history_to_json

# logging
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


def _log_simulation_summary(history_file_path: Path) -> None:
    """Log summary statistics from simulation event logs.

    Args:
        history_file_path: Path to the saved history JSON file
    """
    try:
        logger.info("\n=== Simulation Post-Processing Summary ===")

        # Process event logs
        event_dfs = process_event_logs(history_file_path)

        # Log overview of event types
        logger.info(f"Successfully processed {len(event_dfs)} event types")
        for event_name, event_df in event_dfs.items():
            logger.info(f"  - {event_name}: {len(event_df)} events")

        # Analyze NewFeedback events if present
        if "NewFeedback" in event_dfs:
            logger.info("\n--- Feedback Analysis ---")
            feedback_df = event_dfs["NewFeedback"]

            # Total feedback events
            total_feedback = len(feedback_df)
            logger.info(f"Total feedback events: {total_feedback}")

            # Overall average score
            avg_score = feedback_df["score"].mean()
            logger.info(f"Overall average score: {avg_score:.2f}")

            # Per-agent feedback statistics
            logger.info("Feedback by agent:")
            per_agent_stats = (
                feedback_df.group_by("agentId")
                .agg(
                    [
                        pl.count("score").alias("feedback_count"),
                        pl.mean("score").alias("avg_score"),
                    ]
                )
                .sort("agentId")
            )
            print(per_agent_stats)

        logger.info("\n=== Post-Processing Complete ===")

    except Exception as e:
        logger.warning(f"Failed to generate simulation summary: {e}")


class TestERC8004Simulation:
    """Test suite for ERC-8004 agent simulation."""

    @pytest.mark.asyncio
    async def test_simulation_workflow(
        self,
        agent_factory: Dict[str, Any],
        server_factory: Dict[str, Any],
        local_network_config: Any,
        ethereum_tester_provider,  # : EthereumTesterProvider,
        contract_objects,  #: Dict[str, Any],
    ) -> None:
        """Test multi-turn simulation of agent interactions.

        This test runs a simulation based on the configuration in local_network.yaml.
        For each agent specified in the simulation config:
        1. Runs their prompt loop_count times
        2. Verifies outcomes (if failing_transaction_allowed is False)
        3. Logs results for each iteration

        Args:
            agent_factory: Agent factory with all instantiated agents
            server_factory: Server factory with all agent servers
            local_network_config: Network configuration with simulation settings
        """
        # Load simulation configuration
        if (
            not local_network_config.simulation
            or not local_network_config.simulation.enabled
        ):
            pytest.skip("Simulation not enabled in config")

        simulation_config = local_network_config.simulation

        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        logger.info("=== Starting ERC-8004 Simulation ===")
        logger.info(f"Simulation config: {simulation_config}")

        failing_transaction_allowed = simulation_config.failing_transaction_allowed
        sim_agents = simulation_config.agents

        if not sim_agents:
            pytest.skip("No agents configured for simulation")

        # Identify all agents involved in the simulation
        all_agent_ids = set()
        for sim_agent_config in sim_agents:
            all_agent_ids.add(sim_agent_config.agent_id)

        # Get all available agent IDs from factory (potential peers)
        available_agent_ids = set(agent_factory.keys())

        # Peer agents are all agents except the simulation agents
        peer_agent_ids = available_agent_ids - all_agent_ids

        logger.info(f"Simulation agents: {all_agent_ids}")
        logger.info(f"Peer agents: {peer_agent_ids}")

        # Setup Phase: Register all agents and start servers for peers
        try:
            # Register all agents (both sim agents and peers)
            logger.info("Registering all agents...")
            for agent_id in available_agent_ids:
                agent = agent_factory[agent_id]["agent"]
                logger.info(
                    f"Registering {agent_id} with address: {agent.client.get_address()}"
                )
                agent.register_agent()
                logger.info(f"  Registered {agent_id}")

            # Start servers for peer agents
            threads = []
            if peer_agent_ids:
                logger.info("Starting peer agent servers...")
                for peer_id in peer_agent_ids:
                    server = server_factory[peer_id]
                    thread = threading.Thread(target=server.run, daemon=True)
                    thread.start()
                    threads.append((peer_id, server, thread))
                    logger.info(f"  Started server for {peer_id}")

                # Wait for all servers to be ready
                logger.info("Waiting for servers to be ready...")
                tasks = [
                    wait_for_server(server.host, server.port)
                    for _, server, _ in threads
                ]
                results = await asyncio.gather(*tasks)

                if not all(results):
                    pytest.fail("Not all servers started successfully")
                logger.info("All peer servers ready!")

            # Configure simulation agents with peer agents and tools
            for sim_agent_id in all_agent_ids:
                sim_agent = agent_factory[sim_agent_id]["agent"]

                if not sim_agent.agent_config.dspy_config:
                    logger.warning(
                        f"No DSPy config for {sim_agent_id}, skipping tool "
                        "configuration"
                    )
                    continue

                # Configure peer agent IDs
                sim_agent.agent_config.dspy_config.peer_agent_ids = [
                    agent_factory[peer_id]["agent"].agent_id
                    for peer_id in peer_agent_ids
                ]

                # Configure tools
                logger.info(f"Configuring tools for {sim_agent_id}...")
                await sim_agent.configure_dspy_agent_tools()

                # Log configured tools
                tools = (
                    sim_agent.dspy_agent._tools
                    if hasattr(sim_agent.dspy_agent, "_tools")
                    else []
                )
                tool_names = [tool.name for tool in tools]
                logger.info(f"  {sim_agent_id} has {len(tools)} tools: {tool_names}")

            # Simulation Loop
            logger.info("\n=== Starting Simulation Loop ===")

            for sim_agent_config in sim_agents:
                agent_id = sim_agent_config.agent_id
                prompt = sim_agent_config.prompt
                loop_count = sim_agent_config.loop_count

                logger.info(f"\n--- Running simulation for {agent_id} ---")
                logger.info(f"Prompt: {prompt}")
                logger.info(f"Loop count: {loop_count}")

                sim_agent = agent_factory[agent_id]["agent"]

                # Get list of peer agent names for random selection
                peer_agent_names = []
                for peer_id in peer_agent_ids:
                    peer_agent = agent_factory[peer_id]["agent"]
                    if hasattr(peer_agent, "agent_config") and hasattr(
                        peer_agent.agent_config, "agent_card"
                    ):
                        peer_agent_names.append(peer_agent.agent_config.agent_card.name)

                # Run the loop
                for i in range(loop_count):
                    logger.info(f"\n[{agent_id}] Loop {i+1}/{loop_count}")

                    try:
                        # Select a random peer agent for this iteration
                        import random

                        if peer_agent_names:
                            selected_agent_name = random.choice(peer_agent_names)
                            agent_name_safe = selected_agent_name.replace(
                                " ", "_"
                            ).replace("-", "_")
                            agent_instruction = (
                                f" Use the execute_and_review_request_to_"
                                f"{agent_name_safe} tool to review "
                                f"{selected_agent_name}."
                            )
                        else:
                            agent_instruction = ""

                        # Execute workflow
                        augmented_prompt = (
                            f"Loop {i+1}/{loop_count}: {prompt}{agent_instruction}"
                        )
                        logger.info(f"  Executing: {augmented_prompt}")

                        result = await sim_agent.dspy_agent.aforward(
                            input=augmented_prompt
                        )

                        logger.info(
                            "  Result: "
                            f"{result.output if hasattr(result, 'output') else result}"
                        )

                        # Verify outcome - check for feedback submission
                        await asyncio.sleep(0.5)  # Give blockchain time to finalize

                        # Check if feedback was submitted to any peer agent
                        feedback_found = False
                        for peer_id in peer_agent_ids:
                            peer_agent = agent_factory[peer_id]["agent"]
                            all_feedback = (
                                sim_agent.client.reputation.read_all_feedback(
                                    peer_agent.agent_id
                                )
                            )

                            if len(all_feedback["scores"]) > 0:
                                feedback_found = True
                                logger.info(f"  ✓ Feedback submitted to {peer_id}")
                                logger.info(
                                    "    Total feedback count: "
                                    f"{len(all_feedback['scores'])}"
                                )
                                logger.info(
                                    f"    Latest scores: {all_feedback['scores'][-3:]}"
                                )
                                break

                        if feedback_found:
                            logger.info(f"  ✓ Verification PASSED for loop {i+1}")
                        else:
                            if failing_transaction_allowed:
                                logger.warning(
                                    f"  ⚠ Verification FAILED for loop {i+1} "
                                    "(allowed)"
                                )
                            else:
                                raise AssertionError(
                                    "Verification FAILED: No feedback found for "
                                    f"loop {i+1}"
                                )

                    except Exception as e:
                        logger.error(f"  ✗ Error in loop {i+1}: {e}")
                        if not failing_transaction_allowed:
                            raise
                        logger.warning(
                            "  ⚠ Continuing despite error "
                            "(failing_transaction_allowed=True)"
                        )

                logger.info(f"\n--- Completed simulation for {agent_id} ---")

            logger.info("\n=== Simulation Complete ===")

        finally:
            # Save history to JSON if enabled
            if simulation_config.save_history:
                logger.info("\nSaving transaction history...")
                try:
                    # Get filename from config and ensure it's saved to
                    # pyevm_export directory
                    history_filename = simulation_config.save_history_file
                    history_file_path = Path("pyevm_export") / history_filename

                    # Extract base name without extension for save_history_to_json
                    base_name = Path(history_filename).stem

                    save_history_to_json(
                        base_name,
                        ethereum_tester_provider,
                        contract_objects,
                    )
                    logger.info(f"Transaction history saved to {history_file_path}")

                    # Log simulation summary
                    _log_simulation_summary(history_file_path)

                except Exception as e:
                    logger.warning(f"Failed to save/process transaction history: {e}")

            # Cleanup
            logger.info("\nCleaning up agents...")
            for agent_id in all_agent_ids:
                try:
                    agent = agent_factory[agent_id]["agent"]
                    await agent.close()
                    logger.info(f"  Closed {agent_id}")
                except Exception as e:
                    logger.warning(f"  Error closing {agent_id}: {e}")
            logger.info("Cleanup complete")
