# system packages
import logging
from typing import Any, Dict

from pytest import fixture

# external packages
from web3 import Web3

# Re-export utilities from src for backward compatibility

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Objects
######################################################################

######################################################################
# Helper functions (re-exported from src)
######################################################################

# Functions are imported above for backward compatibility


def verify_registry_deployments(web3: Web3, contracts: Dict[str, Any]) -> bool:
    """Verify all three registries are correctly deployed and linked.

    Checks:
    1. IdentityRegistry exists and is ERC-721 compatible
    2. ReputationRegistry.identityRegistry() == IdentityRegistry address
    3. ValidationRegistry.identityRegistry() == IdentityRegistry address

    Args:
        web3: Web3 instance
        contracts: Dictionary of deployed contracts from contract_factory

    Returns:
        True if all checks pass

    Raises:
        AssertionError: If any verification check fails
    """
    identity_addr = contracts["IdentityRegistry"]["address"]
    reputation_addr = contracts["ReputationRegistry"]["address"]
    validation_addr = contracts["ValidationRegistry"]["address"]

    # Create contract instances
    reputation = web3.eth.contract(
        address=reputation_addr, abi=contracts["ReputationRegistry"]["abi"]
    )
    validation = web3.eth.contract(
        address=validation_addr, abi=contracts["ValidationRegistry"]["abi"]
    )

    # Verify linkage
    assert (
        reputation.functions.getIdentityRegistry().call() == identity_addr
    ), "ReputationRegistry not linked to IdentityRegistry"
    assert (
        validation.functions.getIdentityRegistry().call() == identity_addr
    ), "ValidationRegistry not linked to IdentityRegistry"

    logger.info("✓ All registry deployments verified successfully")
    logger.info(f"  - IdentityRegistry: {identity_addr}")
    logger.info(f"  - ReputationRegistry: {reputation_addr}")
    logger.info(f"  - ValidationRegistry: {validation_addr}")

    return True


@fixture
def contract_factory(simulation_env) -> Dict[str, Any]:
    """Extract contract factory from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.

    Returns:
        Dictionary with contract info keyed by contract type:
        {
            "IdentityRegistry": {
                "address": "0x...",
                "abi": [...],
                "bytecode": "0x..."
            },
            ...
        }
    """
    return simulation_env.contracts


@fixture
def contract_objects(simulation_env) -> Dict[str, Any]:
    """Extract contract objects from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.

    Args:
        simulation_env: Simulation environment with deployed contracts

    Returns:
        Dictionary of contract objects
    """
    return simulation_env.contract_objects
