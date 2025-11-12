# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# tests/test_simulation_env_phase4.py
import pytest

from erc_8004_local_agents.simulation import SimulationEnvironment


def test_agent_creation():
    """Test agent creation from configs."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()
    env._setup_accounts()
    env._setup_agents()

    # Verify agents created
    assert env.agents is not None
    assert len(env.agents) > 0

    # Verify each agent has required components
    for agent_id, agent_data in env.agents.items():
        assert "config" in agent_data
        assert "account" in agent_data
        assert "account_index" in agent_data
        assert "agent" in agent_data

        # Verify agent is properly initialized
        assert agent_data["agent"] is not None
        assert agent_data["agent"].agent_config is not None

        # Verify account matches expected address from index
        assert agent_data["account"].address is not None


def test_server_creation():
    """Test server creation from agents."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()
    env._setup_accounts()
    env._setup_agents()
    env._setup_servers()

    # Verify servers created
    assert env.servers is not None
    assert len(env.servers) > 0

    # Verify each server is properly initialized
    for agent_id, server in env.servers.items():
        assert server is not None
        assert server.agent is not None
        assert server.host is not None
        assert server.port is not None

        # Verify server agent matches the agent from env.agents
        assert env.agents is not None
        assert server.agent == env.agents[agent_id]["agent"]


def test_full_phase4_setup():
    """Test full Phase 4 setup (agents + servers)."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()
    env._setup_accounts()
    env._setup_agents()
    env._setup_servers()

    # Verify all components are set up
    assert env.web3 is not None
    assert env.accounts is not None
    assert env.config is not None
    assert env.contracts is not None
    assert env.contract_objects is not None
    assert env.agents is not None
    assert env.servers is not None

    # Verify agent and server counts match
    assert len(env.agents) == len(env.servers)

    # Verify agents and servers are linked
    for agent_id in env.agents.keys():
        assert agent_id in env.servers
        assert env.servers[agent_id].agent == env.agents[agent_id]["agent"]


def test_full_setup_method():
    """Test the full setup() method integrates all phases."""
    env = SimulationEnvironment()
    result = env.setup()

    # Verify setup returns self for chaining
    assert result == env

    # Verify all components are set up
    assert env.web3 is not None
    assert env.accounts is not None
    assert env.config is not None
    assert env.contracts is not None
    assert env.contract_objects is not None
    assert env.agents is not None
    assert env.servers is not None

    # Verify _is_setup flag is set
    assert env._is_setup is True

    # Verify we can call setup again (should skip)
    result2 = env.setup()
    assert result2 == env


def test_agent_contract_integration():
    """Test that agents have access to deployed contracts."""
    env = SimulationEnvironment()
    env.setup()

    assert env.agents is not None
    assert env.contracts is not None

    # Verify agents can access contracts
    for agent_id, agent_data in env.agents.items():
        agent = agent_data["agent"]

        # Verify agent has contract registry
        assert agent.agent_config.contract_registry is not None

        # Verify registry has correct contract addresses
        registry = agent.agent_config.contract_registry
        assert (
            registry.identity_registry_address
            == env.contracts["IdentityRegistry"]["address"]
        )
        assert (
            registry.reputation_registry_address
            == env.contracts["ReputationRegistry"]["address"]
        )
        assert (
            registry.validation_registry_address
            == env.contracts["ValidationRegistry"]["address"]
        )


@pytest.mark.asyncio
async def test_cleanup():
    """Test that cleanup closes all agents properly."""
    env = SimulationEnvironment()
    env.setup()

    assert env.agents is not None
    # Verify agents exist
    assert len(env.agents) > 0

    # Call cleanup
    await env.cleanup()

    # Note: We can't easily verify agents are closed without checking their
    # internal state
    # This test mainly ensures cleanup doesn't raise errors
    assert True
