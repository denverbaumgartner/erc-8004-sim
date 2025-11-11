# ERC-8004 Simulation Framework

This document provides an overview of the simulation framework's architecture, detailing how it works and what key components you should be aware of when working with the code.

## 1. Overview

The simulation framework is designed to provide a fully encapsulated, configurable environment for testing ERC-8004 agents and smart contracts. It programmatically sets up a local blockchain, deploys contracts, configures agent accounts, and launches agent servers based on declarative YAML configuration files.

The core of the framework is the `SimulationEnvironment` class located in `src/erc_8004_local_agents/simulation/simulation_env.py`. This class manages the entire lifecycle of the simulation.

## 2. Core Components

### `SimulationEnvironment`
This is the main orchestrator. It encapsulates all the moving parts of the simulation:
- **Local Blockchain**: An in-memory `PyEVMBackend` instance for fast and deterministic transaction processing.
- **Web3 Provider**: A configured `Web3` instance connected to the local blockchain.
- **Contracts**: Smart contracts deployed to the local chain.
- **Agents**: Instances of `ChainedAgent`, each with its own configuration, blockchain account, and HTTP server.

It is designed to be used as a context manager (`with SimulationEnvironment() as env:`) to ensure proper setup and teardown of all resources.

### Configuration (`.yaml` files)
The entire simulation is driven by YAML files, which define the desired state of the environment.
- **`local_network.yaml`**: The main configuration file. It specifies which contracts to deploy, what initial account setups to perform (e.g., token transfers), and which agents to initialize.
- **Agent Configs**: Each agent has its own YAML file (e.g., `agent_00.yaml`) defining its properties, such as its agent card, language model, and tools.

### Key Modules
The logic is split across several key modules within `src/erc_8004_local_agents/simulation/`:

- **`simulation_env.py`**: Contains the `SimulationEnvironment` class and manages the setup lifecycle. This is the primary entry point for using the framework.
- **`contract_utils.py`**: Provides helper functions for deploying smart contracts. It handles reading ABI/bytecode and can resolve dependencies between contracts (e.g., passing one contract's address to another's constructor).
- **`account_utils.py`**: Contains logic for executing the initial on-chain operations defined in the configuration, such as sending ETH or calling contract functions to set up a specific state.
- **`types.py`**: Defines the Pydantic data models that map directly to the structure of the YAML configuration files. This provides type safety and validation for all configuration.

## 3. The Setup Lifecycle

When `SimulationEnvironment.setup()` is called, it executes a series of ordered steps to build the environment:
1.  **Provider Setup**: Initializes the `PyEVMBackend` local blockchain and the `Web3` instance.
2.  **Config Loading**: Parses the `local_network.yaml` and associated agent configuration files into the Pydantic models.
3.  **Contract Deployment**: Deploys the contracts specified in the config in the correct order, resolving any address dependencies.
4.  **Account Setup**: Executes all predefined account operations to create the initial on-chain state.
5.  **Agent Initialization**: Creates instances of `ChainedAgent` for each agent defined in the config, assigning them a unique account and connecting them to the deployed contracts.
6.  **Server Setup**: For each initialized agent, it launches a `BaseServer` instance, allowing the agents to communicate via HTTP.

## 4. Usage

This framework is used in two primary ways:
- **Pytest Fixtures**: It powers the integration and end-to-end tests, allowing tests to run against a predictable and isolated environment.
- **Standalone Scripts**: The `sim/run.py` script uses `SimulationEnvironment` to run complex, multi-agent scenarios outside of the `pytest` framework, making it useful for development, debugging, and demonstrations.
