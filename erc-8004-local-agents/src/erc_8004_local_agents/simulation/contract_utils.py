# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Contract deployment and management utilities for simulation environment."""

# system packages
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# external packages
from eth_typing import ChecksumAddress
from web3 import Web3

# internal packages
from erc_8004_local_agents.simulation.types import ContractTypeEnum

logger = logging.getLogger(__name__)


######################################################################
# Helper functions
######################################################################


def resolve_contract_reference(value: Any, deployed_contracts: Dict[str, Any]) -> Any:
    """Resolve contract address references in configuration.

    Args:
        value: Raw value that may contain $contracts.* references
        deployed_contracts: Dictionary of deployed contracts

    Returns:
        Resolved value (address if reference, original value otherwise)

    Examples:
        "$contracts.IDENTITY_REGISTRY.address" -> "0x1234..."
        "$contracts.IdentityRegistry.address" -> "0x1234..."
        "0x5678..." -> "0x5678..."
        1000 -> 1000
    """
    if isinstance(value, str) and value.startswith("$contracts."):
        # Parse reference: $contracts.CONTRACT_TYPE.address
        parts = value.split(".")
        if len(parts) == 3 and parts[2] == "address":
            contract_type = parts[1]
            if contract_type not in deployed_contracts:
                raise ValueError(f"Contract reference not found: {contract_type}")
            return deployed_contracts[contract_type]["address"]
        else:
            raise ValueError(f"Invalid contract reference format: {value}")
    return value


def get_abi_path(contract_name: ContractTypeEnum) -> Path:
    """Get the path to a contract's ABI file.

    Args:
        contract_name: Contract type enum

    Returns:
        Path to the ABI JSON file
    """
    # Navigate from src/erc_8004_local_agents/simulation/ to src/assets/abis/
    # __file__ is at: src/erc_8004_local_agents/simulation/contract_utils.py
    # We need to go up to src/ then to assets/abis/
    abi_directory = Path(__file__).parent.parent.parent / "assets" / "abis"
    return abi_directory / f"{contract_name.value}.json"


def load_abi(abi_path: Path) -> Tuple[Any, Any]:
    """Load ABI and bytecode from JSON file.

    Args:
        abi_path: Path to the ABI JSON file

    Returns:
        Tuple of (abi, bytecode)

    Raises:
        ValueError: If ABI or bytecode not found in file
    """
    with open(abi_path, "r") as f:
        json_object = json.load(f)

    if isinstance(json_object, dict):
        abi = json_object.get("abi")
        bytecode = json_object.get("bytecode")
    else:
        abi = json_object
        bytecode = None

    if not abi:
        raise ValueError("ABI not found in the ABI file")

    if not bytecode:
        raise ValueError("Bytecode not found in the ABI file")

    return abi, bytecode


def deploy_contract(
    web3: Web3, abi_path: Path, deployer_address: ChecksumAddress, *args
) -> Tuple[Optional[ChecksumAddress], Any, Any]:
    """Deploy a smart contract.

    Args:
        web3: Web3 instance
        abi_path: Path to contract ABI file
        deployer_address: Address to deploy from
        *args: Constructor arguments

    Returns:
        Tuple of (contract_address, abi, bytecode)
    """
    # Load the abi
    abi, bytecode = load_abi(abi_path)

    # Create the contract
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    # Deploy the contract
    tx_hash = contract.constructor(*args).transact({"from": deployer_address})

    # Wait for the transaction to be mined
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_receipt["contractAddress"], abi, bytecode
