# ERC-8004 Local Agents Test Fixture Documentation

This document provides an overview of the pytest fixture system used for testing the ERC-8004 local agents. The fixtures are designed to provide a fully integrated environment that includes a local blockchain, deployed smart contracts, pre-configured accounts, and running agent servers.

## Overview

The test environment is configured primarily through a single YAML file: `tests/configs/local_network.yaml`. This file dictates:
1.  Which smart contracts to deploy.
2.  How to initialize test accounts with ETH and ERC-20 tokens.
3.  Which agents to set up and which accounts they should use.

The fixtures are designed to be modular and build upon each other, creating a layered and predictable test setup. The core idea is to define the entire state of the local network in the configuration file and have the fixtures automatically bring that state to life.

## Configuration: `local_network.yaml`

This is the central configuration file for the entire test suite. It is divided into three main sections: `contracts`, `accounts`, and `agents`.

### `contracts`

This section defines the smart contracts to be deployed to the local test network. The deployments are ordered by a `deployment_index`.

-   **Dependency Management**: You can inject the address of a previously deployed contract into the constructor of another contract using the `$contracts.<ContractType>.address` syntax. The factory ensures that contracts are deployed in the correct order.

Example:
```yaml
contracts:
  - deployment_index: 0
    contract_type: IdentityRegistry
    deployer_address: "default"
    contract_args: {}

  - deployment_index: 1
    contract_type: ReputationRegistry
    deployer_address: "default"
    contract_args:
      identityRegistry: "$contracts.IdentityRegistry.address"
```

### `accounts`

This section defines a series of operations to be executed to set up the state of the test accounts. These operations run after all contracts have been deployed.

-   **Account References**: You can refer to accounts using `"default"` (the first account), `"account[n]"` (for the n-th account), or a hardcoded address.
-   **Actions**: Supported actions are `transfer_eth`, `transfer_erc20`, and `approve_erc20`.

Example:
```yaml
accounts:
  - operation_index: 0
    action: "transfer_eth"
    from_account: "default"
    to_account: "account[1]"
    amount: 100

  - operation_index: 1
    action: "transfer_erc20"
    contract: "$contracts.ERC-20.address"
    from_account: "default"
    to_account: "account[1]"
    amount: 400000
```

### `agents`

This section defines the agents to be initialized for the tests. Each agent is linked to an account and a specific agent configuration file.

-   **Configuration**: Each agent has its own YAML configuration file (e.g., `agent_00.yaml`) that defines its properties, such as its agent card, tools, and models.
-   **Account Linking**: The `account_index` links an agent to one of the deterministic test accounts.

Example:
```yaml
agents:
  - agent_id: "agent_00"
    config_file: "agent_00.yaml"
    account_index: 0
    initialization_index: 0
```

## Core Fixtures

The test environment is constructed through a series of dependent fixtures. When you request a high-level fixture in your test, pytest automatically sets up all of its dependencies.

### `provider.py`
-   `ethereum_tester_provider`: Sets up an in-memory `eth-tester` blockchain instance (`PyEVMBackend`).
-   `web3_test_instance`: Provides a `Web3` instance connected to the test provider. This is your primary interface for interacting with the blockchain.
-   `accounts`: A tuple of available `ChecksumAddress` accounts from the tester.

### `config.py`
-   `local_network_config`: Loads and parses `tests/configs/local_network.yaml` into Pydantic models for type-safe access.

### `contracts.py`
-   `contract_factory`: The workhorse for contract deployment. It reads the `contracts` section of the config, deploys them in order, and resolves any address dependencies. It returns a dictionary of deployed contracts, including their address, ABI, and bytecode.

### `account_setup.py`
-   `account_setup_factory`: Depends on `contract_factory`. It executes the operations defined in the `accounts` section of the config, such as transferring funds and setting token allowances.

### `agents.py`
-   `agent_factory`: Depends on `contract_factory` and `account_setup_factory`. It creates and initializes all agents defined in the `agents` section of the config. For each agent, it:
    -   Loads its specific YAML configuration.
    -   Creates a local `Account` object from the deterministic private key.
    -   Instantiates the `ChainedAgent`.
    -   Returns a dictionary of all created agents and their associated data.

### `servers.py`
-   `server_factory`: The highest-level fixture. It depends on `agent_factory`. It takes the instantiated agents and launches a `BaseServer` for each one, making them accessible over HTTP. This is essential for end-to-end tests that simulate agent-to-agent communication.

## Execution Flow

When a test requests a fixture like `server_factory`, the following setup sequence is triggered:
1.  The `local_network_config` fixture loads the `local_network.yaml` file.
2.  The `ethereum_tester_provider` and `web3_test_instance` fixtures create a fresh, in-memory blockchain.
3.  The `accounts` fixture exposes the generated test accounts.
4.  The `contract_factory` fixture deploys all configured contracts to the blockchain.
5.  The `account_setup_factory` fixture executes all account initialization operations.
6.  The `agent_factory` fixture instantiates all agents, providing them with their configuration, private keys, and the addresses of the deployed contracts.
7.  Finally, the `server_factory` fixture starts up local web servers for each agent.

Your test function then executes with a fully provisioned and running local agent network.

## Writing a New Test

To write a new test, simply create a new `test_*.py` file in the `tests/` directory and include one or more of the fixtures as arguments to your test function.

### Example Test

Here is a simple example that demonstrates how to access the deployed contracts and agent servers.

```python
# test_example.py
import httpx
import pytest

# The presence of the `server_factory` fixture triggers the entire
# environment setup.
def test_contracts_are_deployed(contract_factory):
    """
    A simple test to verify that the contract factory deployed contracts.
    """
    assert "IdentityRegistry" in contract_factory
    assert "address" in contract_factory["IdentityRegistry"]
    assert contract_factory["IdentityRegistry"]["address"] is not None

@pytest.mark.asyncio
async def test_agent_server_health(server_factory):
    """
    Tests that the agent servers are running and healthy.
    """
    # Get the server for agent_00
    server = server_factory["agent_00"]

    # Start the server in a separate thread (if not already running)
    # Note: For more complex scenarios, you might run servers in the background.
    # The `test_conftest.py` provides an example of this.

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{server.host}:{server.port}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
```

By leveraging these fixtures, you can focus on writing test logic without worrying about the boilerplate of setting up and tearing down the complex test environment.