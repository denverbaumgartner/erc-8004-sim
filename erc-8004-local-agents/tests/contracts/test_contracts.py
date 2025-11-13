# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0

# system packages
import logging

# internal packages

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

######################################################################
# Tests
######################################################################


class TestContracts:

    def test_contract_factory(self, contract_factory):
        logger.debug(f"contract_factory contains: {list(contract_factory.keys())}")
        assert contract_factory is not None
        assert isinstance(contract_factory, dict)
        assert len(contract_factory) > 0
        for contract_name, contract_info in contract_factory.items():
            logger.debug(f"checking contract: {contract_name}")
            assert contract_name is not None
            assert isinstance(contract_name, str)
            assert contract_info is not None
            assert isinstance(contract_info, dict)
            assert len(contract_info) == 3
            assert "address" in contract_info
            assert "abi" in contract_info
            assert "bytecode" in contract_info
            logger.debug(f"contract address is: {contract_info['address']}")
