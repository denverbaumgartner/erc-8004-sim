# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from pathlib import Path
from typing import Any, Dict, List

# external packages
import polars as pl
from web3 import Web3
from web3.types import TxReceipt

# internal packages


# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def decode_logs_from_receipt(
    receipt: TxReceipt, contract_objects: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Decode logs from a transaction receipt using contract ABIs.

    Args:
        receipt: Transaction receipt containing logs
        contract_objects: Dictionary of contract name to web3.contract instances

    Returns:
        List of decoded event logs as dictionaries
    """
    all_decoded_logs = []

    # Ethereum tester returns receipts in a different format, need to access
    # logs directly
    logs = receipt.get("logs", [])
    if not logs:
        return all_decoded_logs

    # Build a map of checksummed address to contract for faster lookup
    address_to_contract = {}
    for contract_name, contract in contract_objects.items():
        checksum_addr = Web3.to_checksum_address(contract.address)
        address_to_contract[checksum_addr] = (contract_name, contract)

    # Process each log
    for log in logs:
        # Convert snake_case keys to camelCase for web3.py compatibility
        # Ethereum Tester uses snake_case, but web3.py expects camelCase
        normalized_log = {
            "address": log.get("address"),
            "blockHash": log.get("block_hash"),
            "blockNumber": log.get("block_number"),
            "data": log.get("data"),
            "logIndex": log.get("log_index"),
            "topics": log.get("topics", []),
            "transactionHash": log.get("transaction_hash"),
            "transactionIndex": log.get("transaction_index"),
        }

        log_address = Web3.to_checksum_address(normalized_log.get("address", ""))

        # Only try to decode if this log is from one of our known contracts
        if log_address not in address_to_contract:
            continue

        contract_name, contract = address_to_contract[log_address]

        # Try each event in this contract
        for event in contract.events:
            try:
                # Use process_log to decode the individual log
                decoded = event().process_log(normalized_log)
                # Convert EventData (AttributeDict) to dict for easier processing
                log_dict = dict(decoded)
                log_dict["contract_name"] = contract_name
                log_dict["event_name"] = decoded["event"]
                all_decoded_logs.append(log_dict)
                break  # Successfully decoded, don't try other events
            except Exception:
                # This event doesn't match, try next one
                # Uncomment for debugging:
                # print(f"Failed to decode with {event.event_name}: {e}")
                pass

    return all_decoded_logs


def process_event_logs(file_path: str | Path) -> Dict[str, pl.DataFrame]:
    """Process event logs from a JSON file into separate DataFrames by event type.

    This function loads a JSON file containing decoded event logs and creates
    a separate polars DataFrame for each event type. The 'args' field is
    automatically unpacked into individual columns for each event type.

    Args:
        file_path: Path to the JSON file containing event logs

    Returns:
        Dictionary mapping event names to their corresponding DataFrames.
        Each DataFrame contains common metadata columns plus event-specific
        columns unpacked from the 'args' field.

    Example:
        >>> event_dfs = process_event_logs("erc_8004_sim_history.json")
        >>> transfer_df = event_dfs.get("Transfer")
        >>> feedback_df = event_dfs.get("NewFeedback")
        >>> avg_score = feedback_df.filter(pl.col("agentId") == 0)["score"].mean()
    """
    import json

    # Load the JSON file using standard json module to handle large numbers
    with open(file_path, "r") as f:
        data = json.load(f)

    # Convert to polars DataFrame
    df = pl.DataFrame(data)

    # Get unique event names
    event_names = df["event_name"].unique().to_list()

    # Create a dictionary to store DataFrames for each event type
    event_dfs = {}

    for event_name in event_names:
        # Filter for this event type
        event_df = df.filter(pl.col("event_name") == event_name)

        # Unnest the 'args' struct to flatten it into columns
        event_df = event_df.unnest("args")

        # Store in dictionary
        event_dfs[event_name] = event_df

        logger.info(f"Processed {len(event_df)} '{event_name}' events")

    return event_dfs
