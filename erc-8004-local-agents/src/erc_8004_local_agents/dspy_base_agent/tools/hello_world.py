# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0
"""Hello World tool for DSPy agents."""

# system packages
import logging

# external packages
import dspy

# internal packages

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def greet(name: str) -> str:
    """Greets the person with the given name.

    Args:
        name: Name of the person to greet

    Returns:
        Greeting message
    """
    logger.info(f"greet tool called with name: {name}")
    greeting = f"Hello, {name}!"
    logger.debug(f"greet tool returning: {greeting}")
    return greeting


hello_world_tool = dspy.Tool(
    func=greet,
    name="greet",
    desc="Greets a person.",
)
