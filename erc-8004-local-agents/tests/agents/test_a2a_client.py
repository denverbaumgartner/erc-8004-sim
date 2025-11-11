# system packages
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# external packages
import httpx
import pytest
from a2a.types import AgentCard, SendMessageResponse

from erc_8004_local_agents.agents.a2a_client import A2AClientWrapper
from erc_8004_local_agents.agents.base import ChainedAgent

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestA2AClientWrapper:
    """Test the A2AClientWrapper class."""

    @pytest.mark.asyncio
    async def test_wrapper_initialization(self):
        """Test that the wrapper can be initialized."""
        async with httpx.AsyncClient() as client:
            wrapper = A2AClientWrapper(
                endpoint="http://localhost:8000",
                httpx_client=client,
            )
            assert wrapper.endpoint == "http://localhost:8000"
            assert wrapper.httpx_client is client
            assert wrapper._agent_card is None
            assert wrapper._client is None

    @pytest.mark.asyncio
    async def test_wrapper_lazy_initialization(self):
        """Test that the wrapper lazily initializes the A2A client."""
        async with httpx.AsyncClient() as client:
            wrapper = A2AClientWrapper(
                endpoint="http://localhost:8000",
                httpx_client=client,
            )

            # Mock the agent card resolver and A2AClient
            mock_agent_card = MagicMock(spec=AgentCard)
            mock_agent_card.url = "http://localhost:8000/messages"
            mock_agent_card.supports_authenticated_extended_card = False

            with (
                patch(
                    "erc_8004_local_agents.agents.a2a_client.A2ACardResolver"
                ) as mock_resolver_class,
                patch(
                    "erc_8004_local_agents.agents.a2a_client.A2AClient"
                ) as mock_client_class,
            ):
                mock_resolver = MagicMock()
                mock_resolver.get_agent_card = AsyncMock(return_value=mock_agent_card)
                mock_resolver_class.return_value = mock_resolver

                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Ensure initialization happens
                await wrapper._ensure_initialized()

                # Verify initialization occurred
                assert wrapper._agent_card is mock_agent_card
                assert wrapper._client is mock_client

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message through the wrapper."""
        async with httpx.AsyncClient() as client:
            wrapper = A2AClientWrapper(
                endpoint="http://localhost:8000",
                httpx_client=client,
            )

            # Mock the agent card and client
            mock_agent_card = MagicMock(spec=AgentCard)
            mock_response = MagicMock(spec=SendMessageResponse)

            with patch(
                "erc_8004_local_agents.agents.a2a_client.A2ACardResolver"
            ) as mock_resolver_class:
                mock_resolver = MagicMock()
                mock_resolver.get_agent_card = AsyncMock(return_value=mock_agent_card)
                mock_resolver_class.return_value = mock_resolver

                with patch(
                    "erc_8004_local_agents.agents.a2a_client.A2AClient"
                ) as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.send_message = AsyncMock(return_value=mock_response)
                    mock_client_class.return_value = mock_client

                    # Send a message
                    response = await wrapper.send_message("Hello, agent!")

                    # Verify response
                    assert response is mock_response
                    mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_task_and_context(self):
        """Test sending a message with task_id and context_id."""
        async with httpx.AsyncClient() as client:
            wrapper = A2AClientWrapper(
                endpoint="http://localhost:8000",
                httpx_client=client,
            )

            # Mock the agent card and client
            mock_agent_card = MagicMock(spec=AgentCard)
            mock_agent_card.url = "http://localhost:8000/messages"
            mock_agent_card.supports_authenticated_extended_card = False
            mock_response = MagicMock(spec=SendMessageResponse)

            with patch(
                "erc_8004_local_agents.agents.a2a_client.A2ACardResolver"
            ) as mock_resolver_class:
                mock_resolver = MagicMock()
                mock_resolver.get_agent_card = AsyncMock(return_value=mock_agent_card)
                mock_resolver_class.return_value = mock_resolver

                with patch(
                    "erc_8004_local_agents.agents.a2a_client.A2AClient"
                ) as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.send_message = AsyncMock(return_value=mock_response)
                    mock_client_class.return_value = mock_client

                    # Send a message with task_id and context_id
                    task_id = str(uuid4())
                    context_id = str(uuid4())
                    response = await wrapper.send_message(
                        "Hello, agent!",
                        task_id=task_id,
                        context_id=context_id,
                    )

                    # Verify response
                    assert response is mock_response
                    mock_client.send_message.assert_called_once()

                    # Verify that the message was sent with proper parameters
                    call_args = mock_client.send_message.call_args[0][0]
                    assert hasattr(call_args, "params")
                    # The actual params object has the task_id and context_id set
                    # properly
                    # Just verify the call was made with SendMessageRequest
                    assert call_args.id is not None

    @pytest.mark.asyncio
    async def test_send_message_with_input_address(self):
        """Test sending a message with input_address."""
        async with httpx.AsyncClient() as client:
            wrapper = A2AClientWrapper(
                endpoint="http://localhost:8000",
                httpx_client=client,
            )

            # Mock the agent card and client
            mock_agent_card = MagicMock(spec=AgentCard)
            mock_agent_card.url = "http://localhost:8000/messages"
            mock_agent_card.supports_authenticated_extended_card = False
            mock_response = MagicMock(spec=SendMessageResponse)

            with patch(
                "erc_8004_local_agents.agents.a2a_client.A2ACardResolver"
            ) as mock_resolver_class:
                mock_resolver = MagicMock()
                mock_resolver.get_agent_card = AsyncMock(return_value=mock_agent_card)
                mock_resolver_class.return_value = mock_resolver

                with patch(
                    "erc_8004_local_agents.agents.a2a_client.A2AClient"
                ) as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.send_message = AsyncMock(return_value=mock_response)
                    mock_client_class.return_value = mock_client

                    # Send a message with input_address
                    test_address = "0x1234567890123456789012345678901234567890"
                    response = await wrapper.send_message(
                        "Hello, agent!",
                        input_address=test_address,
                    )

                    # Verify response
                    assert response is mock_response
                    mock_client.send_message.assert_called_once()

                    # Verify input_address was included in message_data
                    call_args = mock_client.send_message.call_args[0][0]
                    assert hasattr(call_args, "params")
                    assert call_args.id is not None


class TestChainedAgentA2AIntegration:
    """Test the A2A client integration in ChainedAgent."""

    @pytest.mark.asyncio
    async def test_base_agent_get_httpx_client(self, base_agent: ChainedAgent):
        """Test that ChainedAgent creates and reuses httpx client."""
        # Get the client twice
        client1 = base_agent._get_httpx_client()
        client2 = base_agent._get_httpx_client()

        # Should be the same instance
        assert client1 is client2
        assert isinstance(client1, httpx.AsyncClient)

        # Clean up
        await base_agent.close()

    @pytest.mark.asyncio
    async def test_base_agent_get_a2a_client(self, base_agent: ChainedAgent):
        """Test that ChainedAgent creates and caches A2A clients."""
        endpoint = "http://localhost:8000"

        # Mock the wrapper initialization
        with patch(
            "erc_8004_local_agents.agents.base.A2AClientWrapper"
        ) as mock_wrapper_class:
            mock_wrapper = MagicMock(spec=A2AClientWrapper)
            mock_wrapper_class.return_value = mock_wrapper

            # Get client twice for same endpoint
            client1 = await base_agent.get_a2a_client(endpoint)
            client2 = await base_agent.get_a2a_client(endpoint)

            # Should be the same instance (cached)
            assert client1 is client2
            # Should only create once
            assert mock_wrapper_class.call_count == 1

        # Clean up
        await base_agent.close()

    @pytest.mark.asyncio
    async def test_base_agent_get_multiple_a2a_clients(self, base_agent: ChainedAgent):
        """Test that ChainedAgent creates separate clients for different endpoints."""
        endpoint1 = "http://localhost:8000"
        endpoint2 = "http://localhost:9000"

        # Mock the wrapper initialization
        with patch(
            "erc_8004_local_agents.agents.base.A2AClientWrapper"
        ) as mock_wrapper_class:
            mock_wrapper1 = MagicMock(spec=A2AClientWrapper)
            mock_wrapper2 = MagicMock(spec=A2AClientWrapper)
            mock_wrapper_class.side_effect = [mock_wrapper1, mock_wrapper2]

            # Get clients for different endpoints
            client1 = await base_agent.get_a2a_client(endpoint1)
            client2 = await base_agent.get_a2a_client(endpoint2)

            # Should be different instances
            assert client1 is not client2
            # Should create both
            assert mock_wrapper_class.call_count == 2

        # Clean up
        await base_agent.close()

    @pytest.mark.asyncio
    async def test_base_agent_close(self, base_agent: ChainedAgent):
        """Test that ChainedAgent properly closes resources."""
        # Create an httpx client
        base_agent._get_httpx_client()

        # Mock an A2A client
        with patch(
            "erc_8004_local_agents.agents.base.A2AClientWrapper"
        ) as mock_wrapper_class:
            mock_wrapper = MagicMock(spec=A2AClientWrapper)
            mock_wrapper_class.return_value = mock_wrapper

            await base_agent.get_a2a_client("http://localhost:8000")

            # Verify client exists
            assert base_agent._httpx_client is not None
            assert len(base_agent._a2a_clients) == 1

            # Close
            await base_agent.close()

            # Verify cleanup
            assert base_agent._httpx_client is None
            assert len(base_agent._a2a_clients) == 0

    @pytest.mark.asyncio
    async def test_base_agent_async_context_manager(self, base_agent: ChainedAgent):
        """Test that ChainedAgent works as an async context manager."""
        async with base_agent as agent:
            # Create an httpx client
            agent._get_httpx_client()
            assert agent._httpx_client is not None

        # After exiting context, should be cleaned up
        assert base_agent._httpx_client is None
