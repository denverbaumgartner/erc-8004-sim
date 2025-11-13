# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""E2E Agent Arena - CLI for comparing two agent responses side-by-side."""

import asyncio
import os
import sys
import threading
import uuid
from pathlib import Path

import httpx
from a2a.client import A2AClient
from a2a.types import Message, MessageSendParams, SendMessageRequest, TextPart

from erc_8004_local_agents.agents.base_server import BaseServer
from erc_8004_local_agents.types.types import AgentConfig


def start_server(config_path: str, port: int) -> BaseServer:
    """Start a BaseServer with the given config on the specified port.

    Args:
        config_path: Path to agent configuration YAML file
        port: Port to run the server on

    Returns:
        BaseServer instance
    """
    config = AgentConfig.from_yaml(config_path)

    # Update API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key and config.dspy_config:
        config.dspy_config.api_key = api_key

    server = BaseServer(config, host="127.0.0.1", port=port)

    # Run server in background thread
    def run():
        server.run()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return server


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
    client1: A2AClient, client2: A2AClient, user_input: str
) -> tuple[tuple[str, str], tuple[str, str]]:
    """Send the same message to both agents concurrently.

    Args:
        client1: A2A client for first agent
        client2: A2A client for second agent
        user_input: User's message

    Returns:
        Tuple of ((message_id1, text1), (message_id2, text2))
    """
    # Create message object
    text_part = TextPart(text=user_input)
    message = Message(
        messageId=str(uuid.uuid4()),
        role="user",
        parts=[text_part],
    )

    # Create requests
    request1 = SendMessageRequest(
        id=str(uuid.uuid4()), params=MessageSendParams(message=message)
    )
    request2 = SendMessageRequest(
        id=str(uuid.uuid4()), params=MessageSendParams(message=message)
    )

    # Send to both agents concurrently
    responses = await asyncio.gather(
        client1.send_message(request1),
        client2.send_message(request2),
        return_exceptions=True,
    )

    # Extract message_id and text from responses
    def extract_response_data(response) -> tuple[str, str]:
        if isinstance(response, Exception):
            return ("error", f"Error: {str(response)}")

        # Check if it's an error response
        response_str = str(response)
        if "JSONRPCErrorResponse" in response_str:
            error_msg = "Unknown error"
            if hasattr(response, "root") and hasattr(response.root, "error"):
                error_msg = response.root.error.message
            return ("error", f"Error: {error_msg}")

        # Extract message_id and text from successful response
        try:
            if hasattr(response, "root") and hasattr(response.root, "result"):
                result = response.root.result
                message_id = "unknown"

                # Get message_id
                if hasattr(result, "message_id"):
                    message_id = result.message_id

                # Get text from parts
                if hasattr(result, "parts"):
                    text_parts = []
                    for part in result.parts:
                        if hasattr(part, "text"):
                            text_parts.append(part.text)
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            text_parts.append(part.root.text)
                    if text_parts:
                        return (message_id, " ".join(text_parts))
        except Exception as e:
            return ("error", f"Error parsing response: {str(e)}")

        return ("unknown", str(response))

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
    resp1: tuple[str, str],
    resp2: tuple[str, str],
):
    """Print agent responses in a side-by-side table format.

    Args:
        agent1_name: Name of first agent
        agent2_name: Name of second agent
        resp1: Tuple of (message_id, text) from first agent
        resp2: Tuple of (message_id, text) from second agent
    """
    col_width = 40
    message_id1, text1 = resp1
    message_id2, text2 = resp2

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
    print(f"|{'-' * (col_width + 2)}|{'-' * (col_width + 2)}|\n")

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


async def run_arena():
    """Main arena CLI loop."""
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        print("Please set it and try again.")
        sys.exit(1)

    # Configuration
    config_dir = Path(__file__).parent / "configs"
    agent1_config = config_dir / "agents" / "agent_00.yaml"
    agent2_config = config_dir / "agents" / "agent_01.yaml"

    port1 = 8001
    port2 = 8002

    print("Starting Agent Arena...")
    print("Initializing agent servers...")

    # Start servers (processes kept running in background)
    start_server(str(agent1_config), port1)
    start_server(str(agent2_config), port2)

    # Wait for servers to be ready
    print("Waiting for Agent 1 to start...")
    if not await wait_for_server("127.0.0.1", port1):
        print("Error: Agent 1 failed to start")
        sys.exit(1)

    print("Waiting for Agent 2 to start...")
    if not await wait_for_server("127.0.0.1", port2):
        print("Error: Agent 2 failed to start")
        sys.exit(1)

    print("Both agents ready!\n")

    # Create A2A clients with extended timeout for LLM calls
    timeout = httpx.Timeout(30.0, read=60.0)
    async with (
        httpx.AsyncClient(timeout=timeout) as http_client1,
        httpx.AsyncClient(timeout=timeout) as http_client2,
    ):
        client1 = A2AClient(url=f"http://127.0.0.1:{port1}", httpx_client=http_client1)
        client2 = A2AClient(url=f"http://127.0.0.1:{port2}", httpx_client=http_client2)

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

                # Send to both agents
                resp1, resp2 = await send_message_to_agents(
                    client1, client2, user_input
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

                # We are not storing the feedback, just completing the user flow
                print("\nThank you for your feedback!")
                input("Press Enter to continue...")

            except KeyboardInterrupt:
                clear_screen()
                print("\nExiting Agent Arena. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(run_arena())

###########
