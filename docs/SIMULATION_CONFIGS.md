# Configuration for Local Agent Simulation

This directory contains all the necessary configuration files for running a local simulation of ERC-8004 agents.

## Files and Directories

-   `local_network.yaml`: The main configuration file for the local network setup and simulation scenario.
-   `agents/`: A directory containing individual configuration files for each agent participating in the simulation.

---

## `local_network.yaml`

This is the central configuration file. It's broken down into four main sections: `contracts`, `accounts`, `agents`, and `simulation`.

### `contracts`

This section defines the smart contracts to be deployed to the local blockchain instance before the simulation starts.

-   Contracts are deployed sequentially based on their `deployment_index`.
-   You can specify the `contract_type`, the `deployer_address`, and constructor arguments in `contract_args`.
-   To use the address of a previously deployed contract as an argument for another, you can use the syntax: `"$contracts.<ContractType>.address"`.

**Example:**
```yaml
contracts:
  # Deploy IdentityRegistry first
  - deployment_index: 1
    contract_type: IdentityRegistry
    deployer_address: "default"
    contract_args: {}

  # Deploy ReputationRegistry, passing the IdentityRegistry's address
  - deployment_index: 2
    contract_type: ReputationRegistry
    deployer_address: "default"
    contract_args:
      identityRegistry: "$contracts.IdentityRegistry.address"
```

### `accounts`

This section handles the setup of blockchain accounts. You can use it to distribute ETH or ERC-20 tokens to different accounts to prepare them for the simulation.

-   Operations are executed sequentially based on `operation_index`.
-   Supported `action` types include `transfer_eth`, `transfer_erc20`, and `approve_erc20`.
-   Accounts can be referenced by aliases like `"default"` (usually the deployer) or by index, like `"account[1]"`.

**Example:**
```yaml
accounts:
  # Transfer 100 ETH from the default account to account[1]
  - operation_index: 0
    action: "transfer_eth"
    from_account: "default"
    to_account: "account[1]"
    amount: 100
```

### `agents`

This section links the simulation agents to their respective configuration files and blockchain accounts.

-   `agent_id`: A unique identifier for the agent.
-   `config_file`: The name of the agent's configuration file located in the `agents/` directory.
-   `account_index`: The index of the blockchain account (from the local node's list of accounts) that this agent will use.

**Example:**
```yaml
agents:
  - agent_id: "agent_00"
    config_file: "agent_00.yaml"
    account_index: 0
```

### `simulation`

This section defines the actual simulation scenario to be run.

-   `enabled`: A boolean to enable or disable the simulation run.
-   `failing_transaction_allowed`: If set to `true`, the simulation will continue even if a transaction fails.
-   `save_history` and `save_history_file`: Configure whether to save the simulation history to a JSON file.
-   `agents`: A list of tasks for specific agents. Each entry specifies an `agent_id`, a `prompt` for the agent to act upon, and a `loop_count` for how many times the agent should perform the action.

**Example:**
```yaml
simulation:
  enabled: true
  agents:
  - agent_id: "agent_03"
    prompt: "Please select one of the peer agents and provide feedback..."
    loop_count: 2
```

---

## `agents/` Directory

This directory contains individual YAML configuration files for each agent. These files define an agent's identity, capabilities, and AI model configuration.

A typical agent configuration file (`agent_XX.yaml`) includes:

-   `wallet_config`: The agent's Ethereum address and private key.
-   `network_config`: The blockchain network details (Chain ID and RPC endpoint).
-   `contract_registry`: Addresses for the core ERC-8004 smart contracts.
-   `agent_card`: Public-facing metadata about the agent, such as its `name`, `description`, `version`, and `skills`. This is used for agent discovery.
-   `dspy_config`: Configuration for the agent's underlying AI model, likely using the DSPy framework. This includes which language model to use (`main_model`, `adapter_model`), API keys, and other settings.

By modifying these files, you can change an agent's behavior, its AI model, or the blockchain account it uses.
