# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Reusable simulation environment for ERC-8004 agents."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from eth_account import Account
from eth_tester import PyEVMBackend
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.agents.base_server import BaseServer
from erc_8004_local_agents.simulation.account_utils import execute_account_operation
from erc_8004_local_agents.simulation.contract_utils import (
    deploy_contract,
    get_abi_path,
    resolve_contract_reference,
)
from erc_8004_local_agents.simulation.types import LocalNetworkConfig
from erc_8004_local_agents.types.types import AgentConfig, ContractRegistry

logger = logging.getLogger(__name__)


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


def create_contract_registry(contracts: Dict[str, Any]) -> ContractRegistry:
    """Create a ContractRegistry from deployed contracts."""
    return ContractRegistry(
        identity_registry_address=contracts["IdentityRegistry"]["address"],
        reputation_registry_address=contracts["ReputationRegistry"]["address"],
        validation_registry_address=contracts["ValidationRegistry"]["address"],
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


class SimulationEnvironment:
    """Complete simulation environment for ERC-8004 agents.

    Encapsulates blockchain, contracts, agents, and servers in a reusable class that can
    be used both in pytest fixtures and standalone scripts.

    Usage (pytest):     env = SimulationEnvironment()     env.setup()     # Use
    env.agents, env.contracts, etc.

    Usage (standalone):     with SimulationEnvironment() as env:         # Use
    env.agents, env.contracts, etc.         pass
    """

    def __init__(
        self,
        network_config_path: Optional[str] = None,
        agent_configs_dir: Optional[str] = None,
    ):
        """Initialize environment (does not run setup).

        Args:
            network_config_path: Path to local_network.yaml. If None, uses
                `tests/configs/local_network.yaml`.
            agent_configs_dir: Path to agents config directory. If None, assumes
                it's an 'agents' subdirectory relative to the
                network_config_path.
        """
        # Core components (populated during setup)
        self.provider: Optional[EthereumTesterProvider] = None
        self.web3: Optional[Web3] = None
        self.accounts: Optional[List[ChecksumAddress]] = None
        self.config: Optional[LocalNetworkConfig] = None  # Network config
        self.contracts: Optional[Dict[str, Any]] = None
        self.contract_objects: Optional[Dict[str, Any]] = None
        self.agents: Optional[Dict[str, Dict[str, Any]]] = None
        self.servers: Optional[Dict[str, BaseServer]] = None
        self.account_transaction_hashes: Optional[List[str]] = None

        # Store config paths
        self._network_config_path = (
            network_config_path or self._default_network_config_path()
        )
        if agent_configs_dir:
            self._agent_configs_dir = agent_configs_dir
        else:
            self._agent_configs_dir = str(
                Path(self._network_config_path).parent / "agents"
            )
        self._is_setup = False

    def _default_network_config_path(self) -> str:
        """Get default path to network config."""
        # Navigate from src/erc_8004_local_agents/simulation/ to tests/configs/
        base = Path(__file__).parent.parent.parent.parent / "tests"
        return str(base / "configs" / "local_network.yaml")

    def setup(self) -> "SimulationEnvironment":
        """Execute complete environment setup.

        Returns:
            self (for chaining)
        """
        if self._is_setup:
            logger.warning("Environment already set up, skipping")
            return self

        logger.info("Setting up simulation environment...")

        # Will implement in phases
        self._setup_provider()
        self._setup_config()
        self._setup_contracts()
        self._setup_accounts()
        self._setup_agents()
        self._setup_servers()

        self._is_setup = True
        logger.info("✓ Simulation environment setup complete")
        return self

    async def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up simulation environment...")

        if self.agents:
            for agent_id, agent_data in self.agents.items():
                try:
                    await agent_data["agent"].close()
                    logger.debug(f"  Closed {agent_id}")
                except Exception as e:
                    logger.warning(f"  Error closing {agent_id}: {e}")

        logger.info("✓ Cleanup complete")

    # Context manager support (sync)
    def __enter__(self):
        return self.setup()

    def __exit__(self, *args):
        # Can't do async cleanup in sync context
        # User must call cleanup() manually or use async context manager
        pass

    # Async context manager support
    async def __aenter__(self):
        return self.setup()

    async def __aexit__(self, *args):
        await self.cleanup()

    # Properties for backward compatibility with fixtures
    @property
    def account_setup_info(self) -> Dict[str, Any]:
        """Get account setup information (backward compatibility with
        account_setup_factory).

        Returns:
            Dictionary with transaction_hashes and operations_executed
        """
        if self.account_transaction_hashes is None:
            return {"transaction_hashes": [], "operations_executed": 0}
        return {
            "transaction_hashes": self.account_transaction_hashes,
            "operations_executed": len(self.account_transaction_hashes),
        }

    # Setup methods (to be implemented in phases)
    def _setup_provider(self) -> None:
        """Setup blockchain provider (PyEVM)."""
        logger.debug("Setting up blockchain provider...")

        # Create provider (from ethereum_tester_provider fixture)
        self.provider = EthereumTesterProvider()
        if self.provider.ethereum_tester:
            self.provider.ethereum_tester.backend = PyEVMBackend.from_mnemonic(
                "test test test test test test test test test test test junk",
                genesis_state_overrides={"balance": Web3.to_wei(1000000, "ether")},
            )

        # Create Web3 instance (from web3_test_instance fixture)
        self.web3 = Web3(self.provider)

        # Get accounts (from accounts fixture)
        self.accounts = self.web3.eth.accounts  # type: ignore[assignment]

        logger.debug(f"  Created provider with {len(self.accounts or [])} accounts")

    def _setup_config(self) -> None:
        """Load configuration from YAML."""
        logger.debug(f"Loading network config from {self._network_config_path}...")

        # From local_network_config fixture
        # This loads tests/configs/local_network.yaml which contains:
        # - contracts: list of contracts to deploy
        # - accounts: list of account setup operations
        # - agents: list of agents with references to individual config files
        # - simulation: simulation settings
        self.config = LocalNetworkConfig.load_config(Path(self._network_config_path))

        logger.debug(
            f"  Loaded config: {len(self.config.contracts)} contracts, "
            f"{len(self.config.agents)} agents"
        )
        logger.debug(f"  Agent configs will be loaded from: {self._agent_configs_dir}")

    def _setup_contracts(self) -> None:
        """Deploy all contracts in dependency order."""
        logger.debug("Deploying contracts...")

        assert self.config is not None
        assert self.web3 is not None
        assert self.accounts is not None

        self.contracts = {}

        # Sort by deployment_index (from contract_factory fixture)
        sorted_contracts = sorted(
            self.config.contracts, key=lambda x: x.deployment_index
        )

        for contract_config in sorted_contracts:
            # Determine deployer
            if contract_config.deployer_address == "default":
                deployer_address = self.accounts[0]
            else:
                deployer_address = contract_config.deployer_address

            # Resolve contract references in args
            resolved_args = []
            for arg_value in contract_config.contract_args.values():
                resolved_value = resolve_contract_reference(arg_value, self.contracts)
                resolved_args.append(resolved_value)

            # Deploy
            contract_address, abi, bytecode = deploy_contract(
                self.web3,
                get_abi_path(contract_config.contract_type),
                deployer_address,
                *resolved_args,
            )

            self.contracts[contract_config.contract_type.value] = {
                "address": contract_address,
                "abi": abi,
                "bytecode": bytecode,
            }

            logger.debug(f"  Deployed {contract_config.contract_type.value}")

        # Create contract objects (from contract_objects fixture)
        self.contract_objects = {
            contract_name: self.web3.eth.contract(
                abi=contract["abi"], address=contract["address"]
            )
            for contract_name, contract in self.contracts.items()
        }

        logger.debug(f"  Deployed {len(self.contracts)} contracts")

    def _setup_accounts(self) -> None:
        """Execute account setup operations (transfers, approvals)."""
        logger.debug("Executing account setup operations...")

        assert self.config is not None
        assert self.web3 is not None
        assert self.accounts is not None
        assert self.contracts is not None

        # Sort operations by operation_index (from account_setup_factory)
        sorted_operations = sorted(
            self.config.accounts, key=lambda x: x.operation_index
        )

        transaction_hashes = []

        for operation in sorted_operations:
            tx_hash = execute_account_operation(
                self.web3,
                operation,
                self.accounts,
                self.contracts,
            )
            transaction_hashes.append(tx_hash)

        # Store transaction hashes for tests that need to verify operations
        self.account_transaction_hashes = transaction_hashes

        logger.debug(f"  Executed {len(transaction_hashes)} account operations")

    def _setup_agents(self) -> None:
        """Create all agent instances."""
        logger.debug("Creating agents...")

        assert self.config is not None
        assert self.contracts is not None

        self.agents = {}

        # Sort by initialization_index to ensure proper order
        sorted_agents = sorted(self.config.agents, key=lambda x: x.initialization_index)

        for agent_test_config in sorted_agents:
            # Get agent config path
            agent_config_path = (
                Path(self._agent_configs_dir) / agent_test_config.config_file
            )

            # Load agent config from YAML
            agent_config = AgentConfig.from_yaml(str(agent_config_path))

            # Resolve contract addresses into ContractRegistry
            agent_config.contract_registry = create_contract_registry(self.contracts)

            # Create account from index
            account = create_account_from_index(agent_test_config.account_index)

            # Instantiate the agent
            agent = ChainedAgent.from_config(
                agent_config=agent_config,
                web3=self.web3,
                account=account,
            )

            logger.debug(
                f"  Created {agent_test_config.agent_id}: "
                f"config={agent_test_config.config_file}, "
                f"account={account.address}"  # type: ignore[attr-defined]
            )

            self.agents[agent_test_config.agent_id] = {
                "config": agent_config,
                "account": account,
                "account_index": agent_test_config.account_index,
                "agent": agent,
            }

        logger.debug(f"  Created {len(self.agents)} agent(s)")

    def _setup_servers(self) -> None:
        """Create all server instances."""
        logger.debug("Creating servers...")

        assert self.agents is not None

        self.servers = {}

        for agent_id, agent_data in self.agents.items():
            agent = agent_data["agent"]
            url = agent.agent_config.agent_card.url

            # Parse URL to get host and port
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            port = parsed_url.port

            # Create server
            server = BaseServer(agent, host=host, port=port)

            logger.debug(f"  Created server for {agent_id} at {host}:{port}")

            self.servers[agent_id] = server

        logger.debug(f"  Created {len(self.servers)} server(s)")
