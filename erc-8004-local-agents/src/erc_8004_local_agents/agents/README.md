<!--
SPDX-FileCopyrightText: 2025 Semiotic Labs

SPDX-License-Identifier: Apache-2.0
-->

# Agent-to-Agent (A2A) Communication Framework

This directory contains the core components for building and running interoperable agents using the Agent-to-Agent (A2A) communication protocol. It provides a server for hosting agents, a client for interacting with them, and base classes for agent implementation and execution logic.

## Key Components

### `base.py`: ChainedAgent

The `ChainedAgent` is the central class for an agent's identity and capabilities. It integrates with:
- **ERC-8004:** For on-chain identity registration and discovery.
- **DSPy:** For language model-based logic and reasoning.
- **A2A Communication:** It uses `A2AClientWrapper` to connect and communicate with other agents.

### `base_server.py`: BaseServer

The `BaseServer` makes a `ChainedAgent` available over the network. It's a `uvicorn` server that implements the A2A protocol, allowing other agents to discover and interact with it via a standardized HTTP interface.

### `a2a_client.py`: A2AClientWrapper

This is a client-side wrapper that simplifies communication with other agents. It handles the discovery of an agent's capabilities (via its "agent card") and provides simple methods for sending messages.

### `base_executor.py`: BaseExecutor

The `BaseExecutor` acts as the bridge between the `BaseServer` and the `ChainedAgent`. When the server receives an incoming request, the executor calls the agent's logic to process the request and generate a response.

## How It Works

1.  A `ChainedAgent` is defined with its specific logic and tools.
2.  A `BaseServer` is instantiated to host this agent, exposing it at a network endpoint.
3.  Other agents can discover this agent (e.g., via its on-chain ERC-8004 registration).
4.  Using `A2AClientWrapper`, another agent can send a message to the server.
5.  The `BaseServer` receives the message and uses `BaseExecutor` to run the `ChainedAgent`'s logic to handle the request.
