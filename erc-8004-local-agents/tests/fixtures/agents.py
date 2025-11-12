# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from pathlib import Path
from typing import Any, Dict

from eth_account import Account
from pytest import fixture

# internal packages
from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.types.types import AgentConfig, ContractRegistry

# external packages


# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

######################################################################
# Constants
######################################################################

# Deterministic private keys for eth-tester accounts
ETH_TESTER_PRIVATE_KEYS = {
    0: "0x0000000000000000000000000000000000000000000000000000000000000001",
    1: "0x0000000000000000000000000000000000000000000000000000000000000002",
    2: "0x0000000000000000000000000000000000000000000000000000000000000003",
    3: "0x0000000000000000000000000000000000000000000000000000000000000004",
    4: "0x0000000000000000000000000000000000000000000000000000000000000005",
    5: "0x0000000000000000000000000000000000000000000000000000000000000006",
    6: "0x0000000000000000000000000000000000000000000000000000000000000007",
    7: "0x0000000000000000000000000000000000000000000000000000000000000008",
    8: "0x0000000000000000000000000000000000000000000000000000000000000009",
    9: "0x000000000000000000000000000000000000000000000000000000000000000a",
}

######################################################################
# Helper functions
######################################################################


def get_agent_config_path(config_file: str) -> Path:
    """Get the path to an agent config file in the agents/ subdirectory."""
    config_dir = Path(__file__).parent.parent / "configs" / "agents"
    return config_dir / config_file


def create_contract_registry(contract_factory: Dict[str, Any]) -> ContractRegistry:
    """Create a ContractRegistry from deployed contracts."""
    return ContractRegistry(
        identity_registry_address=contract_factory["IdentityRegistry"]["address"],
        reputation_registry_address=contract_factory["ReputationRegistry"]["address"],
        validation_registry_address=contract_factory["ValidationRegistry"]["address"],
    )


def create_account_from_index(account_index: int) -> Account:
    """Create an Account instance from an eth-tester account index."""
    if account_index not in ETH_TESTER_PRIVATE_KEYS:
        raise ValueError(
            f"Account index {account_index} out of range "
            f"(0-{len(ETH_TESTER_PRIVATE_KEYS)-1})"
        )

    private_key = ETH_TESTER_PRIVATE_KEYS[account_index]
    account = Account.from_key(private_key)
    logger.debug(f"Created account {account_index}: {account.address}")
    return account


def load_and_resolve_agent_config(
    config_file: str,
    contract_factory: Dict[str, Any],
) -> AgentConfig:
    """Load an agent config file and resolve contract addresses.

    Args:
        config_file: Filename of the agent config in agents/ subdirectory
        contract_factory: Dictionary of deployed contracts

    Returns:
        AgentConfig with resolved contract addresses
    """
    config_path = get_agent_config_path(config_file)
    logger.debug(f"Loading agent config from {config_path}")

    agent_config = AgentConfig.from_yaml(str(config_path))

    # Resolve contract addresses from deployed contracts
    agent_config.contract_registry = create_contract_registry(contract_factory)

    return agent_config


######################################################################
# Fixtures
######################################################################


@fixture
def agent_factory(simulation_env) -> Dict[str, Dict[str, Any]]:
    """Extract agent factory from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.

    Returns:
        Dictionary with agent info keyed by agent_id:
        {
            "agent_00": {
                "config": AgentConfig instance,
                "account": Account instance,
                "account_index": 0,
                "agent": ChainedAgent instance
            },
            ...
        }
    """
    return simulation_env.agents


######################################################################
# Individual agent fixtures (backward compatibility)
######################################################################


@fixture
def agent_config(agent_factory: Dict[str, Any]) -> AgentConfig:
    """Get agent_00 config (backward compatibility)."""
    return agent_factory["agent_00"]["config"]


@fixture
def account(agent_factory: Dict[str, Any]) -> Account:
    """Get agent_00 account (backward compatibility)."""
    return agent_factory["agent_00"]["account"]


@fixture
def agent_config_01(agent_factory: Dict[str, Any]) -> AgentConfig:
    """Get agent_01 config (backward compatibility)."""
    return agent_factory["agent_01"]["config"]


@fixture
def account_01(agent_factory: Dict[str, Any]) -> Account:
    """Get agent_01 account (backward compatibility)."""
    return agent_factory["agent_01"]["account"]


@fixture
def agent_config_02(agent_factory: Dict[str, Any]) -> AgentConfig:
    """Get agent_02 config (backward compatibility)."""
    return agent_factory["agent_02"]["config"]


@fixture
def account_02(agent_factory: Dict[str, Any]) -> Account:
    """Get agent_02 account (backward compatibility)."""
    return agent_factory["agent_02"]["account"]


@fixture
def base_agent(agent_factory: Dict[str, Any]) -> ChainedAgent:
    """Get agent_00 instance (backward compatibility)."""
    return agent_factory["agent_00"]["agent"]


@fixture
def base_agent_01(agent_factory: Dict[str, Any]) -> ChainedAgent:
    """Get agent_01 instance (backward compatibility)."""
    return agent_factory["agent_01"]["agent"]


@fixture
def base_agent_02(agent_factory: Dict[str, Any]) -> ChainedAgent:
    """Get agent_02 instance (backward compatibility)."""
    return agent_factory["agent_02"]["agent"]


@fixture
def base_agent_03(agent_factory: Dict[str, Any]) -> ChainedAgent:
    """Get agent_03 instance (backward compatibility)."""
    return agent_factory["agent_03"]["agent"]


@fixture
def base_agent_04(agent_factory: Dict[str, Any]) -> ChainedAgent:
    """Get agent_04 instance (backward compatibility)."""
    return agent_factory["agent_04"]["agent"]
