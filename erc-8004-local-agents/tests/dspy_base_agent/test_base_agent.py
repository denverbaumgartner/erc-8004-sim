# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Any, Dict

from erc8004 import ERC8004Client, Web3Adapter

# external packages
from web3 import Web3

from erc_8004_local_agents.agents.base import ChainedAgent

# internal packages
from erc_8004_local_agents.types.types import AgentConfig

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestChainedAgent:

    def test_base_agent(
        self, contract_factory: Dict[str, Any], base_agent: ChainedAgent
    ) -> None:
        assert base_agent is not None
        assert isinstance(base_agent, ChainedAgent)
        assert base_agent.agent_config is not None
        assert isinstance(base_agent.agent_config, AgentConfig)
        assert base_agent.w3 is not None
        assert isinstance(base_agent.w3, Web3)
        assert base_agent.adapter is not None
        assert isinstance(base_agent.adapter, Web3Adapter)
        assert base_agent.client is not None
        assert isinstance(base_agent.client, ERC8004Client)

        # check that the dspy agent is configured
        assert base_agent.dspy_agent is not None

        # use the base agent to get the current block number
        block_number = base_agent.w3.eth.block_number
        assert block_number is not None
        assert isinstance(block_number, int)
        assert block_number > 0

    def test_base_agent_01(self, base_agent_01: ChainedAgent) -> None:
        logger.info(f"Base Agent 01 Address: {base_agent_01.client.get_address()}")
        assert base_agent_01 is not None
        assert isinstance(base_agent_01, ChainedAgent)
        assert base_agent_01.agent_config is not None
        assert isinstance(base_agent_01.agent_config, AgentConfig)
        assert base_agent_01.w3 is not None
        assert isinstance(base_agent_01.w3, Web3)
        assert base_agent_01.adapter is not None
        assert isinstance(base_agent_01.adapter, Web3Adapter)

    def test_base_agent_02(self, base_agent_02: ChainedAgent) -> None:
        logger.info(f"Base Agent 02 Address: {base_agent_02.client.get_address()}")
        assert base_agent_02 is not None
        assert isinstance(base_agent_02, ChainedAgent)
        assert base_agent_02.agent_config is not None
        assert isinstance(base_agent_02.agent_config, AgentConfig)
        assert base_agent_02.w3 is not None
        assert isinstance(base_agent_02.w3, Web3)

    def test_base_agent_04(self, base_agent_04: ChainedAgent) -> None:
        logger.info(f"Base Agent 04 Address: {base_agent_04.client.get_address()}")
        assert base_agent_04 is not None
        assert isinstance(base_agent_04, ChainedAgent)
        assert base_agent_04.agent_config is not None
        assert isinstance(base_agent_04.agent_config, AgentConfig)
        assert base_agent_04.w3 is not None
        assert isinstance(base_agent_04.w3, Web3)

    def test_base_agent_register(self, base_agent: ChainedAgent) -> None:
        result = base_agent.register_agent()
        assert result is not None
        assert isinstance(result, dict)

        # ensure the agent id is set
        assert base_agent.agent_id is not None
        assert isinstance(base_agent.agent_id, int)
        logger.info(f"Agent ID: {base_agent.agent_id}")

        assert "agentId" in result
        assert "txHash" in result
