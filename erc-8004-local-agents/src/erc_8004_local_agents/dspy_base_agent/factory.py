"""Factory for creating DSPy agents."""

# system packages
import logging
from typing import Optional

# external packages
from erc8004 import ERC8004Client

from erc_8004_local_agents.dspy_base_agent.agents.feedback_agent import FeedbackAgent

# internal packages
from erc_8004_local_agents.dspy_base_agent.agents.hello_world import HelloWorldAgent
from erc_8004_local_agents.dspy_base_agent.base import BaseAgent
from erc_8004_local_agents.dspy_base_agent.tools.factory import ToolFactory
from erc_8004_local_agents.dspy_base_agent.types import DSPyAgentConfig

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentFactory:
    """Factory for creating and managing DSPy agents."""

    _agents = {
        "hello_world": HelloWorldAgent,
        "feedback_agent": FeedbackAgent,
    }

    @classmethod
    def create_agent(
        cls, config: DSPyAgentConfig, client: Optional[ERC8004Client] = None
    ) -> BaseAgent:
        """Create an agent based on the configuration.

        Args:
            config: Agent configuration
            client: Optional ERC8004Client for tools that require blockchain access

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type is unknown
        """
        logger.info(f"AgentFactory: Creating agent of type '{config.agent_type}'")
        logger.debug(f"Agent name: {config.name}")
        logger.debug(f"Agent description: {config.description}")

        agent_class = cls._agents.get(config.agent_type)
        if not agent_class:
            logger.error(f"Unknown agent type: {config.agent_type}")
            logger.debug(f"Available agent types: {list(cls._agents.keys())}")
            raise ValueError(f"Unknown agent type: {config.agent_type}")

        logger.debug(f"Found agent class: {agent_class.__name__}")
        logger.debug("Instantiating agent...")
        agent = agent_class(config)
        logger.info(f"Agent instance created: {config.name}")

        # Get tools from ToolFactory and set them on the agent
        if config.tools:
            logger.info(f"Requesting {len(config.tools)} tool(s) from ToolFactory")
            logger.debug(f"Tool names: {config.tools}")
            tool_factory = ToolFactory(client)
            tools = tool_factory.get_tools(config.tools)
            logger.debug("Setting tools on agent...")
            agent.set_tools(tools)
        else:
            logger.info("No tools configured for this agent")

        logger.info(f"AgentFactory: Agent '{config.name}' created successfully")
        return agent
