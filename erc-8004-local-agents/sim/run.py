# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env python3
"""Standalone ERC-8004 Agent Simulation Runner.

This script allows running agent simulations without pytest.
"""

import argparse
import asyncio
import logging
import os
import random
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from erc_8004_local_agents.tui import SimulationTUI

import httpx
import polars as pl

from erc_8004_local_agents.data.decoder import process_event_logs
from erc_8004_local_agents.data.evm_export import save_history_to_json
from erc_8004_local_agents.simulation import SimulationEnvironment

logger = logging.getLogger(__name__)
tui_logger = logging.getLogger("simulation.tui")


async def wait_for_server(host: str, port: int, max_retries: int = 20) -> bool:
    """Wait for server to be ready by checking agent card endpoint."""
    for i in range(max_retries):
        try:
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


def _log_simulation_summary(history_file_path: Path, tui_mode: bool = False) -> None:
    """Log summary statistics from simulation event logs.

    Args:
        history_file_path: Path to the saved history JSON file
        tui_mode: If True, also log summary to TUI logger
    """
    try:
        logger.info("\n=== Simulation Post-Processing Summary ===")
        if tui_mode:
            tui_logger.info("")
            tui_logger.info("[bold cyan]=== Simulation Summary ===[/bold cyan]")

        # Process event logs
        event_dfs = process_event_logs(history_file_path)

        # Log overview of event types
        logger.info(f"Successfully processed {len(event_dfs)} event types")
        if tui_mode:
            tui_logger.info(f"Processed {len(event_dfs)} event types")

        for event_name, event_df in event_dfs.items():
            logger.info(f"  - {event_name}: {len(event_df)} events")
            if tui_mode:
                tui_logger.info(f"  • {event_name}: {len(event_df)} events")

        # Analyze NewFeedback events if present
        if "NewFeedback" in event_dfs:
            logger.info("\n--- Feedback Analysis ---")
            if tui_mode:
                tui_logger.info("")
                tui_logger.info("[yellow]Feedback Analysis:[/yellow]")

            feedback_df = event_dfs["NewFeedback"]

            # Total feedback events
            total_feedback = len(feedback_df)
            logger.info(f"Total feedback events: {total_feedback}")
            if tui_mode:
                tui_logger.info(f"Total feedback events: [bold]{total_feedback}[/bold]")

            # Overall average score
            avg_score = feedback_df["score"].mean()
            logger.info(f"Overall average score: {avg_score:.2f}")
            if tui_mode:
                tui_logger.info(f"Overall average score: [bold]{avg_score:.2f}[/bold]")

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

            # Print to console/file (excluding shape line)
            table_str = str(per_agent_stats)
            table_lines = [
                line for line in table_str.split("\n") if not line.startswith("shape:")
            ]
            print("\n".join(table_lines))

            # Also log to TUI if in TUI mode
            if tui_mode:
                tui_logger.info("")
                tui_logger.info("Feedback by agent:")
                # Convert dataframe to string and log each line (excluding shape)
                for line in table_lines:
                    tui_logger.info(f"  {line}")

        logger.info("\n=== Post-Processing Complete ===")

    except Exception as e:
        logger.warning(f"Failed to generate simulation summary: {e}")
        if tui_mode:
            tui_logger.error(f"[red]Failed to generate summary: {e}[/red]")


class SimulationRunner:
    """Manages the lifecycle of an ERC-8004 agent simulation."""

    def __init__(self, args):
        """Initialize the simulation runner.

        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self._env: Optional[SimulationEnvironment] = None
        self.threads = []
        self._history_saved = False  # Track if history has been saved
        self._cleanup_done = False  # Track if cleanup has been performed
        self._shutdown_requested = False  # Track if shutdown was requested

    @property
    def env(self) -> SimulationEnvironment:
        """Return the simulation environment, raising an error if it's not set."""
        if self._env is None:
            raise RuntimeError(
                "Simulation environment accessed before it was initialized."
            )
        return self._env

    async def run(self) -> None:
        """Main entry point to execute the simulation."""
        # Setup logging (TUI mode redirects console logs to file)
        self._setup_logging(tui_mode=self.args.tui)

        # Create and set up the environment
        logger.info("Setting up simulation environment...")
        self._env = SimulationEnvironment(network_config_path=self.args.config)
        self.env.setup()

        try:
            # Execute with or without TUI
            if self.args.tui:
                await self._run_with_tui()
            else:
                await self._execute_simulation()
        finally:
            # Save history and perform cleanup
            await self._save_history()
            await self._cleanup()

    async def _execute_simulation(
        self, tui_app: Optional["SimulationTUI"] = None
    ) -> None:
        """Execute the main simulation logic.

        Args:
            tui_app: Optional TUI app instance for real-time updates

        Replicates the logic from test_simulation_workflow.
        """
        # Start periodic TUI update task if TUI is enabled
        update_task = None
        if tui_app:

            async def periodic_update():
                """Periodically update the TUI with agent status and reputation."""
                while True:
                    try:
                        agents_data = self._get_agents_data()
                        tui_app.update_agents_panel(agents_data)
                    except Exception as e:
                        logger.debug(f"Failed to update TUI: {e}")
                    await asyncio.sleep(0.1)  # Update every 1 second

            update_task = asyncio.create_task(periodic_update())

        try:
            await self._run_simulation_logic()
        finally:
            # Reset all agent statuses to Idle
            self._reset_all_agent_statuses()

            # Trigger one final TUI update to display the Idle status
            if tui_app:
                agents_data = self._get_agents_data()
                tui_app.update_agents_panel(agents_data)
                # Give the TUI a moment to render the update
                await asyncio.sleep(0.5)

            # Cancel the update task when simulation completes
            if update_task:
                update_task.cancel()
                try:
                    await update_task
                except asyncio.CancelledError:
                    pass

    async def _run_simulation_logic(self) -> None:
        """Execute the main simulation logic.

        Separated from _execute_simulation to allow for TUI update task management.
        """
        # Extract components from simulation_env
        agent_factory = self.env.agents
        server_factory = self.env.servers
        local_network_config = self.env.config
        contract_objects = self.env.contract_objects

        assert agent_factory is not None
        assert server_factory is not None
        assert local_network_config is not None

        # Load simulation configuration
        if (
            not local_network_config.simulation
            or not local_network_config.simulation.enabled
        ):
            logger.error("Simulation not enabled in config")
            sys.exit(1)

        simulation_config = local_network_config.simulation
        assert simulation_config is not None

        # Check for API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY not set in environment")
            sys.exit(1)

        logger.info("=== Starting ERC-8004 Simulation ===")
        logger.info(f"Simulation config: {simulation_config}")
        tui_logger.info("[bold green]Starting ERC-8004 Simulation[/bold green]")

        failing_transaction_allowed = simulation_config.failing_transaction_allowed
        sim_agents = simulation_config.agents

        if not sim_agents:
            logger.error("No agents configured for simulation")
            sys.exit(1)

        # Identify all agents involved in the simulation
        all_agent_ids = set()
        for sim_agent_config in sim_agents:
            all_agent_ids.add(sim_agent_config.agent_id)

        # Get all available agent IDs from factory (potential peers)
        available_agent_ids = set(agent_factory.keys())

        # Server agents are all agents except the client agents
        peer_agent_ids = available_agent_ids - all_agent_ids

        logger.info(f"Client agents: {all_agent_ids}")
        logger.info(f"Server agents: {peer_agent_ids}")
        tui_logger.info(
            f"Configured [green]{len(all_agent_ids)}[/green] client agents and [blue]{len(peer_agent_ids)}[/blue] server agents"
        )

        # Setup Phase: Register all agents and start servers for server agents
        # Register all agents (both client and server agents)
        logger.info("Registering all agents...")
        tui_logger.info("[yellow]Registering all agents...[/yellow]")
        for agent_id in available_agent_ids:
            agent = agent_factory[agent_id]["agent"]
            logger.info(
                f"Registering {agent_id} with address: {agent.client.get_address()}"
            )
            agent.register_agent()
            logger.info(f"  Registered {agent_id}")
            tui_logger.info(f"  ✓ Registered [bold]{agent_id}[/bold]")

        # Start servers for server agents
        if peer_agent_ids:
            logger.info("Starting server agent servers...")
            tui_logger.info("[yellow]Starting server agent servers...[/yellow]")
            for peer_id in peer_agent_ids:
                server = server_factory[peer_id]
                thread = threading.Thread(target=server.run, daemon=True)
                thread.start()
                self.threads.append((peer_id, server, thread))
                logger.info(f"  Started server for {peer_id}")
                tui_logger.info(f"  ✓ Started server for [bold]{peer_id}[/bold]")

            # Wait for all servers to be ready
            logger.info("Waiting for servers to be ready...")
            tasks = [
                wait_for_server(server.host, server.port)
                for _, server, _ in self.threads
            ]
            results = await asyncio.gather(*tasks)

            if not all(results):
                logger.error("Not all servers started successfully")
                sys.exit(1)
            logger.info("All server agent servers ready!")
            tui_logger.info(
                "[bold green]✓ All server agent servers ready![/bold green]"
            )

        # Configure client agents with server agents and tools
        for sim_agent_id in all_agent_ids:
            sim_agent = agent_factory[sim_agent_id]["agent"]

            if not sim_agent.agent_config.dspy_config:
                logger.warning(
                    f"No DSPy config for {sim_agent_id}, skipping tool configuration"
                )
                continue

            # Configure server agent IDs
            sim_agent.agent_config.dspy_config.peer_agent_ids = [
                agent_factory[peer_id]["agent"].agent_id for peer_id in peer_agent_ids
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
        tui_logger.info("[bold cyan]=== Starting Simulation Loop ===[/bold cyan]")

        for sim_agent_config in sim_agents:
            agent_id = sim_agent_config.agent_id
            prompt = sim_agent_config.prompt
            loop_count = sim_agent_config.loop_count

            logger.info(f"\n--- Running simulation for {agent_id} ---")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Loop count: {loop_count}")
            tui_logger.info(
                f"[bold magenta]Running simulation for {agent_id}[/bold magenta] ({loop_count} loops)"
            )

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
                tui_logger.info(f"[cyan][{agent_id}][/cyan] Loop {i+1}/{loop_count}")

                try:
                    # Select a random peer agent for this iteration
                    selected_agent_name = ""
                    if peer_agent_names:
                        selected_agent_name = random.choice(peer_agent_names)
                        agent_instruction = f" Use the execute_and_review_request_to_{selected_agent_name.replace(' ', '_').replace('-', '_')} tool to review {selected_agent_name}."
                        # Update status to show which peer agent is being targeted
                        sim_agent.current_status = (
                            f"Executing task with {selected_agent_name}"
                        )
                    else:
                        agent_instruction = ""
                        sim_agent.current_status = "Executing task"

                    # Execute workflow
                    augmented_prompt = (
                        f"Loop {i+1}/{loop_count}: {prompt}{agent_instruction}"
                    )
                    logger.info(f"  Executing: {augmented_prompt}")
                    if peer_agent_names and selected_agent_name:
                        tui_logger.info(
                            f"  Executing agent task with server: [bold]{selected_agent_name}[/bold]"
                        )

                    # Track feedback counts before execution
                    feedback_counts_before = {}
                    for peer_id in peer_agent_ids:
                        peer_agent = agent_factory[peer_id]["agent"]
                        all_feedback = sim_agent.client.reputation.read_all_feedback(
                            peer_agent.agent_id
                        )
                        feedback_counts_before[peer_id] = len(
                            all_feedback.get("scores", [])
                        )

                    result = await sim_agent.dspy_agent.aforward(input=augmented_prompt)

                    # Set status back to idle after execution
                    sim_agent.current_status = "Idle"

                    logger.info(
                        f"  Result: {result.output if hasattr(result, 'output') else result}"
                    )
                    tui_logger.info(f"  ✓ Task execution completed")

                    # Verify outcome - check for feedback submission
                    sim_agent.current_status = "Verifying feedback"
                    await asyncio.sleep(0.5)  # Give blockchain time to finalize

                    # Check if feedback was submitted to any peer agent
                    feedback_found = False
                    for peer_id in peer_agent_ids:
                        peer_agent = agent_factory[peer_id]["agent"]
                        all_feedback = sim_agent.client.reputation.read_all_feedback(
                            peer_agent.agent_id
                        )
                        scores = all_feedback.get("scores", [])
                        count_after = len(scores)
                        count_before = feedback_counts_before[peer_id]

                        # Check if new feedback was added to this peer
                        if count_after > count_before:
                            feedback_found = True
                            # Get the newly submitted score(s)
                            new_scores = scores[count_before:]
                            latest_score = new_scores[-1]  # Most recent new score

                            logger.info(f"  ✓ Feedback submitted to {peer_id}")
                            logger.info(f"    Total feedback count: {count_after}")
                            logger.info(f"    Latest scores: {scores[-3:]}")
                            tui_logger.info(
                                f"  [green]✓ Feedback submitted to {peer_id}[/green] (score: {latest_score})"
                            )
                            break

                    sim_agent.current_status = "Idle"

                    if feedback_found:
                        logger.info(f"  ✓ Verification PASSED for loop {i+1}")
                        tui_logger.info(
                            f"  [bold green]✓ Verification PASSED[/bold green]"
                        )
                    else:
                        if failing_transaction_allowed:
                            logger.warning(
                                f"  ⚠ Verification FAILED for loop {i+1} (allowed)"
                            )
                            tui_logger.warning(
                                f"  [yellow]⚠ Verification FAILED (allowed)[/yellow]"
                            )
                        else:
                            raise AssertionError(
                                f"Verification FAILED: No feedback found for loop {i+1}"
                            )

                except Exception as e:
                    logger.error(f"  ✗ Error in loop {i+1}: {e}")
                    tui_logger.error(
                        f"  [red]✗ Error in loop {i+1}:[/red] {str(e)[:100]}"
                    )
                    if not failing_transaction_allowed:
                        raise
                    logger.warning(
                        f"  ⚠ Continuing despite error (failing_transaction_allowed=True)"
                    )
                    tui_logger.warning(f"  [yellow]⚠ Continuing despite error[/yellow]")

            # Reset status to Idle after all loops complete
            sim_agent.current_status = "Idle"

            logger.info(f"\n--- Completed simulation for {agent_id} ---")
            tui_logger.info(
                f"[bold green]✓ Completed simulation for {agent_id}[/bold green]"
            )

        logger.info("\n=== Simulation Complete ===")
        tui_logger.info("[bold cyan]=== Simulation Complete ===[/bold cyan]")

    async def _run_with_tui(self) -> None:
        """Run the simulation with the Textual TUI enabled."""
        from erc_8004_local_agents.tui import SimulationTUI

        # Format agent information for the agents panel
        agents_info = self._format_agents_info()

        # Create callback for post-simulation summary generation
        async def generate_summary():
            """Generate and display summary in TUI."""
            await self._save_history(tui_mode=True)

        # Store reference to app for updates during simulation
        app_holder = {"app": None}

        # Wrapper that passes the TUI app to _execute_simulation
        async def simulation_with_tui():
            await self._execute_simulation(tui_app=app_holder["app"])

        # Create the TUI app with the simulation coroutine and callback
        app = SimulationTUI(
            agents_info,
            simulation_coro=simulation_with_tui,
            post_simulation_callback=generate_summary,
        )

        # Store app reference for use in simulation
        app_holder["app"] = app  # type: ignore[assignment]

        # Run the app (blocks until app.exit() is called)
        # The app will set up logging and run the simulation as a worker
        await app.run_async()

    def _get_agent_reputation(self, agent) -> int:
        """Get the average reputation score for an agent.

        Args:
            agent: ChainedAgent instance

        Returns:
            Average reputation score, or 0 if no feedback exists
        """
        # agent.agent_id should be the numeric on-chain registry ID, not the config string ID
        if not hasattr(agent, "agent_id") or agent.agent_id is None:
            return 0

        try:
            # Use get_summary to get the average score directly from the contract
            # agent.agent_id must be the numeric on-chain ID from the IdentityRegistry
            summary = agent.client.reputation.get_summary(agent.agent_id)
            avg_score = summary.get("averageScore", 0)

            # Debug logging to track reputation reads
            if avg_score > 0:
                logger.debug(
                    f"[REPUTATION] Agent ID {agent.agent_id}: avg_score={avg_score}, count={summary.get('count', 0)}"
                )

            return avg_score

        except Exception as e:
            logger.debug(f"Failed to get reputation for agent {agent.agent_id}: {e}")
            return 0

    def _get_agents_data(self) -> dict:
        """Get current status and reputation for all agents.

        Returns:
            Dictionary mapping agent_id to agent data (status, reputation, address, role)
        """
        if self._env is None or not self._env.agents:
            return {}

        # Get simulation config to identify sim agents vs peers
        simulation_config = self.env.config.simulation
        sim_agent_ids = set()
        if simulation_config and simulation_config.agents:
            sim_agent_ids = {a.agent_id for a in simulation_config.agents}

        agents_data = {}
        for agent_config_id, agent_dict in self.env.agents.items():
            agent = agent_dict["agent"]
            address = agent.client.get_address() if hasattr(agent, "client") else "N/A"
            current_status = agent.current_status

            # Get the on-chain registry ID (numeric)
            on_chain_agent_id = agent.agent_id if hasattr(agent, "agent_id") else None

            reputation = self._get_agent_reputation(agent)

            agents_data[agent_config_id] = {
                "status": current_status,
                "reputation": reputation,
                "address": address,
                "role": "simulation" if agent_config_id in sim_agent_ids else "peer",
                "on_chain_id": on_chain_agent_id,  # Include for debugging
            }

            # Debug logging to track agent ID mapping
            logger.debug(
                f"[AGENT DATA] Config ID: {agent_config_id}, On-chain ID: {on_chain_agent_id}, Reputation: {reputation}"
            )

            # Debug logging to track status reads (only log non-Idle statuses)
            if current_status != "Idle":
                logger.info(f"[STATUS READ] {agent_config_id}: {current_status}")

        return agents_data

    def _reset_all_agent_statuses(self) -> None:
        """Reset all agent statuses to Idle.

        This is called at the end of the simulation to ensure all agents
        display as Idle in the TUI.
        """
        if self._env is None or not self._env.agents:
            return

        logger.info("Resetting all agent statuses to Idle...")
        for agent_id, agent_dict in self.env.agents.items():
            agent = agent_dict["agent"]
            if hasattr(agent, "current_status"):
                agent.current_status = "Idle"
                logger.debug(f"  Reset {agent_id} status to Idle")

    def _format_agents_info(self) -> str:
        """Format agent information for display in the TUI.

        Returns:
            Formatted string containing agent information
        """
        if self._env is None or not self._env.agents:
            return "[yellow]No agents configured[/yellow]"

        lines = []
        lines.append("[bold cyan]ERC-8004 Simulation[/bold cyan]")
        lines.append("")

        # Get simulation config to identify sim agents vs peers
        simulation_config = self.env.config.simulation
        sim_agent_ids = set()
        if simulation_config and simulation_config.agents:
            sim_agent_ids = {a.agent_id for a in simulation_config.agents}

        # List all agents
        for agent_id, agent_data in self.env.agents.items():
            agent = agent_data["agent"]
            address = agent.client.get_address() if hasattr(agent, "client") else "N/A"

            # Determine role
            if agent_id in sim_agent_ids:
                role = "[green]Client Agent[/green]"
            else:
                role = "[blue]Server Agent[/blue]"

            lines.append(f"[bold]{agent_id}[/bold]")
            lines.append(f"  Role: {role}")
            lines.append(f"  Address: [dim]{address[:10]}...[/dim]")
            lines.append("")

        return "\n".join(lines)

    async def _save_history(self, tui_mode: bool = False) -> None:
        """Save transaction history to JSON file if enabled.

        Args:
            tui_mode: If True, logs summary to TUI logger as well
        """
        if self._env is None:
            return

        # Skip if already saved
        if self._history_saved:
            return

        simulation_config = self.env.config.simulation

        # Check if history saving is disabled via command-line flag
        if self.args.no_history:
            logger.info("History saving disabled via --no-history flag")
            return

        # Check if history saving is enabled in config
        if not simulation_config or not simulation_config.save_history:
            logger.info("History saving not enabled in config")
            return

        logger.info("\nSaving transaction history...")
        try:
            # Determine history file path
            if self.args.history_file:
                # Use command-line provided path
                history_file_path = Path(self.args.history_file)
                base_name = history_file_path.stem
            else:
                # Get filename from config and ensure it's saved to pyevm_export directory
                history_filename = simulation_config.save_history_file
                history_file_path = Path("pyevm_export") / history_filename
                base_name = Path(history_filename).stem

            # Ensure pyevm_export directory exists
            history_file_path.parent.mkdir(parents=True, exist_ok=True)

            save_history_to_json(
                base_name,
                self.env.provider,
                self.env.contract_objects,
            )
            logger.info(f"Transaction history saved to {history_file_path}")

            # Log simulation summary
            _log_simulation_summary(history_file_path, tui_mode=tui_mode)

            # Mark as saved to prevent duplicate calls
            self._history_saved = True

        except Exception as e:
            logger.warning(f"Failed to save/process transaction history: {e}")

    async def _cleanup(self) -> None:
        """Gracefully shut down servers and clean up resources."""
        if self._cleanup_done:
            return

        if self._env is None:
            self._cleanup_done = True
            return

        agent_factory = self.env.agents
        assert agent_factory is not None

        logger.info("\nCleaning up agents...")
        for agent_id in agent_factory.keys():
            try:
                agent = agent_factory[agent_id]["agent"]
                await agent.close()
                logger.info(f"  Closed {agent_id}")
            except Exception as e:
                logger.warning(f"  Error closing {agent_id}: {e}")

        self._cleanup_done = True
        logger.info("Cleanup complete")

    def _setup_logging(self, tui_mode: bool = False) -> None:
        """Configure logging based on command-line arguments.

        Args:
            tui_mode: If True, redirects console logs to a file to avoid interfering with TUI
        """
        log_level = getattr(logging, self.args.log_level.upper())

        if tui_mode:
            # In TUI mode, redirect console logs to a file to avoid breaking the TUI
            log_file = Path("simulation.log")
            handlers = [logging.FileHandler(log_file, mode="w")]
        else:
            # Normal mode: log to stdout
            handlers = [logging.StreamHandler(sys.stdout)]

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
            force=True,  # Force reconfiguration if already configured
        )

        # Set level for application loggers
        logging.getLogger("erc_8004_local_agents").setLevel(log_level)
        logging.getLogger(__name__).setLevel(log_level)

        if tui_mode:
            logger.info(f"TUI mode enabled: Console logs redirected to simulation.log")


async def main():
    """Parse arguments and execute the simulation runner."""

    parser = argparse.ArgumentParser(
        description="ERC-8004 Agent Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sim/run.py
  python sim/run.py --config configs/my_scenario.yaml
  python sim/run.py --log-level DEBUG
  python sim/run.py --no-history
  python sim/run.py --history-file my_history.json
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/local_network.yaml",
        help="Path to the main network configuration YAML file (default: configs/local_network.yaml)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM provider (overrides OPENROUTER_API_KEY environment variable)",
    )

    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable saving transaction history to JSON file",
    )

    parser.add_argument(
        "--history-file",
        type=str,
        default=None,
        help="Path to save the simulation history JSON file (overrides config)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "--tui",
        action="store_true",
        help="Enable the Textual TUI for simulation monitoring",
    )

    args = parser.parse_args()

    # Set environment variable if API key provided
    if args.api_key:
        os.environ["OPENROUTER_API_KEY"] = args.api_key

    # log out the arguments
    logger.info(f"Arguments: {args}")
    logger.info(f"History file: {args.history_file}")
    logger.info(f"Log level: {args.log_level}")
    logger.info(f"TUI: {args.tui}")
    logger.info(f"No history: {args.no_history}")
    logger.info(f"Config: {args.config}")

    # Create and run the simulation
    runner = SimulationRunner(args)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
