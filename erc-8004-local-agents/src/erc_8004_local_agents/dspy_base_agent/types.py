"""Configuration types for DSPy agents."""

from pydantic import BaseModel


class DSPyModelConfig(BaseModel):
    """Configuration for a language model."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 150
    cache: bool = False


class DSPyAgentConfig(BaseModel):
    """Configuration for a DSPy agent."""

    agent_type: str
    name: str
    description: str
    main_model: DSPyModelConfig
    adapter_model: DSPyModelConfig
    api_key: str
    tools: list[str] = []
    peer_agent_ids: list[int] = []
    peer_agent_uris: list[str] = []


class AgentResponse(BaseModel):
    """Response from a DSPy agent."""

    output: str
