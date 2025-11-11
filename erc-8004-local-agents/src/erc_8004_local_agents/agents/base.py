# system packages
import logging
import os
import time
from typing import Optional

# external packages
import httpx
from erc8004 import ERC8004Client, Web3Adapter
from eth_account import Account
from web3 import Web3

# internal packages
from erc_8004_local_agents.agents.a2a_client import A2AClientWrapper
from erc_8004_local_agents.dspy_base_agent import AgentFactory, BaseAgent
from erc_8004_local_agents.dspy_base_agent.tools.external_agent_tools import (
    create_external_agent_review_tool,
    create_external_agent_tool,
)
from erc_8004_local_agents.types.types import AgentConfig, AgentResponse

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ChainedAgent:
    """Base class for all agents."""

    def __init__(
        self,
        agent_config: AgentConfig,
        w3: Web3,
        adapter: Web3Adapter,
        client: ERC8004Client,
        dspy_agent: Optional[BaseAgent] = None,
    ):
        self.agent_config = agent_config
        self.w3 = w3
        self.adapter = adapter
        self.client = client
        self.dspy_agent = dspy_agent

        # initialized agent information
        self.agent_id = None

        # TUI status tracking
        self.current_status: str = "Idle"

        # A2A client management
        self._httpx_client: Optional[httpx.AsyncClient] = None
        self._a2a_clients: dict[str, A2AClientWrapper] = {}

    @classmethod
    def from_config(
        cls,
        agent_config: AgentConfig,
        web3: Optional[Web3] = None,
        account: Optional[Account] = None,
    ) -> "ChainedAgent":
        """Set up ERC-8004 client components and create a ChainedAgent instance.

        This is a class method to allow flexible instantiation, particularly
        useful for testing with local networks.

        Args:
            agent_config: Agent configuration
            web3: Optional Web3 instance (for testing)
            account: Optional Account instance (for testing)

        Returns:
            An initialized ChainedAgent instance
        """
        # we make these optional so that we can use the local network for testing
        if web3 is None:
            w3 = Web3(Web3.HTTPProvider(agent_config.network_config.chain_rpc))
        else:
            w3 = web3

        if account is None:
            adapter = Web3Adapter(
                web3=w3, private_key=agent_config.wallet_config.private_key
            )
        else:
            adapter = Web3Adapter(web3=w3, account=account)

        client = ERC8004Client(
            adapter=adapter,
            addresses={
                "identityRegistry": (
                    agent_config.contract_registry.identity_registry_address
                ),
                "reputationRegistry": (
                    agent_config.contract_registry.reputation_registry_address
                ),
                "validationRegistry": (
                    agent_config.contract_registry.validation_registry_address
                ),
                "chainId": agent_config.network_config.chain_id,
            },
        )

        # Create DSPy agent if config is provided
        dspy_agent = None
        if agent_config.dspy_config:
            # Use environment variable for API key if available
            api_key_env = os.getenv("OPENROUTER_API_KEY")
            if api_key_env:
                logger.info("Using OPENROUTER_API_KEY from environment")
                agent_config.dspy_config.api_key = api_key_env

            logger.info("Creating DSPy agent from configuration")
            dspy_agent = AgentFactory.create_agent(agent_config.dspy_config, client)
            logger.info(f"DSPy agent created: {agent_config.dspy_config.name}")

        return cls(
            agent_config=agent_config,
            w3=w3,
            adapter=adapter,
            client=client,
            dspy_agent=dspy_agent,
        )

    async def configure_dspy_agent_tools(self):
        """Asynchronously configures and sets tools for the DSPy agent.

        This method connects to peer agents specified in the agent configuration and
        creates tools that allow the DSPy agent to communicate with them. Supports both
        peer_agent_ids (for on-chain registered agents) and peer_agent_uris (for any
        agent at a URI).
        """
        if not self.dspy_agent or not self.agent_config.dspy_config:
            logger.info("No DSPy agent or config found, skipping tool configuration")
            return

        self.current_status = "Configuring tools"
        peer_ids = self.agent_config.dspy_config.peer_agent_ids or []
        peer_uris = self.agent_config.dspy_config.peer_agent_uris or []

        if not peer_ids and not peer_uris:
            logger.info("No peer agents configured (neither IDs nor URIs)")
            self.current_status = "Idle"
            return

        # Start with only the agent's initial tools (filter out any existing
        # external agent tools)
        existing_tools = self.dspy_agent._tools or []
        tools = [
            tool
            for tool in existing_tools
            if not (
                tool.name
                and (
                    tool.name.startswith("execute_request_to_")
                    or tool.name.startswith("execute_and_review_request_to_")
                )
            )
        ]

        total_peers = len(peer_ids) + len(peer_uris)
        logger.info(f"Configuring tools for {total_peers} peer agent(s)")

        # Process peer_agent_ids first
        for agent_id in peer_ids:
            try:
                logger.info(f"Connecting to peer agent with ID {agent_id}")
                a2a_client = await self.connect_to_agent(str(agent_id))

                # Ensure client is initialized to fetch agent card
                await a2a_client._ensure_initialized()

                # Verify agent card is available
                if not a2a_client.agent_card:
                    logger.warning(
                        f"No agent card available for agent ID {agent_id}, skipping"
                    )
                    continue

                agent_card = a2a_client.agent_card

                # Pass instantiated clients directly to the factory
                # Use the actual address from the adapter (used for signing
                # transactions)
                input_address = self.adapter.get_address()
                assert input_address is not None
                logger.debug(f"Using input_address from adapter: {input_address}")

                request_tool = create_external_agent_tool(
                    a2a_client=a2a_client,
                    input_address=input_address,
                )

                # Get LM from the DSPy agent if available
                lm = getattr(self.dspy_agent, "lm", None)

                review_tool = create_external_agent_review_tool(
                    a2a_client=a2a_client,
                    erc8004_client=self.client,
                    input_address=input_address,
                    agent_id=agent_id,  # Include agent_id for on-chain feedback
                    lm=lm,  # Pass LM for automated review
                )

                tools.extend(
                    [request_tool, review_tool]
                )  # tools.extend([request_tool, review_tool])
                logger.info(
                    f"Created 2 tools for agent ID {agent_id} ({agent_card.name})"
                )

            except Exception as e:
                logger.error(f"Failed to create tools for agent ID {agent_id}: {e}")

        # Process peer_agent_uris
        for agent_uri in peer_uris:
            try:
                logger.info(f"Connecting to peer agent at {agent_uri}")
                a2a_client = await self.get_a2a_client(agent_uri)

                # Ensure client is initialized to fetch agent card
                await a2a_client._ensure_initialized()

                # Verify agent card is available
                if not a2a_client.agent_card:
                    logger.warning(
                        f"No agent card available for agent at {agent_uri}, skipping"
                    )
                    continue

                agent_card = a2a_client.agent_card

                # Pass instantiated clients directly to the factory
                # Use the actual address from the adapter (used for signing
                # transactions)
                input_address = self.adapter.get_address()
                assert input_address is not None
                logger.debug(f"Using input_address from adapter: {input_address}")

                request_tool = create_external_agent_tool(
                    a2a_client=a2a_client,
                    input_address=input_address,
                )

                # Get LM from the DSPy agent if available
                lm = getattr(self.dspy_agent, "lm", None)

                review_tool = create_external_agent_review_tool(
                    a2a_client=a2a_client,
                    erc8004_client=self.client,
                    input_address=input_address,
                    agent_id=None,  # No agent_id for URI-based connections
                    lm=lm,  # Pass LM for automated review
                )

                tools.extend(
                    [request_tool, review_tool]
                )  # tools.extend([request_tool, review_tool])
                logger.info(
                    f"Created 2 tools for agent at {agent_uri} ({agent_card.name})"
                )

            except Exception as e:
                logger.error(f"Failed to create tools for agent at {agent_uri}: {e}")

        if tools:
            self.dspy_agent.set_tools(tools)
            logger.info(f"DSPy agent configured with {len(tools)} external agent tools")
        else:
            logger.info("No tools were created for external agents")

        self.current_status = "Idle"

    def _create_feedback_auth(self, client_address: str) -> str:
        """Create a signed feedback auth for the agent for a given client.

        Args:
            client_address: The address of the client to create feedback auth for

        Returns:
            A signed feedback auth string

        Raises:
            ValueError: If agent is not registered
        """
        if self.agent_id is None:
            raise ValueError(
                "Agent not registered. Please call register_agent() first."
            )

        chain_id = self.client.get_chain_id()
        agent_owner_address = self.adapter.get_address()
        assert agent_owner_address is not None

        # Get the last feedback index for this client
        last_index = self.client.reputation.get_last_index(
            self.agent_id, client_address
        )

        # Create feedbackAuth, valid for 1 hour
        feedback_auth = self.client.reputation.create_feedback_auth(
            self.agent_id,
            client_address,
            last_index + 1,  # Allow next feedback
            int(time.time()) + 3600,  # Valid for 1 hour
            chain_id,
            agent_owner_address,
        )

        # Sign the feedbackAuth
        signed_auth = self.client.reputation.sign_feedback_auth(feedback_auth)
        return signed_auth

    def process_request(
        self, input: str, input_address: Optional[str] = None
    ) -> "AgentResponse":
        """Process a request using the DSPy agent.

        Args:
            input: Input string to process
            input_address: Optional address of the client for feedback auth

        Returns:
            AgentResponse containing output and optional feedback_auth

        Raises:
            ValueError: If DSPy agent is not configured
        """
        if not self.dspy_agent:
            raise ValueError(
                "DSPy agent not configured. Please provide dspy_config in AgentConfig."
            )

        # Note: Status is managed by the caller (executor or simulation loop)

        # Generate feedback_auth if input_address is provided
        feedback_auth = None
        if input_address:
            try:
                feedback_auth = self._create_feedback_auth(input_address)
                logger.debug(f"Generated feedback_auth for {input_address}")
            except Exception as e:
                logger.warning(f"Failed to generate feedback_auth: {e}")

        logger.info(f"Processing request with DSPy agent: {input[:50]}...")
        result = self.dspy_agent(input=input)
        logger.info("Request processed successfully")

        return AgentResponse(output=result.output, feedback_auth=feedback_auth)

    def register_agent(self):
        # TODO: we should add a check to see if the agent is already registered
        self.current_status = "Registering"
        try:
            result = self.client.identity.register_with_uri(
                token_uri=self.agent_config.agent_card.url,
            )
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            self.current_status = "Idle"
            raise e

        self.agent_id = result["agentId"]
        self.current_status = "Idle"
        return result

    async def connect_to_agent(self, agent_id: str) -> A2AClientWrapper:
        """Connect to an agent from the identity registry. Takes the agent's ID and
        returns an A2AClientWrapper. Assumes the agent is a2a compatible.

        Args:
            agent_id: The ID of the agent to connect to

        Returns:
            An A2AClientWrapper instance for communicating with the agent
        """

        agent_uri = self.client.identity.get_token_uri(int(agent_id))
        return await self.get_a2a_client(agent_uri)

    def _get_httpx_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx.AsyncClient instance.

        Returns:
            Shared httpx.AsyncClient instance for all A2A communications
        """
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient()
            logger.info("Created new httpx.AsyncClient instance")
        return self._httpx_client

    async def get_a2a_client(self, endpoint: str) -> A2AClientWrapper:
        """Get or create an A2A client wrapper for the given endpoint.

        This method implements lazy initialization and caching of A2A clients.
        Each endpoint gets a single cached client instance that is reused.

        Args:
            endpoint: Base URL of the target agent (e.g., "http://localhost:8000")

        Returns:
            A2AClientWrapper instance for communicating with the agent at the endpoint
        """
        # Check cache first
        if endpoint in self._a2a_clients:
            logger.debug(f"Returning cached A2A client for {endpoint}")
            return self._a2a_clients[endpoint]

        # Create new client wrapper
        logger.info(f"Creating new A2A client for {endpoint}")
        client_wrapper = A2AClientWrapper(
            endpoint=endpoint,
            httpx_client=self._get_httpx_client(),
        )

        # Cache and return
        self._a2a_clients[endpoint] = client_wrapper
        return client_wrapper

    async def send_message_to_agent(
        self,
        endpoint: str,
        text: str,
        task_id: Optional[str] = None,
        context_id: Optional[str] = None,
    ):
        """Send a message to another agent via A2A protocol.

        Args:
            endpoint: Base URL of the target agent
            text: Message text to send
            task_id: Optional task ID for multi-turn conversations
            context_id: Optional context ID for conversation continuity

        Returns:
            SendMessageResponse from the target agent
        """
        client = await self.get_a2a_client(endpoint)

        # Include this agent's wallet address as input_address
        input_address = self.agent_config.wallet_config.address

        response = await client.send_message(
            text=text,
            task_id=task_id,
            context_id=context_id,
            input_address=input_address,
        )

        return response

    async def close(self) -> None:
        """Clean up resources, including the httpx client.

        This method should be called when the agent is shutting down to ensure proper
        cleanup of HTTP connections.
        """
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
            logger.info("Closed httpx.AsyncClient")
            self._httpx_client = None
        self._a2a_clients.clear()

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager protocol."""
        await self.close()
