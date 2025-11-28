# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging
from typing import Any, Dict, List

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


class TestERC8004Registries:
    """Comprehensive test suite for ERC-8004 registry contract deployments.

    Tests verify:
    - Correct deployment of all three registries
    - Proper constructor argument passing
    - Registry linking via constructor parameters
    - Basic functionality of each registry
    """

    def test_identity_registry_deployment(self, contract_factory: Dict[str, Any]):
        """Verify IdentityRegistry is deployed."""
        assert "IdentityRegistry" in contract_factory
        assert contract_factory["IdentityRegistry"]["address"] is not None
        assert isinstance(contract_factory["IdentityRegistry"]["address"], str)
        assert contract_factory["IdentityRegistry"]["address"].startswith("0x")
        assert len(contract_factory["IdentityRegistry"]["address"]) == 42

    def test_reputation_registry_deployment(
        self, contract_factory: Dict[str, Any], web3_test_instance: Web3
    ):
        """Verify ReputationRegistry is deployed with correct IdentityRegistry."""
        assert "ReputationRegistry" in contract_factory

        reputation = web3_test_instance.eth.contract(
            address=contract_factory["ReputationRegistry"]["address"],
            abi=contract_factory["ReputationRegistry"]["abi"],
        )

        linked_identity = reputation.functions.getIdentityRegistry().call()
        assert linked_identity == contract_factory["IdentityRegistry"]["address"]

    def test_validation_registry_deployment(
        self, contract_factory: Dict[str, Any], web3_test_instance: Web3
    ):
        """Verify ValidationRegistry is deployed with correct IdentityRegistry."""
        assert "ValidationRegistry" in contract_factory

        validation = web3_test_instance.eth.contract(
            address=contract_factory["ValidationRegistry"]["address"],
            abi=contract_factory["ValidationRegistry"]["abi"],
        )

        linked_identity = validation.functions.getIdentityRegistry().call()
        assert linked_identity == contract_factory["IdentityRegistry"]["address"]

    def test_all_registries_linked(
        self, contract_factory: Dict[str, Any], web3_test_instance: Web3
    ):
        """Verify both ReputationRegistry and ValidationRegistry reference the same
        IdentityRegistry."""
        reputation = web3_test_instance.eth.contract(
            address=contract_factory["ReputationRegistry"]["address"],
            abi=contract_factory["ReputationRegistry"]["abi"],
        )
        validation = web3_test_instance.eth.contract(
            address=contract_factory["ValidationRegistry"]["address"],
            abi=contract_factory["ValidationRegistry"]["abi"],
        )

        rep_identity = reputation.functions.getIdentityRegistry().call()
        val_identity = validation.functions.getIdentityRegistry().call()

        assert rep_identity == val_identity
        assert rep_identity == contract_factory["IdentityRegistry"]["address"]

    def test_identity_registry_functionality(
        self,
        contract_factory: Dict[str, Any],
        web3_test_instance: Web3,
        accounts: List[ChecksumAddress],
    ):
        """Test basic IdentityRegistry functionality."""
        identity = web3_test_instance.eth.contract(
            address=contract_factory["IdentityRegistry"]["address"],
            abi=contract_factory["IdentityRegistry"]["abi"],
        )

        # Verify contract has the expected ERC-721 functions
        assert hasattr(identity.functions, "register")
        assert hasattr(identity.functions, "ownerOf")
        assert hasattr(identity.functions, "tokenURI")
        assert hasattr(identity.functions, "balanceOf")

        # Verify initial balance is 0
        initial_balance = identity.functions.balanceOf(accounts[0]).call()
        assert initial_balance == 0

    def test_reputation_registry_functionality(
        self,
        contract_factory: Dict[str, Any],
        web3_test_instance: Web3,
        accounts: List[ChecksumAddress],
    ):
        """Test basic ReputationRegistry has expected functions."""
        reputation = web3_test_instance.eth.contract(
            address=contract_factory["ReputationRegistry"]["address"],
            abi=contract_factory["ReputationRegistry"]["abi"],
        )

        # Verify contract has the expected functions from the ABI
        assert hasattr(reputation.functions, "getIdentityRegistry")
        assert hasattr(reputation.functions, "getSummary")
        assert hasattr(reputation.functions, "giveFeedback")
        assert hasattr(reputation.functions, "readFeedback")

        # Verify the identity registry reference is correct
        linked_identity = reputation.functions.getIdentityRegistry().call()
        assert linked_identity == contract_factory["IdentityRegistry"]["address"]

    def test_validation_registry_functionality(
        self,
        contract_factory: Dict[str, Any],
        web3_test_instance: Web3,
        accounts: List[ChecksumAddress],
    ):
        """Test basic ValidationRegistry has expected functions."""
        validation = web3_test_instance.eth.contract(
            address=contract_factory["ValidationRegistry"]["address"],
            abi=contract_factory["ValidationRegistry"]["abi"],
        )

        # Verify contract has the expected functions from the ABI
        assert hasattr(validation.functions, "getIdentityRegistry")
        assert hasattr(validation.functions, "getSummary")
        assert hasattr(validation.functions, "validationRequest")
        assert hasattr(validation.functions, "validationResponse")

        # Verify the identity registry reference is correct
        linked_identity = validation.functions.getIdentityRegistry().call()
        assert linked_identity == contract_factory["IdentityRegistry"]["address"]
