# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""Base server for running A2A agent."""

import logging
from typing import Union

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from erc_8004_local_agents.agents.base import ChainedAgent
from erc_8004_local_agents.agents.base_executor import BaseExecutor
from erc_8004_local_agents.types.types import AgentConfig

logger = logging.getLogger(__name__)


async def health(request: Request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


class BaseServer:
    """Server that runs a ChainedAgent with A2A protocol."""

    def __init__(
        self,
        config_or_agent: Union[AgentConfig, ChainedAgent],
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        """Initialize the server with agent configuration or instance.

        Args:
            config_or_agent: Either an AgentConfig or ChainedAgent instance
            host: Host to bind server (default: 0.0.0.0)
            port: Port to bind server (default: 8000)
        """
        self.host = host
        self.port = port

        # Handle both AgentConfig and ChainedAgent
        if isinstance(config_or_agent, ChainedAgent):
            self.agent = config_or_agent
            self.config = config_or_agent.agent_config
            logger.info(
                "Initializing BaseServer with existing agent: "
                f"{self.config.agent_card.name}"
            )
        else:
            self.config = config_or_agent
            logger.info(
                f"Initializing BaseServer for agent: {config_or_agent.agent_card.name}"
            )
            # Create ChainedAgent from config
            self.agent = ChainedAgent.from_config(config_or_agent)
            logger.info("ChainedAgent created successfully")

        # Create executor
        self.executor = BaseExecutor(self.agent)

        # Create task store
        self.task_store = InMemoryTaskStore()
        logger.info("InMemoryTaskStore initialized")

        # Create request handler
        self.request_handler = DefaultRequestHandler(
            agent_executor=self.executor,
            task_store=self.task_store,
        )
        logger.info("DefaultRequestHandler created")

        # Create A2A application
        app_builder = A2AStarletteApplication(
            agent_card=self.config.agent_card,
            http_handler=self.request_handler,
        )
        self.app = app_builder.build()
        logger.info("A2AStarletteApplication initialized")

        # Add health check route
        self.app.routes.append(Route("/health", health))
        logger.info("Health check endpoint added at /health")

    def run(self) -> None:
        """Start the uvicorn server."""
        logger.info(f"Starting server on {self.host}:{self.port}")

        # Configure uvicorn to use our logging system
        log_config = uvicorn.config.LOGGING_CONFIG  # type: ignore[attr-defined]
        log_config["formatters"]["default"][
            "fmt"
        ] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_config["formatters"]["access"][
            "fmt"
        ] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        logger.info(
            "[SERVER] About to start uvicorn for "
            f"{self.agent.agent_config.agent_card.name}"
        )
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_config=log_config,
            access_log=True,
        )
        logger.info(
            f"[SERVER] Uvicorn stopped for {self.agent.agent_config.agent_card.name}"
        )
