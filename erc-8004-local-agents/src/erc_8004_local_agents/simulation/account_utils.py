# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

"""Account operation utilities for simulation environment."""

# system packages
import logging
import re
from typing import Any, Dict, List

# external packages
from eth_typing import ChecksumAddress
from web3 import Web3

# internal packages
from erc_8004_local_agents.simulation.types import (
    AccountActionEnum,
    AccountOperationConfig,
)

logger = logging.getLogger(__name__)


######################################################################
# Helper functions
######################################################################


def resolve_account_address(
    account_ref: str,
    accounts: List[ChecksumAddress],
    deployed_contracts: Dict[str, Any],
) -> ChecksumAddress:
    """Resolve account references to actual addresses.

    Args:
        account_ref: Account reference string (e.g., "default", "account[1]", "0x...")
        accounts: List of available test accounts
        deployed_contracts: Dictionary of deployed contracts

    Returns:
        Resolved ChecksumAddress

    Examples:
        "default" -> accounts[0]
        "account[0]" -> accounts[0]
        "account[5]" -> accounts[5]
        "0x1234..." -> "0x1234..."
        "$contracts.ERC-20.address" -> deployed contract address
    """
    # Handle "default" keyword
    if account_ref == "default":
        return accounts[0]

    # Handle account[N] pattern
    match = re.match(r"account\[(\d+)\]", account_ref)
    if match:
        index = int(match.group(1))
        if index >= len(accounts):
            raise ValueError(
                f"Account index {index} out of range (max: {len(accounts) - 1})"
            )
        return accounts[index]

    # Handle contract references
    if account_ref.startswith("$contracts."):
        parts = account_ref.split(".")
        if len(parts) == 3 and parts[2] == "address":
            contract_type = parts[1]
            if contract_type not in deployed_contracts:
                raise ValueError(f"Contract reference not found: {contract_type}")
            return deployed_contracts[contract_type]["address"]
        else:
            raise ValueError(f"Invalid contract reference format: {account_ref}")

    # Handle direct address (with checksum conversion)
    if account_ref.startswith("0x"):
        return Web3.to_checksum_address(account_ref)

    raise ValueError(f"Invalid account reference: {account_ref}")


def execute_transfer_eth(
    web3: Web3,
    from_account: ChecksumAddress,
    to_account: ChecksumAddress,
    amount: int | float,
) -> str:
    """Transfer ETH between accounts.

    Args:
        web3: Web3 instance
        from_account: Source account address
        to_account: Destination account address
        amount: Amount in ETH (will be converted to wei)

    Returns:
        Transaction hash
    """
    amount_wei = Web3.to_wei(amount, "ether")

    tx_hash = web3.eth.send_transaction(
        {
            "from": from_account,
            "to": to_account,
            "value": amount_wei,
        }
    )

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    logger.info(f"✓ Transferred {amount} ETH from {from_account} to {to_account}")

    return tx_receipt["transactionHash"].hex()


def execute_transfer_erc20(
    web3: Web3,
    contract_address: ChecksumAddress,
    contract_abi: Any,
    from_account: ChecksumAddress,
    to_account: ChecksumAddress,
    amount: int | float,
    decimals: int,
) -> str:
    """Transfer ERC-20 tokens between accounts.

    Args:
        web3: Web3 instance
        contract_address: ERC-20 contract address
        contract_abi: Contract ABI
        from_account: Source account
        to_account: Destination account
        amount: Amount of tokens (will be converted using decimals)
        decimals: Token decimals

    Returns:
        Transaction hash
    """
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    amount_smallest_unit = int(amount * (10**decimals))

    tx_hash = contract.functions.transfer(to_account, amount_smallest_unit).transact(
        {"from": from_account}
    )

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    logger.info(f"✓ Transferred {amount} tokens from {from_account} to {to_account}")

    return tx_receipt["transactionHash"].hex()


def execute_approve_erc20(
    web3: Web3,
    contract_address: ChecksumAddress,
    contract_abi: Any,
    owner: ChecksumAddress,
    spender: ChecksumAddress,
    amount: int | float,
    decimals: int,
) -> str:
    """Approve ERC-20 token spending allowance.

    Args:
        web3: Web3 instance
        contract_address: ERC-20 contract address
        contract_abi: Contract ABI
        owner: Account granting allowance
        spender: Account receiving allowance
        amount: Allowance amount (will be converted using decimals)
        decimals: Token decimals

    Returns:
        Transaction hash
    """
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    amount_smallest_unit = int(amount * (10**decimals))

    tx_hash = contract.functions.approve(spender, amount_smallest_unit).transact(
        {"from": owner}
    )

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    logger.info(f"✓ Approved {amount} tokens for {spender} from {owner}")

    return tx_receipt["transactionHash"].hex()


def execute_account_operation(
    web3: Web3,
    operation: AccountOperationConfig,
    accounts: List[ChecksumAddress],
    deployed_contracts: Dict[str, Any],
) -> str:
    """Execute a single account operation based on configuration.

    Args:
        web3: Web3 instance
        operation: Account operation configuration
        accounts: List of test accounts
        deployed_contracts: Dictionary of deployed contracts

    Returns:
        Transaction hash

    Raises:
        ValueError: If operation configuration is invalid
    """
    # Resolve contract address and ABI if needed
    contract_address = None
    contract_abi = None
    if operation.contract:
        parts = operation.contract.split(".")
        if len(parts) == 3 and parts[0] == "$contracts" and parts[2] == "address":
            contract_type = parts[1]
            if contract_type not in deployed_contracts:
                raise ValueError(f"Contract not found: {contract_type}")
            contract_address = deployed_contracts[contract_type]["address"]
            contract_abi = deployed_contracts[contract_type]["abi"]
        else:
            raise ValueError(f"Invalid contract reference: {operation.contract}")

    # Execute based on action type
    if operation.action == AccountActionEnum.TRANSFER_ETH:
        if not operation.from_account or not operation.to_account:
            raise ValueError("transfer_eth requires from_account and to_account")

        from_addr = resolve_account_address(
            operation.from_account, accounts, deployed_contracts
        )
        to_addr = resolve_account_address(
            operation.to_account, accounts, deployed_contracts
        )

        return execute_transfer_eth(web3, from_addr, to_addr, operation.amount)

    elif operation.action == AccountActionEnum.TRANSFER_ERC20:
        if (
            not operation.from_account
            or not operation.to_account
            or not contract_address
        ):
            raise ValueError(
                "transfer_erc20 requires from_account, to_account, and contract"
            )

        from_addr = resolve_account_address(
            operation.from_account, accounts, deployed_contracts
        )
        to_addr = resolve_account_address(
            operation.to_account, accounts, deployed_contracts
        )

        return execute_transfer_erc20(
            web3,
            contract_address,
            contract_abi,
            from_addr,
            to_addr,
            operation.amount,
            operation.decimals,
        )

    elif operation.action == AccountActionEnum.APPROVE_ERC20:
        if not operation.owner or not operation.spender or not contract_address:
            raise ValueError("approve_erc20 requires owner, spender, and contract")

        owner_addr = resolve_account_address(
            operation.owner, accounts, deployed_contracts
        )
        spender_addr = resolve_account_address(
            operation.spender, accounts, deployed_contracts
        )

        return execute_approve_erc20(
            web3,
            contract_address,
            contract_abi,
            owner_addr,
            spender_addr,
            operation.amount,
            operation.decimals,
        )

    else:
        raise ValueError(f"Unknown action type: {operation.action}")
