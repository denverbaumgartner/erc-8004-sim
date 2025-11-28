# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Optional

# external packages
import dspy
from erc8004 import ERC8004Client

# internal packages

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_feedback_tool(
    client: ERC8004Client,
) -> dspy.Tool:
    """Get the feedback tool."""
    return dspy.Tool(
        func=client.reputation.give_feedback,
        name="give_feedback",
        desc=(
            "Give feedback to an agent. Must submit a valid feedback auth "
            "(will be returned by the agent being reviewed as a part of the "
            "response)."
        ),
        args={
            "agent_id": {"type": "int", "description": "The agent ID"},
            "score": {"type": "int", "description": "The score (0-100)"},
            "feedback_auth": {
                "type": "str",
                "description": (
                    "The feedback auth (will be returned by the agent being "
                    "reviewed as a part of the response)"
                ),
            },
            "tag1": {"type": "str", "description": "Optional: The tag1"},
            "tag2": {"type": "str", "description": "Optional: The tag2"},
            "feedback_uri": {
                "type": "str",
                "description": "Optional: The feedback URI",
            },
            "feedback_hash": {
                "type": "str",
                "description": "Optional: The feedback hash",
            },
        },
        arg_types={
            "agent_id": int,
            "score": int,
            "feedback_auth": str,
            "tag1": Optional[str],
            "tag2": Optional[str],
            "feedback_uri": Optional[str],
            "feedback_hash": Optional[str],
        },
        arg_desc={
            "agent_id": "The agent ID",
            "score": "The score (0-100)",
            "feedback_auth": "The feedback auth",
            "tag1": "Optional: The tag1",
            "tag2": "Optional: The tag2",
            "feedback_uri": "Optional: The feedback URI",
            "feedback_hash": "Optional: The feedback hash",
        },
    )
