# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# flake8: noqa
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from parent directory
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from tests.fixtures.account_setup import account_setup_factory  # noqa: F401
from tests.fixtures.agents import (  # noqa: F401
    account,
    account_01,
    account_02,
    agent_config,
    agent_config_01,
    agent_config_02,
    agent_factory,
    base_agent,
    base_agent_01,
    base_agent_02,
    base_agent_03,
    base_agent_04,
)
from tests.fixtures.config import local_network_config  # noqa: F401
from tests.fixtures.contracts import contract_factory, contract_objects  # noqa: F401
from tests.fixtures.provider import (  # noqa: F401
    accounts,
    ethereum_tester_provider,
    simulation_env,
    web3_test_instance,
)
from tests.fixtures.servers import (  # noqa: F401
    base_server,
    base_server_01,
    base_server_02,
    server_factory,
)
