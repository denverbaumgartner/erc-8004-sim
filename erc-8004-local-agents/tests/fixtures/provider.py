# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Tuple

# external packages
from eth_typing import ChecksumAddress
from pytest import fixture
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

# internal packages
from erc_8004_local_agents.simulation import SimulationEnvironment

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Base Simulation Environment (session-scoped for efficiency)
######################################################################


@fixture(scope="session")
def simulation_env() -> SimulationEnvironment:
    """Provide complete simulation environment (session-scoped for efficiency).

    This is the primary fixture that sets up the entire simulation once per
    test session.
    Other fixtures extract components from this shared environment.

    Returns:
        Fully initialized SimulationEnvironment
    """
    logger.info("Setting up session-scoped SimulationEnvironment...")

    # Explicitly use test configs (not root configs/)
    from pathlib import Path

    test_config_path = str(
        Path(__file__).parent.parent / "configs" / "local_network.yaml"
    )
    agent_configs_dir = str(Path(__file__).parent.parent / "configs" / "agents")

    logger.info(f"Using test config path: {test_config_path}")
    logger.info(f"Using agent configs dir: {agent_configs_dir}")

    env = SimulationEnvironment(
        network_config_path=test_config_path, agent_configs_dir=agent_configs_dir
    )
    env.setup()
    logger.info("SimulationEnvironment setup complete")
    return env


######################################################################
# Provider Layer (extracts from simulation_env)
######################################################################


@fixture
def ethereum_tester_provider(simulation_env) -> EthereumTesterProvider:
    """Extract provider from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.
    """
    return simulation_env.provider


@fixture
def web3_test_instance(simulation_env) -> Web3:
    """Extract Web3 instance from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.
    """
    return simulation_env.web3


@fixture
def accounts(simulation_env) -> Tuple[ChecksumAddress, ...]:
    """Extract accounts from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.
    """
    return tuple(simulation_env.accounts)
