"""E2E Agent Arena - Interactive pytest test for comparing agent responses."""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from erc8004 import ERC8004Client

from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.data.evm_export import save_history_to_json
from erc_8004_local_agents.simulation import SimulationEnvironment

logger = logging.getLogger(__name__)


async def wait_for_server(host: str, port: int, max_retries: int = 20) -> bool:
    """Wait for server to be ready by checking agent card endpoint.

    Args:
        host: Server host
        port: Server port
        max_retries: Maximum number of retries

    Returns:
        True if server is ready, False otherwise
    """
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


async def send_message_to_agents(
    client_agent: ChainedAgent, endpoint1: str, endpoint2: str, user_input: str
) -> tuple[tuple[str, str, str], tuple[str, str, str]]:
    """Send the same message to both agents concurrently using client agent.

    Args:
        client_agent: ChainedAgent to use as client
        endpoint1: Endpoint URL for first agent
        endpoint2: Endpoint URL for second agent
        user_input: User's message

    Returns:
        Tuple of ((message_id1, text1, feedback_auth1),
                  (message_id2, text2, feedback_auth2))
    """
    # Send to both agents concurrently
    responses = await asyncio.gather(
        client_agent.send_message_to_agent(endpoint=endpoint1, text=user_input),
        client_agent.send_message_to_agent(endpoint=endpoint2, text=user_input),
        return_exceptions=True,
    )

    # Extract message_id, text, and feedback_auth from responses
    def extract_response_data(response) -> tuple[str, str, str]:
        if isinstance(response, Exception):
            return ("error", f"Error: {str(response)}", "")

        # Check if it's an error response
        response_str = str(response)
        if "JSONRPCErrorResponse" in response_str:
            error_msg = "Unknown error"
            if hasattr(response, "root") and hasattr(response.root, "error"):
                error_msg = response.root.error.message
            return ("error", f"Error: {error_msg}", "")

        # Extract message_id, text, and feedback_auth from successful response
        try:
            if hasattr(response, "root") and hasattr(response.root, "result"):
                result = response.root.result
                message_id = "unknown"
                feedback_auth = ""

                # Get message_id
                if hasattr(result, "message_id"):
                    message_id = result.message_id

                # Get feedback_auth from metadata
                if hasattr(result, "metadata") and result.metadata:
                    feedback_auth = result.metadata.get("feedback_auth", "")

                # Get text from parts
                if hasattr(result, "parts"):
                    text_parts = []
                    for part in result.parts:
                        if hasattr(part, "text"):
                            text_parts.append(part.text)
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            text_parts.append(part.root.text)
                    if text_parts:
                        return (message_id, " ".join(text_parts), feedback_auth)
        except Exception as e:
            return ("error", f"Error parsing response: {str(e)}", "")

        return ("unknown", str(response), "")

    return extract_response_data(responses[0]), extract_response_data(responses[1])


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")


def print_header():
    """Print the ASCII art header."""
    print(
        r"""
 _____ ____   ____       ___   ___   ___  _  _
| ____|  _ \ / ___|     ( _ ) / _ \ / _ \| || |
|  _| | |_) | |   _____ / _ \| | | | | | | || |_
| |___|  _ <| |__|_____| (_) | |_| | |_| |__   _|
|_____|_| \_\\____|     \___/ \___/ \___/   |_|

    _                    _      _
   / \   __ _  ___ _ __ | |_   / \   _ __ ___ _ __   __ _
  / _ \ / _` |/ _ \ '_ \| __| / _ \ | '__/ _ \ '_ \ / _` |
 / ___ \ (_| |  __/ | | | |_ / ___ \| | |  __/ | | | (_| |
/_/   \_\__, |\___|_| |_|\__/_/   \_\_|  \___|_| |_|\__,_|
        |___/
"""
    )
    print("Type your message and press Enter to send to both agents.")
    print("Type 'exit' or 'quit' to stop.\n")


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap text to fit within specified width.

    Args:
        text: Text to wrap
        width: Maximum width per line

    Returns:
        List of wrapped lines
    """
    if len(text) <= width:
        return [text]

    lines = []
    words = text.split()
    current_line = ""

    for word in words:
        # If adding this word would exceed width
        if current_line and len(current_line) + len(word) + 1 > width:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def print_responses(
    agent1_name: str,
    agent2_name: str,
    resp1: tuple[str, str, str],
    resp2: tuple[str, str, str],
):
    """Print agent responses in a side-by-side table format.

    Args:
        agent1_name: Name of first agent
        agent2_name: Name of second agent
        resp1: Tuple of (message_id, text, feedback_auth) from first agent
        resp2: Tuple of (message_id, text, feedback_auth) from second agent
    """
    col_width = 40
    message_id1, text1, _ = resp1  # Ignore feedback_auth for display
    message_id2, text2, _ = resp2  # Ignore feedback_auth for display

    # Print table header
    print(f"\n| {agent1_name:<{col_width}} | {agent2_name:<{col_width}} |")
    print(f"|{'-' * (col_width + 2)}|{'-' * (col_width + 2)}|")

    # Print message IDs (truncate to fit in column)
    # Show first 8 chars of UUID (like git commit hashes)
    if len(message_id1) > 8:
        id1_display = f"message_id='{message_id1[:8]}...'"
    else:
        id1_display = f"message_id='{message_id1}'"

    if len(message_id2) > 8:
        id2_display = f"message_id='{message_id2[:8]}...'"
    else:
        id2_display = f"message_id='{message_id2}'"

    print(f"| {id1_display:<{col_width}} | {id2_display:<{col_width}} |")
    print(f"|{'-' * (col_width + 2)}|{'-' * (col_width + 2)}|")

    # Print response text (wrap if needed)
    resp1_display = f"{agent1_name} response: {text1}"
    resp2_display = f"{agent2_name} response: {text2}"

    resp1_lines = wrap_text(resp1_display, col_width)
    resp2_lines = wrap_text(resp2_display, col_width)
    max_resp_lines = max(len(resp1_lines), len(resp2_lines))

    # Pad with empty strings if needed
    resp1_lines.extend([""] * (max_resp_lines - len(resp1_lines)))
    resp2_lines.extend([""] * (max_resp_lines - len(resp2_lines)))

    for line1, line2 in zip(resp1_lines, resp2_lines):
        print(f"| {line1:<{col_width}} | {line2:<{col_width}} |")

    print(f"|{'-' * (col_width + 2)}|{'-' * (col_width + 2)}|\n")


def prompt_for_feedback():
    """Prompt the user for feedback and return their choice."""
    print("Which response was better?")
    print("  1. Agent 1")
    print("  2. Agent 2")
    print("  3. Both were about the same")
    print("  4. Both were bad")

    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ["1", "2", "3", "4"]:
                return choice
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D or Ctrl+C gracefully
            return None


def submit_feedback(
    client: ERC8004Client,
    agent1_id: int,
    agent2_id: int,
    feedback_auth1: str,
    feedback_auth2: str,
    feedback_choice: str,
) -> tuple[str, str] | None:
    """Submit feedback based on user's choice.

    Args:
        client: ERC8004Client to use for submitting feedback
        agent1_id: ID of first agent
        agent2_id: ID of second agent
        feedback_auth1: Feedback auth token from first agent
        feedback_auth2: Feedback auth token from second agent
        feedback_choice: User's choice ("1", "2", "3", or "4")

    Returns:
        Tuple of (winner_txn_hash, loser_txn_hash) if feedback submitted, None otherwise
    """
    # Cases 3 and 4: No feedback submission
    if feedback_choice in ["3", "4"]:
        return None

    # Determine winner and loser IDs
    if feedback_choice == "1":
        winner_id = agent1_id
        loser_id = agent2_id
        winner_auth = feedback_auth1
        loser_auth = feedback_auth2
    else:  # feedback_choice == "2"
        winner_id = agent2_id
        loser_id = agent1_id
        winner_auth = feedback_auth2
        loser_auth = feedback_auth1

    try:
        # Submit feedback for winner
        logger.info(f"Submitting feedback for winner (Agent {winner_id})")
        winner_result = client.reputation.give_feedback(
            agent_id=winner_id,
            score=100,
            feedback_auth=winner_auth,
            tag1=str(winner_id),
            tag2=str(loser_id),
            feedback_uri="",
            feedback_hash="",
        )

        # Submit feedback for loser
        logger.info(f"Submitting feedback for loser (Agent {loser_id})")
        loser_result = client.reputation.give_feedback(
            agent_id=loser_id,
            score=0,
            feedback_auth=loser_auth,
            tag1=str(winner_id),
            tag2=str(loser_id),
            feedback_uri="",
            feedback_hash="",
        )

        logger.info("Feedback submitted successfully")

        # Extract transaction hashes (give_feedback returns {"txHash": ...})
        winner_txn = winner_result.get("txHash", "unknown")
        loser_txn = loser_result.get("txHash", "unknown")

        return (winner_txn, loser_txn)
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        print(f"\nError submitting feedback: {e}")
        return None


class TestAgentArenaE2E:
    """Test suite for Agent Arena E2E interactive CLI."""

    @pytest.mark.asyncio
    async def test_agent_arena_interactive(
        self,
        simulation_env: SimulationEnvironment,
    ) -> None:
        """Interactive test comparing responses from two agents side-by-side.

        This test starts two agent servers and uses a third agent as a client
        to send messages and display responses interactively.

        Args:
            simulation_env: Simulation environment with all agents and servers
        """
        # Skip if no API key (agents will have loaded it automatically from env)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Get server and agent references from simulation_env
        servers = simulation_env.servers
        agents = simulation_env.agents
        assert servers is not None
        assert agents is not None

        # Get specific servers and agents by ID
        server1 = servers["agent_00"]
        server2 = servers["agent_01"]
        base_agent_02 = agents["agent_02"]["agent"]

        ethereum_tester_provider = simulation_env.provider
        contract_objects = simulation_env.contract_objects

        # Get agent instances from servers
        base_agent = server1.agent
        base_agent_01 = server2.agent

        # Register agents (needed for feedback_auth)
        logger.info("Registering agents...")
        base_agent.register_agent()
        base_agent_01.register_agent()
        logger.info(
            f"Agents registered: {base_agent.agent_id}, {base_agent_01.agent_id}"
        )

        # Get host and port from servers
        host = server1.host
        port1 = server1.port
        port2 = server2.port

        # Update agent card URLs to match server locations
        base_agent.agent_config.agent_card.url = f"http://{host}:{port1}"
        base_agent_01.agent_config.agent_card.url = f"http://{host}:{port2}"

        # Start servers in background threads
        thread1 = threading.Thread(target=server1.run, daemon=True)
        thread2 = threading.Thread(target=server2.run, daemon=True)
        thread1.start()
        thread2.start()

        # Wait for servers to be ready
        logger.info("Waiting for servers to start...")
        if not await wait_for_server(host, port1):
            pytest.fail("Agent 1 server failed to start")
        if not await wait_for_server(host, port2):
            pytest.fail("Agent 2 server failed to start")
        logger.info("Both servers ready!")

        # Endpoints for agents
        endpoint1 = f"http://{host}:{port1}"
        endpoint2 = f"http://{host}:{port2}"

        # Set up session logging
        log_dir = Path(__file__).parent.parent / "agent_arena_logs"
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"arena_session_{timestamp}.json"
        session_logs = []
        logger.info(f"Session logs will be saved to: {log_file}")

        try:
            # Show initial header
            clear_screen()
            print_header()

            # Main interaction loop
            while True:
                try:
                    user_input = input("user_input: ").strip()

                    if user_input.lower() in ["exit", "quit"]:
                        clear_screen()
                        print("Exiting Agent Arena. Goodbye!")
                        break

                    if not user_input:
                        continue

                    print("\nSending to agents...")

                    # Send to both agents using client agent
                    resp1, resp2 = await send_message_to_agents(
                        base_agent_02, endpoint1, endpoint2, user_input
                    )

                    # Clear screen and show header again
                    clear_screen()
                    print_header()

                    # Display results
                    print_responses("agent_one", "agent_two", resp1, resp2)

                    # Get user feedback
                    feedback = prompt_for_feedback()
                    if feedback is None:
                        # User pressed Ctrl+C or Ctrl+D
                        clear_screen()
                        print("\nExiting Agent Arena. Goodbye!")
                        break

                    # Submit feedback based on user's choice
                    winner_txn = None
                    loser_txn = None
                    if feedback in ["1", "2"]:
                        # Extract feedback_auth tokens from responses
                        _, _, feedback_auth1 = resp1
                        _, _, feedback_auth2 = resp2

                        # Validate feedback_auth tokens are present
                        if not feedback_auth1 or not feedback_auth2:
                            print(
                                "\nWarning: Missing feedback_auth tokens. "
                                "Cannot submit feedback."
                            )
                        else:
                            # Submit feedback using the client agent's ERC8004Client
                            assert base_agent.agent_id is not None
                            assert base_agent_01.agent_id is not None
                            txn_hashes = submit_feedback(
                                client=base_agent_02.client,
                                agent1_id=base_agent.agent_id,
                                agent2_id=base_agent_01.agent_id,
                                feedback_auth1=feedback_auth1,
                                feedback_auth2=feedback_auth2,
                                feedback_choice=feedback,
                            )

                            if txn_hashes:
                                winner_txn, loser_txn = txn_hashes
                                print("\nFeedback submitted successfully!")
                                print("\nTransaction Hashes:")
                                print(f"  Winner feedback: {winner_txn}")
                                print(f"  Loser feedback:  {loser_txn}")
                            else:
                                print("\nFeedback submission failed.")
                    else:
                        print("\nNo feedback submitted.")

                    # Log this interaction
                    message_id1, text1, _ = resp1
                    message_id2, text2, _ = resp2
                    log_entry = {
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "user_input": user_input,
                        "agent_1": {
                            "name": "agent_one",
                            "id": base_agent.agent_id,
                            "message_id": message_id1,
                            "response_text": text1,
                            "error": None if message_id1 != "error" else text1,
                        },
                        "agent_2": {
                            "name": "agent_two",
                            "id": base_agent_01.agent_id,
                            "message_id": message_id2,
                            "response_text": text2,
                            "error": None if message_id2 != "error" else text2,
                        },
                        "feedback": {
                            "choice": feedback if feedback else "none",
                            "winner_txn_hash": winner_txn,
                            "loser_txn_hash": loser_txn,
                        },
                    }
                    session_logs.append(log_entry)

                    input("\nPress Enter to continue...")

                except KeyboardInterrupt:
                    clear_screen()
                    print("\nExiting Agent Arena. Goodbye!")
                    break
                except Exception as e:
                    print(f"\nError: {e}\n")

        finally:
            # Save session logs to file
            if session_logs:
                with open(log_file, "w") as f:
                    json.dump(session_logs, f, indent=2)
                logger.info(f"Session logs saved to: {log_file}")
                logger.info(f"Total interactions logged: {len(session_logs)}")

            # Save decoded transaction history
            history_filename = f"arena_session_{timestamp}"
            assert ethereum_tester_provider is not None
            assert contract_objects is not None
            save_history_to_json(
                history_filename, ethereum_tester_provider, contract_objects
            )
            logger.info(
                f"Transaction history saved to: pyevm_export/{history_filename}.json"
            )

            # Clean up client agent resources
            await base_agent_02.close()
            logger.info("Test cleanup complete")
