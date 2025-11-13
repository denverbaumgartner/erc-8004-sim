<!--
SPDX-FileCopyrightText: 2025 Semiotic Labs

SPDX-License-Identifier: Apache-2.0
-->

# DSPy Base Agent Framework

This document provides instructions on how to extend the DSPy base agent framework by adding new agents and tools, and how to configure them.

## Table of Contents
- [Adding a New Agent](#adding-a-new-agent)
- [Adding a New Tool](#adding-a-new-tool)
- [Configuration](#configuration)

## Adding a New Agent

To add a new agent to the framework, follow these steps:

1.  **Create a New Agent File**:
    Create a new Python file in the `src/erc_8004_local_agents/dspy_base_agent/agents/` directory. For example, `my_agent.py`.

2.  **Define a Signature**:
    In your new file, define a signature class that inherits from `dspy.Signature`. This class specifies the input and output fields for your agent.

    ```python
    import dspy

    class MyAgentSignature(dspy.Signature):
        """A brief description of your agent's purpose."""
        input: str = dspy.InputField(desc="Description of the input.")
        output: str = dspy.OutputField(desc="Description of the output.")
    ```

3.  **Implement the Agent**:
    Create a class for your agent that inherits from `BaseAgent`. You must implement the `_create_signature`, `_create_agent_module`, and `forward` methods.

    ```python
    from ..base import BaseAgent
    import dspy

    class MyAgent(BaseAgent):
        def _create_signature(self) -> type[dspy.Signature]:
            return MyAgentSignature

        def _create_agent_module(self, signature: type[dspy.Signature]) -> dspy.Module:
            # For example, using a ReAct module
            return dspy.ReAct(signature, tools=self._tools)

        def forward(self, input: str) -> dspy.Prediction:
            return self._agent(input=input)
    ```

4.  **Register the Agent in the Factory**:
    Open `src/erc_8004_local_agents/dspy_base_agent/factory.py` and register your new agent in the `AgentFactory`.

    -   Import your new agent class.
    -   Add an entry to the `_agents` dictionary, mapping a unique string key to your agent class. This key will be used as the `agent_type` in the configuration file.

    ```python
    # In factory.py
    ...
    from erc_8004_local_agents.dspy_base_agent.agents.my_agent import MyAgent
    ...

    class AgentFactory:
        _agents = {
            "hello_world": HelloWorldAgent,
            "feedback_agent": FeedbackAgent,
            "my_agent": MyAgent,  # Add your agent here
        }
        ...
    ```

## Adding a New Tool

To add a new tool for agents to use, follow these steps:

1.  **Create a New Tool File**:
    It's best practice to create a new Python file in `src/erc_8004_local_agents/dspy_base_agent/tools/` (e.g., `my_tool.py`), or add to an existing relevant file.

2.  **Define the Tool's Functionality**:
    Write the Python function that your tool will execute. Then, wrap it in a `dspy.Tool` instance.

    ```python
    # In my_tool.py
    import dspy

    def my_tool_function(arg1: str) -> str:
        """Description of what my tool does."""
        return f"You passed {arg1}"

    my_awesome_tool = dspy.Tool(
        func=my_tool_function,
        name="my_awesome_tool",
        desc="A description for the LLM of what this tool does.",
    )
    ```

3.  **Register the Tool in the Factory**:
    Open `src/erc_8004_local_agents/dspy_base_agent/tools/factory.py` and register your new tool in the `ToolFactory`.

    -   Import your new tool instance.
    -   Add an entry to the `_tool_mapping` dictionary (for general tools) or `_client_tool_mapping` (if the tool requires an `ERC8004Client` instance). The key is a string that will be used in the agent configuration.

    ```python
    # In tools/factory.py
    ...
    from erc_8004_local_agents.dspy_base_agent.tools.my_tool import my_awesome_tool
    ...

    class ToolFactory:
        def __init__(self, client: ERC8004Client):
            ...
            self._tool_mapping = {
                "hello_world_tool": hello_world_tool,
                "random_number_tool": get_random_number_tool(),
                "my_awesome_tool": my_awesome_tool, # Add your tool here
            }
            ...
    ```

## Configuration

The agent's behavior is configured via a YAML file, as seen in `configs/agents/agent_00.yaml`. The `dspy_config` section is crucial for setting up the DSPy agent.

Here is an example of the `dspy_config` section:

```yaml
dspy_config:
  agent_type: "hello_world"
  api_key: "your-api-key"
  main_model:
    model: "openrouter/google/gemini-2.5-flash"
    temperature: 0.7
    max_tokens: 15000
    cache: true
  adapter_model:
    model: "openrouter/google/gemini-2.5-flash"
    temperature: 0.7
    max_tokens: 15000
    cache: true
  tools:
    - "hello_world_tool"
    - "random_number_tool"
```

### `dspy_config` Parameters:

-   `agent_type`: (Required) A string that matches one of the keys in the `AgentFactory._agents` dictionary. This determines which agent class will be instantiated.
-   `api_key`: Your API key for the language model service.
-   `main_model` & `adapter_model`: These objects configure the primary and adapter language models for the agent.
    -   `model`: The identifier for the language model (e.g., from OpenRouter).
    -   `temperature`: The creativity of the model's responses.
    -   `max_tokens`: The maximum number of tokens in a response.
    -   `cache`: A boolean to enable or disable caching of model responses.
-   `tools`: A list of strings, where each string must match a key in the `ToolFactory`'s tool mappings. These are the tools that the agent will be able to use.
