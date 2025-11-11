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

    def test_ethereum_tester_provider(self, ethereum_tester_provider):
        assert ethereum_tester_provider.is_connected()
        assert isinstance(ethereum_tester_provider, EthereumTesterProvider)

    def test_web3_test_instance(self, web3_test_instance):
        assert web3_test_instance.is_connected()
        assert isinstance(web3_test_instance, Web3)

    def test_server_factory(self, server_factory):
        assert server_factory is not None
        assert isinstance(server_factory, dict)
        assert len(server_factory) > 0
        for server_id, server in server_factory.items():
            assert server is not None
            assert isinstance(server, BaseServer)
            assert server.agent is not None
            assert isinstance(server.agent, ChainedAgent)

    @pytest.mark.asyncio
    async def test_server_health_check(self, server_factory):
        """Test the health check endpoint for all servers."""
        threads = []
        for server in server_factory.values():
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            threads.append(thread)

        tasks = [
            wait_for_server_health(server.host, server.port)
            for server in server_factory.values()
        ]
        results = await asyncio.gather(*tasks)

        assert all(results), "Not all servers passed the health check"

        # Check the response of the first server
        first_server = list(server_factory.values())[0]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{first_server.host}:{first_server.port}/health"
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
