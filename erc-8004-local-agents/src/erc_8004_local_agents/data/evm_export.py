# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Helper functions for exporting and decoding EVM transaction history."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from web3.providers.eth_tester import EthereumTesterProvider
from web3.types import TxReceipt

from erc_8004_local_agents.data.decoder import decode_logs_from_receipt

logger = logging.getLogger(__name__)


def export_receipts(
    ethereum_tester_provider: EthereumTesterProvider,
) -> List[TxReceipt]:
    """Export all transaction receipts from the EthereumTester instance.

    Args:
        ethereum_tester_provider: EthereumTester provider instance

    Returns:
        List of all transaction receipts from all blocks
    """
    tester = ethereum_tester_provider.ethereum_tester
    assert tester is not None
    all_receipts = []
    current_block = tester.get_block_by_number("latest")
    for block_num in range(0, current_block["number"] + 1):
        block = tester.get_block_by_number(block_num)  # type: ignore[arg-type]
        for tx_hash in block["transactions"]:
            receipt = tester.get_transaction_receipt(tx_hash)
            all_receipts.append(receipt)
    return all_receipts


def export_decoded_receipts(
    ethereum_tester_provider: EthereumTesterProvider, contract_objects: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Export and decode all transaction receipts using contract ABIs.

    Args:
        ethereum_tester_provider: EthereumTester provider instance
        contract_objects: Dictionary of contract name to web3.contract instances

    Returns:
        List of decoded event logs as dictionaries
    """
    all_decoded_receipts = []
    all_receipts = export_receipts(ethereum_tester_provider)
    for receipt in all_receipts:
        decoded_receipts = decode_logs_from_receipt(receipt, contract_objects)
        all_decoded_receipts.extend(decoded_receipts)
    return all_decoded_receipts


def save_history_to_json(
    file_name: str,
    ethereum_tester_provider: EthereumTesterProvider,
    contract_objects: Dict[str, Any],
):
    """Save decoded transaction history to a JSON file.

    Args:
        file_name: Name of the output file (without .json extension)
        ethereum_tester_provider: EthereumTester provider instance
        contract_objects: Dictionary of contract name to web3.contract instances
    """

    def _default_serializer(o):
        """Custom JSON serializer for bytes and other non-serializable types."""
        if isinstance(o, bytes):
            return "0x" + o.hex()
        raise TypeError(
            f"Object of type {o.__class__.__name__} is not JSON serializable"
        )

    output_dir = Path("pyevm_export")
    output_dir.mkdir(exist_ok=True)
    file_path = output_dir / f"{file_name}.json"
    logger.info(f"Saving history to {file_path}")
    all_decoded_receipts = export_decoded_receipts(
        ethereum_tester_provider, contract_objects
    )
    with open(file_path, "w") as f:
        json.dump(all_decoded_receipts, f, indent=2, default=_default_serializer)
