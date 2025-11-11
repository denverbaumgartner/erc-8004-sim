"""Factory for creating DSPy tools."""

# system packages
import logging

# external packages
import dspy
from erc8004 import ERC8004Client

from erc_8004_local_agents.dspy_base_agent.tools.common_tools import (
    get_random_number_tool,
)
from erc_8004_local_agents.dspy_base_agent.tools.erc_8004_tools import get_feedback_tool

# internal packages
from erc_8004_local_agents.dspy_base_agent.tools.hello_world import hello_world_tool

logger = logging.getLogger(__name__)


class ToolFactory:
    """Factory for creating and managing DSPy tools."""

    def __init__(self, client: ERC8004Client):
        self.client = client

        # static tools
        self._tool_mapping = {
            "hello_world_tool": hello_world_tool,
            "random_number_tool": get_random_number_tool(),
        }

        # context-aware tools
        if self.client is not None:
            self._client_tool_mapping = {
                "give_feedback_tool": get_feedback_tool(self.client),
            }
        else:
            self._client_tool_mapping = {}

        self.all_tool_mapping = {
            **self._tool_mapping,
            **self._client_tool_mapping,
        }
        logger.debug(f"Available tools: {list(self.all_tool_mapping.keys())}")

    def get_tools(self, tool_names: list[str]) -> list[dspy.Tool]:
        """Get tools by name.

        Args:
            tool_names: List of tool names to retrieve

        Returns:
            List of DSPy tools

        Raises:
            KeyError: If a tool name is not found
        """
        logger.info(f"ToolFactory: Retrieving {len(tool_names)} tool(s)")
        logger.debug(f"Requested tools: {tool_names}")
        logger.debug(f"Available tools: {list(self.all_tool_mapping.keys())}")

        tools = []
        for name in tool_names:

            if name in self._client_tool_mapping:
                if self.client is None:
                    logger.error(f"Tool '{name}' requires a client")
                    raise KeyError(f"Tool '{name}' not found")
                tool = self.all_tool_mapping[name]
                logger.debug(f"Retrieved tool: {tool.name} - {tool.desc}")
                tools.append(tool)
                continue

            elif name in self.all_tool_mapping:
                tool = self.all_tool_mapping[name]
                logger.debug(f"Retrieved tool: {tool.name} - {tool.desc}")
                tools.append(tool)
                continue
            else:
                logger.error(f"Tool '{name}' not found in tool mapping")
                logger.debug(f"Available tools: {list(self.all_tool_mapping.keys())}")
                raise KeyError(f"Tool '{name}' not found")

        logger.info(f"ToolFactory: Successfully retrieved {len(tools)} tool(s)")
        return tools
