# system packages
import logging
from typing import Any, Dict

from pytest import fixture

# Re-export utilities from src for backward compatibility
from erc_8004_local_agents.simulation.account_utils import resolve_account_address

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Helper functions (re-exported from src)
######################################################################

# Functions are imported above for backward compatibility
__all__ = ["resolve_account_address", "account_setup_factory"]


######################################################################
# Fixtures
######################################################################


@fixture
def account_setup_factory(simulation_env) -> Dict[str, Any]:
    """Extract account setup results from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.

    Note: The SimulationEnvironment executes all account setup operations during
    its setup phase. This fixture extracts the real transaction hashes that were
    generated during those operations.

    Returns:
        Dictionary containing:
        - transaction_hashes: List of REAL transaction hashes for all operations
        - operations_executed: Number of operations executed
    """
    # The account setup was already executed during simulation_env.setup()
    # Extract the real transaction hashes from the simulation environment
    account_info = simulation_env.account_setup_info

    logger.debug(
        "Account setup factory: "
        f"{account_info['operations_executed']} operations were executed"
    )

    return account_info
