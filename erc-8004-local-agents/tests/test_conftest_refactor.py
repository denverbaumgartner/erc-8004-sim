# system packages
import asyncio
import threading

# external packages
import httpx
import pytest
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

# internal packages
from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.agents.base_server import BaseServer
from erc_8004_local_agents.simulation import SimulationEnvironment

# logging


async def wait_for_server_health(host: str, port: int, max_retries: int = 20) -> bool:
    """Wait for server to be ready by checking health endpoint."""
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://{host}:{port}/health")
                if response.status_code == 200:
                    return True
        except Exception:
            if i == max_retries - 1:
                return False
            await asyncio.sleep(0.5)
    return False


class TestSetup:

    def test_ethereum_tester_provider(self, simulation_env: SimulationEnvironment):
        """Test provider setup via simulation_env."""
        provider = simulation_env.provider
        assert provider is not None
        assert provider.is_connected()
        assert isinstance(provider, EthereumTesterProvider)

    def test_web3_test_instance(self, simulation_env: SimulationEnvironment):
        """Test web3 instance via simulation_env."""
        web3 = simulation_env.web3
        assert web3 is not None
        assert web3.is_connected()
        assert isinstance(web3, Web3)

    def test_server_factory(self, simulation_env: SimulationEnvironment):
        """Test servers via simulation_env."""
        servers = simulation_env.servers
        assert servers is not None
        assert isinstance(servers, dict)
        assert len(servers) > 0
        for server_id, server in servers.items():
            assert server is not None
            assert isinstance(server, BaseServer)
            assert server.agent is not None
            assert isinstance(server.agent, ChainedAgent)

    @pytest.mark.asyncio
    async def test_server_health_check(self, simulation_env: SimulationEnvironment):
        """Test the health check endpoint for all servers."""
        servers = simulation_env.servers
        assert servers is not None
        threads = []
        for server in servers.values():
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            threads.append(thread)

        tasks = [
            wait_for_server_health(server.host, server.port)
            for server in servers.values()
        ]
        results = await asyncio.gather(*tasks)

        assert all(results), "Not all servers passed the health check"

        # Check the response of the first server
        first_server = list(servers.values())[0]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{first_server.host}:{first_server.port}/health"
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
