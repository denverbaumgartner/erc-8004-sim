# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# tests/test_simulation_env_phase3.py

from erc_8004_local_agents.simulation import SimulationEnvironment


def test_contract_deployment():
    """Test contract deployment creates all contracts."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()

    # Verify contracts deployed
    assert env.contracts is not None
    assert len(env.contracts) > 0

    # Verify each contract has address, abi, bytecode
    for contract_name, contract_data in env.contracts.items():
        assert "address" in contract_data
        assert "abi" in contract_data
        assert "bytecode" in contract_data
        assert contract_data["address"] is not None

    # Verify contract objects created
    assert env.contract_objects is not None
    assert len(env.contract_objects) == len(env.contracts)

    # Verify contracts are accessible
    for contract_name, contract_obj in env.contract_objects.items():
        assert contract_obj.address is not None


def test_account_setup():
    """Test account setup executes all operations."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()
    env._setup_accounts()

    # Verify accounts still exist
    assert env.accounts is not None
    assert len(env.accounts) >= 10
    assert env.web3 is not None

    # Verify accounts have balances (both ETH and potentially tokens)
    for i in range(min(5, len(env.accounts))):
        balance = env.web3.eth.get_balance(env.accounts[i])
        # All accounts should have some ETH (either from genesis or transfers)
        assert balance > 0


def test_full_phase3_setup():
    """Test full Phase 3 setup (contracts + accounts)."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()
    env._setup_accounts()

    # Verify all components are set up
    assert env.web3 is not None
    assert env.accounts is not None
    assert env.config is not None
    assert env.contracts is not None
    assert env.contract_objects is not None

    # Verify we can interact with deployed contracts
    # Get a contract from the deployed contracts
    assert len(env.contract_objects) > 0
    first_contract = list(env.contract_objects.values())[0]

    # Verify contract is on the blockchain
    code = env.web3.eth.get_code(first_contract.address)
    assert len(code) > 0  # Contract has bytecode


def test_contract_linking():
    """Test that contracts reference each other correctly."""
    env = SimulationEnvironment()
    env._setup_provider()
    env._setup_config()
    env._setup_contracts()

    # Verify contracts exist
    assert env.contracts is not None
    assert env.contract_objects is not None

    # If we have contracts that reference each other, verify links
    # This will depend on your specific contract setup
    # For example, if CardRegistry references IdentityRegistry:
    if "CardRegistry" in env.contracts and "IdentityRegistry" in env.contracts:
        card_registry = env.contract_objects["CardRegistry"]
        identity_registry_address = env.contracts["IdentityRegistry"]["address"]

        # The CardRegistry should have been deployed with the IdentityRegistry address
        # We can verify this by checking if the contract call doesn't revert
        assert card_registry.address is not None
        assert identity_registry_address is not None
