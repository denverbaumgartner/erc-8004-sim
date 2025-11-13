# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# tests/test_simulation_fixture.py
"""Tests for the simulation_env fixture."""

from erc_8004_local_agents.simulation import SimulationEnvironment


def test_simulation_env_fixture(simulation_env: SimulationEnvironment):
    """Test that simulation_env fixture works."""
    assert simulation_env is not None
    assert simulation_env._is_setup is True


def test_simulation_env_has_all_components(simulation_env: SimulationEnvironment):
    """Test that simulation_env provides all components."""
    # Verify all core components are present
    assert simulation_env.provider is not None
    assert simulation_env.web3 is not None
    assert simulation_env.accounts is not None
    assert simulation_env.config is not None
    assert simulation_env.contracts is not None
    assert simulation_env.contract_objects is not None
    assert simulation_env.agents is not None
    assert simulation_env.servers is not None


def test_simulation_env_agents_structure(simulation_env: SimulationEnvironment):
    """Test that agents have expected structure."""
    assert simulation_env.agents is not None
    assert len(simulation_env.agents) > 0

    for agent_id, agent_data in simulation_env.agents.items():
        assert "config" in agent_data
        assert "account" in agent_data
        assert "account_index" in agent_data
        assert "agent" in agent_data


def test_simulation_env_servers_linked(simulation_env: SimulationEnvironment):
    """Test that servers are linked to agents."""
    assert simulation_env.servers is not None
    assert simulation_env.agents is not None
    assert len(simulation_env.servers) == len(simulation_env.agents)

    for agent_id in simulation_env.agents.keys():
        assert agent_id in simulation_env.servers
        assert (
            simulation_env.servers[agent_id].agent
            == simulation_env.agents[agent_id]["agent"]
        )
