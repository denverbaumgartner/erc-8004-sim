# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0
"""Configuration types for simulation environment."""

# system packages
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import yaml

# external packages
from eth_typing import ChecksumAddress
from pydantic import BaseModel

######################################################################
# Enums
######################################################################


class ContractTypeEnum(Enum):
    ERC_20 = "ERC-20"
    IDENTITY_REGISTRY = "IdentityRegistry"
    REPUTATION_REGISTRY = "ReputationRegistry"
    VALIDATION_REGISTRY = "ValidationRegistry"


class AccountActionEnum(Enum):
    TRANSFER_ETH = "transfer_eth"
    TRANSFER_ERC20 = "transfer_erc20"
    APPROVE_ERC20 = "approve_erc20"


######################################################################
# Configuration Models
######################################################################


class ContractConfig(BaseModel):
    deployment_index: int
    contract_type: ContractTypeEnum
    deployer_address: ChecksumAddress
    contract_args: Dict[str, Any]


class AccountOperationConfig(BaseModel):
    operation_index: int
    action: AccountActionEnum
    from_account: str | None = None
    to_account: str | None = None
    contract: str | None = None
    owner: str | None = None
    spender: str | None = None
    amount: int | float
    decimals: int = 18


class AgentTestConfig(BaseModel):
    """Configuration for an agent in the test environment.

    Attributes:
        agent_id: Unique identifier for the agent (e.g., "agent_00")
        config_file: Filename of the agent config in the agents/ subdirectory
        account_index: Index of the eth-tester account to use for this agent
        initialization_index: Order in which agents should be initialized
    """

    agent_id: str
    config_file: str
    account_index: int
    initialization_index: int


class SimulationAgentConfig(BaseModel):
    """Configuration for an agent in the simulation.

    Attributes:
        agent_id: ID of the agent that will be driving the simulation loop
        prompt: The prompt to be sent to the agent in each loop
        loop_count: Number of times the agent's main workflow should be executed
    """

    agent_id: str
    prompt: str
    loop_count: int = 1


class SimulationConfig(BaseModel):
    """Configuration for the simulation test.

    Attributes:
        enabled: If False or not present, the simulation test should be skipped
        failing_transaction_allowed: If True, the test will not fail if an on-chain
            verification step does not pass
        save_history: If True, save the simulation history to a JSON file
        save_history_file: Filename for the history JSON file (saved in pyevm_export/)
        agents: List of agents to participate in the simulation
    """

    enabled: bool = False
    failing_transaction_allowed: bool = False
    save_history: bool = True
    save_history_file: str = "erc_8004_sim_history.json"
    agents: List[SimulationAgentConfig] = []


class LocalNetworkConfig(BaseModel):
    """Complete configuration for local network setup.

    This defines contracts to deploy, account operations to execute, agents to
    instantiate, and simulation parameters.
    """

    contracts: List[ContractConfig]
    accounts: List[AccountOperationConfig] = []
    agents: List[AgentTestConfig] = []
    simulation: SimulationConfig | None = None

    @classmethod
    def load_config(cls, config_file: Path) -> "LocalNetworkConfig":
        """Load configuration from YAML file."""
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        return cls.model_validate(config)
