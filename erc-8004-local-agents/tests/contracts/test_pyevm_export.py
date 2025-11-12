# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any, Dict, List

# external packages
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from web3.types import TxReceipt

# internal packages
from erc_8004_local_agents.data.evm_export import save_history_to_json


def test_export_transactions(
    agent_factory,
    ethereum_tester_provider: EthereumTesterProvider,
):
    """Test that we can export all blocks and transactions from the local py-evm
    instance."""
    # Get a couple of agents and register them to create transactions
    agent_00 = agent_factory["agent_00"]["agent"]
    agent_01 = agent_factory["agent_01"]["agent"]
    agent_00.register_agent()
    agent_01.register_agent()

    tester = ethereum_tester_provider.ethereum_tester
    assert tester is not None

    # Get all transactions from all blocks
    all_transactions = []
    all_blocks = []
    current_block = tester.get_block_by_number("latest")
    for block_num in range(0, current_block["number"] + 1):
        # type: ignore[arg-type]
        block = tester.get_block_by_number(block_num, full_transactions=True)
        all_blocks.append(block)
        all_transactions.extend(block["transactions"])

    # Export to a file for review
    output_dir = Path("pyevm_export")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "evm_export.json"

    export_data = {
        "blocks": all_blocks,
        "transactions": all_transactions,
    }

    def default_serializer(o):
        if isinstance(o, bytes):
            return o.hex()
        raise TypeError(
            f"Object of type {o.__class__.__name__} is not JSON serializable"
        )

    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2, default=default_serializer)

    print(
        f"Exported {len(all_blocks)} blocks and {len(all_transactions)} "
        f"transactions to {output_path}"
    )

    # some basic assertions
    assert len(all_blocks) > 0
    assert len(all_transactions) > 0


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


def test_decode_exported_transactions(
    contract_factory,
    agent_factory,
    ethereum_tester_provider: EthereumTesterProvider,
):
    """Test that we can decode all transactions from the local py-evm instance into
    structured events using the deployed contract ABIs."""
    # Create web3 instance and contract objects
    web3 = Web3(ethereum_tester_provider)
    deployed_contracts = contract_factory

    contract_objects = {}
    for name, details in deployed_contracts.items():
        contract_objects[name] = web3.eth.contract(
            address=details["address"], abi=details["abi"]
        )

    # Generate some transactions by registering agents
    agent_00 = agent_factory["agent_00"]["agent"]
    agent_01 = agent_factory["agent_01"]["agent"]
    agent_00.register_agent()
    agent_01.register_agent()

    # Retrieve all transaction receipts
    tester = ethereum_tester_provider.ethereum_tester
    assert tester is not None
    all_receipts = []
    current_block = tester.get_block_by_number("latest")
    for block_num in range(0, current_block["number"] + 1):
        block = tester.get_block_by_number(block_num)  # type: ignore[arg-type]
        for tx_hash in block["transactions"]:
            receipt = tester.get_transaction_receipt(tx_hash)
            all_receipts.append(receipt)

    # Decode logs from all receipts
    all_decoded_logs = []
    for receipt in all_receipts:
        decoded_logs = decode_logs_from_receipt(receipt, contract_objects)
        all_decoded_logs.extend(decoded_logs)

    # Assert that we have decoded some logs
    assert len(all_decoded_logs) > 0, "Should have decoded at least some event logs"

    # Count events by type for reporting
    event_counts = {}
    for log in all_decoded_logs:
        event_name = log.get("event_name", "Unknown")
        event_counts[event_name] = event_counts.get(event_name, 0) + 1

    # Export decoded logs to JSON for review
    output_dir = Path("pyevm_export")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "decoded_evm_export.json"

    def default_serializer(o):
        """Custom JSON serializer for bytes and other non-serializable types."""
        if isinstance(o, bytes):
            return "0x" + o.hex()
        raise TypeError(
            f"Object of type {o.__class__.__name__} is not JSON serializable"
        )

    with open(output_path, "w") as f:
        json.dump(all_decoded_logs, f, indent=2, default=default_serializer)

    print(
        f"\n✓ Decoded {len(all_decoded_logs)} event logs from "
        f"{len(all_receipts)} transactions"
    )
    print(f"  Event breakdown: {event_counts}")
    print(f"  Exported to: {output_path}")

    # Additional assertions to verify we decoded expected events
    # The IdentityRegistry emits "Registered" events (not "AgentRegistered")
    assert (
        "Registered" in event_counts
    ), "Should have decoded Registered events from IdentityRegistry"
    assert event_counts["Registered"] >= 2, "Should have at least 2 agent registrations"


def test_save_history_to_json(
    contract_factory,
    agent_factory,
    ethereum_tester_provider: EthereumTesterProvider,
):
    """Test that save_history_to_json works correctly with the refactored helper
    functions."""
    # Create contract objects from factory
    web3 = Web3(ethereum_tester_provider)
    contract_objects = {}
    for name, details in contract_factory.items():
        contract_objects[name] = web3.eth.contract(
            address=details["address"], abi=details["abi"]
        )

    # Generate some transactions by registering agents
    agent_00 = agent_factory["agent_00"]["agent"]
    agent_01 = agent_factory["agent_01"]["agent"]
    agent_00.register_agent()
    agent_01.register_agent()

    # Save history to JSON using the helper function
    test_file_name = "test_history_export"
    save_history_to_json(test_file_name, ethereum_tester_provider, contract_objects)

    # Verify the file was created
    output_path = Path("pyevm_export") / f"{test_file_name}.json"
    assert output_path.exists(), f"Output file should exist at {output_path}"

    # Load and verify the contents
    with open(output_path, "r") as f:
        decoded_logs = json.load(f)

    # Basic assertions
    assert isinstance(decoded_logs, list), "Decoded logs should be a list"
    assert len(decoded_logs) > 0, "Should have decoded at least some logs"

    # Verify structure of decoded logs
    first_log = decoded_logs[0]
    assert "event" in first_log, "Each log should have an 'event' field"
    assert "contract_name" in first_log, "Each log should have a 'contract_name' field"
    assert "event_name" in first_log, "Each log should have an 'event_name' field"

    # Count events
    event_counts = {}
    for log in decoded_logs:
        event_name = log.get("event_name", "Unknown")
        event_counts[event_name] = event_counts.get(event_name, 0) + 1

    # Verify we have expected events
    assert "Registered" in event_counts, "Should have Registered events"
    assert event_counts["Registered"] >= 2, "Should have at least 2 registrations"

    print("\n✓ save_history_to_json test passed")
    print(f"  Saved {len(decoded_logs)} decoded logs to {output_path}")
    print(f"  Event breakdown: {event_counts}")
