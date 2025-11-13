# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Optional

import yaml
from a2a.types import AgentCard

# external packages
from pydantic import BaseModel, model_validator

# internal packages
from erc_8004_local_agents.dspy_base_agent.types import DSPyAgentConfig

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WalletConfig(BaseModel):
    address: str
    private_key: str


class NetworkConfig(BaseModel):
    chain_id: int
    chain_rpc: str


class ContractRegistry(BaseModel):
    identity_registry_address: str
    reputation_registry_address: str
    validation_registry_address: str


class AgentResponse(BaseModel):
    """Response from agent processing including optional feedback auth."""

    output: str
    feedback_auth: Optional[str] = None


class AgentConfig(BaseModel):
    wallet_config: WalletConfig
    network_config: NetworkConfig
    contract_registry: ContractRegistry
    agent_card: AgentCard
    dspy_config: Optional[DSPyAgentConfig] = None

    @model_validator(mode="before")
    @classmethod
    def _populate_dspy_config_details(cls, data):
        if data.get("dspy_config") and data.get("agent_card"):
            data["dspy_config"]["name"] = data["agent_card"]["name"]
            data["dspy_config"]["description"] = data["agent_card"]["description"]
        return data

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "AgentConfig":
        with open(yaml_path, "r") as file:
            yaml_data = yaml.load(file, Loader=yaml.FullLoader)
        return cls.model_validate(yaml_data)
