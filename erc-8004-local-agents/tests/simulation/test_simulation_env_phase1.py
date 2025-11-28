# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# tests/test_simulation_env_phase1.py
import pytest

from erc_8004_local_agents.simulation import SimulationEnvironment


def test_simulation_env_creation():
    """Test that SimulationEnvironment can be instantiated."""
    env = SimulationEnvironment()
    assert env is not None
    assert env.provider is None  # Not set up yet
    assert env._is_setup is False


def test_simulation_env_default_config_path():
    """Test default config path is set correctly."""
    env = SimulationEnvironment()
    assert "local_network.yaml" in env._network_config_path


def test_simulation_env_custom_config_path():
    """Test custom config path."""
    custom_path = "/custom/path/config.yaml"
    env = SimulationEnvironment(network_config_path=custom_path)
    assert env._network_config_path == custom_path


@pytest.mark.asyncio
async def test_simulation_env_basic_lifecycle():
    """Test basic lifecycle: creation, setup, and cleanup."""
    env = SimulationEnvironment()

    # Verify initial state
    assert env._is_setup is False

    # Setup should succeed now that all phases are implemented
    result = env.setup()
    assert result == env
    assert env._is_setup is True

    # Cleanup should succeed
    await env.cleanup()
