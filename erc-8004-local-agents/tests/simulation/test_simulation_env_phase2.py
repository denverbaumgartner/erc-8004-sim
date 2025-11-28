# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# tests/test_simulation_env_phase2.py

from erc_8004_local_agents.simulation import SimulationEnvironment


def test_provider_setup():
    """Test provider setup creates blockchain."""
    env = SimulationEnvironment()
    env._setup_provider()

    assert env.provider is not None
    assert env.web3 is not None
    assert env.accounts is not None
    assert len(env.accounts) >= 10  # eth-tester default


def test_config_setup():
    """Test config loads from YAML."""
    env = SimulationEnvironment()
    env._setup_config()

    assert env.config is not None
    assert env.config.contracts is not None
    assert env.config.agents is not None

    # Verify structure
    assert len(env.config.contracts) > 0
    assert len(env.config.agents) > 0


def test_provider_and_config_together():
    """Test provider + config setup works."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()

    # Both should be set
    assert env.web3 is not None
    assert env.config is not None
    assert env.accounts is not None

    # Should be able to interact with blockchain
    balance = env.web3.eth.get_balance(env.accounts[0])
    assert balance > 0
