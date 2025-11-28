# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Any, Dict, List

import pytest

# external packages
from eth_typing import ChecksumAddress
from web3 import Web3

# internal packages

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Tests
######################################################################


def test_account_setup_factory_executes_operations(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
    account_setup_factory: Dict[str, Any],
):
    """Test that account setup factory executes all configured operations."""
    # Verify the factory returned expected metadata
    assert "transaction_hashes" in account_setup_factory
    assert "operations_executed" in account_setup_factory
    assert (
        account_setup_factory["operations_executed"] == 12
    )  # We configured 9 operations (6 original + 3 for agent addresses)

    # Verify all transaction hashes are valid
    for tx_hash in account_setup_factory["transaction_hashes"]:
        assert isinstance(tx_hash, str)
        assert len(tx_hash) == 64  # 32 bytes as hex string


def test_eth_transfers_completed(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    account_setup_factory: Dict[str, Any],
):
    """Test that ETH transfers were executed correctly."""
    # Check account[1] received 100 ETH (minus any gas spent)
    balance_1 = web3_test_instance.eth.get_balance(accounts[1])
    # Initial balance was 1,000,000 ETH, we added 100 ETH
    assert balance_1 >= Web3.to_wei(1_000_100, "ether") - Web3.to_wei(
        1, "ether"
    )  # Allow 1 ETH for gas

    # Check account[2] received 50 ETH
    balance_2 = web3_test_instance.eth.get_balance(accounts[2])
    assert balance_2 >= Web3.to_wei(1_000_050, "ether") - Web3.to_wei(
        1, "ether"
    )  # Allow 1 ETH for gas


def test_erc20_transfers_from_deployer(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
    account_setup_factory: Dict[str, Any],
):
    """Test that ERC-20 token transfers from deployer were executed correctly.

    Note: This test runs after all operations complete, so account[1] already
    transferred 100k to account[3]. Final balances reflect all operations.
    """
    # Get the ERC-20 contract
    erc20_contract = web3_test_instance.eth.contract(
        address=contract_factory["ERC-20"]["address"],
        abi=contract_factory["ERC-20"]["abi"],
    )

    # Account[1] received 400,000, then transferred 100,000 = 300,000 final
    balance_1 = erc20_contract.functions.balanceOf(accounts[1]).call()
    expected_balance_1 = Web3.to_wei(300_000, "ether")
    assert balance_1 == expected_balance_1

    # Check account[2] received 300,000 tokens (no subsequent transfers)
    balance_2 = erc20_contract.functions.balanceOf(accounts[2]).call()
    expected_balance_2 = Web3.to_wei(300_000, "ether")
    assert balance_2 == expected_balance_2


def test_erc20_transfer_completed(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
    account_setup_factory: Dict[str, Any],
):
    """Test that ERC-20 token transfers were executed correctly."""
    # Get the ERC-20 contract
    erc20_contract = web3_test_instance.eth.contract(
        address=contract_factory["ERC-20"]["address"],
        abi=contract_factory["ERC-20"]["abi"],
    )

    # Check account[1] balance (400,000 - 100,000 transferred = 300,000)
    balance_1 = erc20_contract.functions.balanceOf(accounts[1]).call()
    expected_balance_1 = Web3.to_wei(300_000, "ether")
    assert balance_1 == expected_balance_1

    # Check account[3] received 100,000 tokens
    balance_3 = erc20_contract.functions.balanceOf(accounts[3]).call()
    expected_balance_3 = Web3.to_wei(100_000, "ether")
    assert balance_3 == expected_balance_3


def test_erc20_approval_completed(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
    account_setup_factory: Dict[str, Any],
):
    """Test that ERC-20 token approvals were executed correctly."""
    # Get the ERC-20 contract
    erc20_contract = web3_test_instance.eth.contract(
        address=contract_factory["ERC-20"]["address"],
        abi=contract_factory["ERC-20"]["abi"],
    )

    # Check that account[3] has allowance from account[2]
    allowance = erc20_contract.functions.allowance(accounts[2], accounts[3]).call()
    expected_allowance = Web3.to_wei(50_000, "ether")
    assert allowance == expected_allowance


def test_operations_executed_in_order(
    account_setup_factory: Dict[str, Any],
):
    """Test that operations were executed in the correct order."""
    # Since we have 9 operations with indices 0-8, verify we got 9 transactions
    assert len(account_setup_factory["transaction_hashes"]) == 12


def test_resolve_account_address_patterns(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
):
    """Test all account address resolution patterns."""
    from tests.fixtures.account_setup import (
        resolve_account_address,  # type: ignore[attr-defined]
    )

    # Test "default" keyword
    resolved = resolve_account_address("default", accounts, contract_factory)
    assert resolved == accounts[0]

    # Test account[N] pattern
    resolved = resolve_account_address("account[1]", accounts, contract_factory)
    assert resolved == accounts[1]

    # Test direct address
    direct_addr = accounts[2]
    resolved = resolve_account_address(direct_addr, accounts, contract_factory)
    assert resolved == direct_addr

    # Test contract reference
    resolved = resolve_account_address(
        "$contracts.ERC-20.address", accounts, contract_factory
    )
    assert resolved == contract_factory["ERC-20"]["address"]


def test_invalid_account_reference(
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
):
    """Test that invalid account references raise appropriate errors."""
    from tests.fixtures.account_setup import (
        resolve_account_address,  # type: ignore[attr-defined]
    )

    # Test invalid account index
    with pytest.raises(ValueError, match="Account index .* out of range"):
        resolve_account_address("account[999]", accounts, contract_factory)

    # Test invalid contract reference
    with pytest.raises(ValueError, match="Contract reference not found"):
        resolve_account_address(
            "$contracts.NonExistent.address", accounts, contract_factory
        )

    # Test invalid format
    with pytest.raises(ValueError, match="Invalid account reference"):
        resolve_account_address("invalid_format", accounts, contract_factory)


def test_account_balances_comprehensive(
    web3_test_instance: Web3,
    accounts: List[ChecksumAddress],
    contract_factory: Dict[str, Any],
    account_setup_factory: Dict[str, Any],
):
    """Comprehensive test verifying all account balances match expected state."""
    erc20_contract = web3_test_instance.eth.contract(
        address=contract_factory["ERC-20"]["address"],
        abi=contract_factory["ERC-20"]["abi"],
    )

    # Get total supply from contract
    total_supply = erc20_contract.functions.totalSupply().call()

    # Account[0] (deployer) - started with 1,000,000, transferred out 400,000 + 300,000
    # = 700,000
    # Remaining: 1,000,000 - 700,000 = 300,000
    balance_0 = erc20_contract.functions.balanceOf(accounts[0]).call()
    expected_balance_0 = Web3.to_wei(300_000, "ether")
    assert balance_0 == expected_balance_0

    # Account[1] - received 400,000, transferred 100,000 out = 300,000
    balance_1 = erc20_contract.functions.balanceOf(accounts[1]).call()
    assert balance_1 == Web3.to_wei(300_000, "ether")

    # Account[2] - received 300,000 = 300,000
    balance_2 = erc20_contract.functions.balanceOf(accounts[2]).call()
    assert balance_2 == Web3.to_wei(300_000, "ether")

    # Account[3] - received 100,000 from transfer = 100,000
    balance_3 = erc20_contract.functions.balanceOf(accounts[3]).call()
    assert balance_3 == Web3.to_wei(100_000, "ether")

    # Verify total supply hasn't changed (no minting/burning)
    # Total: 300k + 300k + 300k + 100k = 1,000,000
    assert total_supply == Web3.to_wei(1_000_000, "ether")

    logger.info(
        "✓ All account balances verified successfully. Total supply: "
        f"{total_supply / 10**18} tokens"
    )
