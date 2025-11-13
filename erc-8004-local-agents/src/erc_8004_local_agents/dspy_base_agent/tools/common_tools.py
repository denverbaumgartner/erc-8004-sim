# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
import random

# external packages
import dspy

# internal packages

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_random_number(lower_bound: int, upper_bound: int) -> int:
    """Get a random number between lower_bound and upper_bound."""
    return random.randint(lower_bound, upper_bound)


def get_random_number_tool() -> dspy.Tool:
    """Get a random number between 0 and 100."""
    return dspy.Tool(
        func=get_random_number,
        name="random_number",
        desc="Get a random number between lower_bound and upper_bound.",
        args={
            "lower_bound": {"type": "int", "description": "The lower bound"},
            "upper_bound": {"type": "int", "description": "The upper bound"},
        },
        arg_types={
            "lower_bound": int,
            "upper_bound": int,
        },
        arg_desc={
            "lower_bound": "The lower bound",
            "upper_bound": "The upper bound",
        },
    )
