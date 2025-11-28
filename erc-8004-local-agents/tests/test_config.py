# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging

# internal packages
from tests.fixtures.types import LocalNetworkConfig

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Tests
######################################################################


class TestConfig:

    def test_local_network_config(self, local_network_config):
        assert local_network_config is not None
        assert isinstance(local_network_config, LocalNetworkConfig)
        assert len(local_network_config.contracts) > 0
