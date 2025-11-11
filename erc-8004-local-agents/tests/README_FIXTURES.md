# Test Fixtures Architecture

This document describes the factory pattern used for test fixtures in this project.

## Overview

The test fixtures follow a clean factory pattern similar to `contract_factory`, making it easy to configure and manage test agents, contracts, and accounts declaratively via YAML configuration.

## Configuration Files

### Main Configuration: `tests/configs/local_network.yaml`

This file defines:
- **Contracts**: Which contracts to deploy and their constructor args
- **Accounts**: Account setup operations (ETH transfers, ERC-20 operations, etc.)
- **Agents**: Which agent configurations to load and initialize

Example agents section:
```yaml
agents:
  - agent_id: "agent_00"
    config_file: "agent_00.yaml"
    account_index: 0
    initialization_index: 0

  - agent_id: "agent_01"
    config_file: "agent_01.yaml"
    account_index: 1
    initialization_index: 1
```

### Agent Configurations: `tests/configs/agents/`

Individual agent YAML files (e.g., `agent_00.yaml`, `agent_01.yaml`) contain:
- Wallet configuration (address, private_key)
- Network configuration (chain_id, chain_rpc)
- Agent card metadata (name, description, skills, etc.)
- DSPy configuration (if applicable)

## Factory Fixtures

### 1. `contract_factory`

**File**: `tests/fixtures/contracts.py`

**Purpose**: Deploys contracts in dependency order and resolves contract address references.

**Returns**: Dictionary of deployed contracts:
```python
{
    "IdentityRegistry": {"address": "0x...", "abi": [...], "bytecode": "0x..."},
    "ReputationRegistry": {"address": "0x...", "abi": [...], "bytecode": "0x..."},
    ...
}
```

### 2. `account_setup_factory`

**File**: `tests/fixtures/account_setup.py`

**Purpose**: Executes account setup operations (transfers, approvals) in order.

**Returns**: Dictionary with operation metadata:
```python
{
    "transaction_hashes": ["0x...", "0x...", ...],
    "operations_executed": 9
}
```

### 3. `agent_factory`

**File**: `tests/fixtures/agents.py`

**Purpose**: Loads agent configurations and creates Account instances.

**Returns**: Dictionary of agent data keyed by agent_id:
```python
{
    "agent_00": {
        "config": AgentConfig instance,
        "account": Account instance,
        "account_index": 0
    },
    ...
}
```

## Backward Compatible Fixtures

For backward compatibility, individual agent fixtures are provided:

- `agent_config`, `account`, `base_agent` - For agent_00
- `agent_config_01`, `account_01`, `base_agent_01` - For agent_01
- `agent_config_02`, `account_02`, `base_agent_02` - For agent_02

These fixtures use `agent_factory` internally but maintain the same API as before.

## Usage Examples

### Using Individual Fixtures (Backward Compatible)

```python
def test_my_agent(base_agent: ChainedAgent, base_agent_01: ChainedAgent):
    """Test using individual agent fixtures."""
    base_agent.register_agent()
    # ... test code
```

### Using Agent Factory (New Pattern)

```python
def test_with_factory(agent_factory: Dict[str, Any]):
    """Test using the agent factory directly."""
    agent_00_config = agent_factory["agent_00"]["config"]
    agent_00_account = agent_factory["agent_00"]["account"]

    # Create agent manually
    agent = ChainedAgent.from_config(
        agent_config=agent_00_config,
        web3=web3_instance,
        account=agent_00_account
    )
```

## Adding New Agents

To add a new agent for testing:

1. Create agent config file in `tests/configs/agents/` (e.g., `agent_03.yaml`)
2. Add entry to `local_network.yaml`:
   ```yaml
   agents:
     - agent_id: "agent_03"
       config_file: "agent_03.yaml"
       account_index: 3
       initialization_index: 3
   ```
3. (Optional) Add ETH transfer in `accounts` section if the agent needs funding
4. (Optional) Create convenience fixtures in `tests/fixtures/agents.py` for backward compatibility

## Benefits of This Pattern

1. **Declarative**: All test setup is declared in YAML, not scattered in Python code
2. **DRY**: Agent configurations are defined once and reused across tests
3. **Flexible**: Easy to add new agents or modify existing ones
4. **Ordered**: Explicit control over initialization order via `initialization_index`
5. **Clean**: Separates configuration from test logic
6. **Backward Compatible**: Existing tests continue to work without changes
