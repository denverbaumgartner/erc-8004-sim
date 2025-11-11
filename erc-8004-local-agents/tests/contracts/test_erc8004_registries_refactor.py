# system packages
import logging

# internal packages
from erc_8004_local_agents.simulation import SimulationEnvironment

# external packages


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

    def test_identity_registry_deployment(self, simulation_env: SimulationEnvironment):
        """Verify IdentityRegistry is deployed."""
        contracts = simulation_env.contracts
        assert contracts is not None
        assert "IdentityRegistry" in contracts
        assert contracts["IdentityRegistry"]["address"] is not None
        assert isinstance(contracts["IdentityRegistry"]["address"], str)
        assert contracts["IdentityRegistry"]["address"].startswith("0x")
        assert len(contracts["IdentityRegistry"]["address"]) == 42

    def test_reputation_registry_deployment(
        self, simulation_env: SimulationEnvironment
    ):
        """Verify ReputationRegistry is deployed with correct IdentityRegistry."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        assert contracts is not None
        assert web3 is not None
        assert "ReputationRegistry" in contracts

        reputation = web3.eth.contract(
            address=contracts["ReputationRegistry"]["address"],
            abi=contracts["ReputationRegistry"]["abi"],
        )

        linked_identity = reputation.functions.getIdentityRegistry().call()
        assert linked_identity == contracts["IdentityRegistry"]["address"]

    def test_validation_registry_deployment(
        self, simulation_env: SimulationEnvironment
    ):
        """Verify ValidationRegistry is deployed with correct IdentityRegistry."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        assert contracts is not None
        assert web3 is not None
        assert "ValidationRegistry" in contracts

        validation = web3.eth.contract(
            address=contracts["ValidationRegistry"]["address"],
            abi=contracts["ValidationRegistry"]["abi"],
        )

        linked_identity = validation.functions.getIdentityRegistry().call()
        assert linked_identity == contracts["IdentityRegistry"]["address"]

    def test_all_registries_linked(self, simulation_env: SimulationEnvironment):
        """Verify both ReputationRegistry and ValidationRegistry reference the same
        IdentityRegistry."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        assert contracts is not None
        assert web3 is not None
        reputation = web3.eth.contract(
            address=contracts["ReputationRegistry"]["address"],
            abi=contracts["ReputationRegistry"]["abi"],
        )
        validation = web3.eth.contract(
            address=contracts["ValidationRegistry"]["address"],
            abi=contracts["ValidationRegistry"]["abi"],
        )

        rep_identity = reputation.functions.getIdentityRegistry().call()
        val_identity = validation.functions.getIdentityRegistry().call()

        assert rep_identity == val_identity
        assert rep_identity == contracts["IdentityRegistry"]["address"]

    def test_identity_registry_functionality(
        self, simulation_env: SimulationEnvironment
    ):
        """Test basic IdentityRegistry functionality."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        accounts = simulation_env.accounts
        assert contracts is not None
        assert web3 is not None
        assert accounts is not None
        identity = web3.eth.contract(
            address=contracts["IdentityRegistry"]["address"],
            abi=contracts["IdentityRegistry"]["abi"],
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
        self, simulation_env: SimulationEnvironment
    ):
        """Test basic ReputationRegistry has expected functions."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        assert contracts is not None
        assert web3 is not None
        reputation = web3.eth.contract(
            address=contracts["ReputationRegistry"]["address"],
            abi=contracts["ReputationRegistry"]["abi"],
        )

        # Verify contract has the expected functions from the ABI
        assert hasattr(reputation.functions, "getIdentityRegistry")
        assert hasattr(reputation.functions, "getSummary")
        assert hasattr(reputation.functions, "giveFeedback")
        assert hasattr(reputation.functions, "readFeedback")

        # Verify the identity registry reference is correct
        linked_identity = reputation.functions.getIdentityRegistry().call()
        assert linked_identity == contracts["IdentityRegistry"]["address"]

    def test_validation_registry_functionality(
        self, simulation_env: SimulationEnvironment
    ):
        """Test basic ValidationRegistry has expected functions."""
        contracts = simulation_env.contracts
        web3 = simulation_env.web3
        assert contracts is not None
        assert web3 is not None
        validation = web3.eth.contract(
            address=contracts["ValidationRegistry"]["address"],
            abi=contracts["ValidationRegistry"]["abi"],
        )

        # Verify contract has the expected functions from the ABI
        assert hasattr(validation.functions, "getIdentityRegistry")
        assert hasattr(validation.functions, "getSummary")
        assert hasattr(validation.functions, "validationRequest")
        assert hasattr(validation.functions, "validationResponse")

        # Verify the identity registry reference is correct
        linked_identity = validation.functions.getIdentityRegistry().call()
        assert linked_identity == contracts["IdentityRegistry"]["address"]
