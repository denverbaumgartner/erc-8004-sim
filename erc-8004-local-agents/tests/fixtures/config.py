# system packages
import logging

from pytest import fixture

# internal packages
from tests.fixtures.types import LocalNetworkConfig

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Objects
######################################################################

######################################################################
# Fixtures
######################################################################


@fixture
def local_network_config(simulation_env) -> LocalNetworkConfig:
    """Extract network config from simulation environment.

    This fixture maintains backward compatibility while using SimulationEnvironment
    internally. Tests using this fixture remain unchanged.
    """
    return simulation_env.config
