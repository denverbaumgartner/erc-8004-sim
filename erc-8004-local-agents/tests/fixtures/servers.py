# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Dict

# external packages
from pytest import fixture

# internal packages
from erc_8004_local_agents.agents.base_server import BaseServer

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

######################################################################
# Fixtures
######################################################################


@fixture
def server_factory(simulation_env) -> Dict[str, BaseServer]:
    """Extract server factory from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.

    Returns:
        Dictionary of BaseServer instances keyed by agent_id
    """
    return simulation_env.servers


@fixture
def base_server(server_factory: Dict[str, BaseServer]) -> BaseServer:
    """Get agent_00 server (backward compatibility)."""
    return server_factory["agent_00"]


@fixture
def base_server_01(server_factory: Dict[str, BaseServer]) -> BaseServer:
    """Get agent_01 server (backward compatibility)."""
    return server_factory["agent_01"]


@fixture
def base_server_02(server_factory: Dict[str, BaseServer]) -> BaseServer:
    """Get agent_02 server (backward compatibility)."""
    return server_factory["agent_02"]
