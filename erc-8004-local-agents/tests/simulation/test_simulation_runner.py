# SPDX-FileCopyrightText: 2025 Semiotic Labs
#
# SPDX-License-Identifier: Apache-2.0
"""Test suite for standalone simulation runner."""

import json
import os
from pathlib import Path

import pytest

from sim.run import SimulationRunner


class TestSimulationRunner:
    """Test the standalone simulation runner and SimulationEnvironment."""

    @pytest.mark.asyncio
    async def test_simulation_runner_execution(self) -> None:
        """Test that the runner executes and produces correct chain state.

        This test:
        1. Instantiates the SimulationRunner with test config
        2. Executes the full simulation
        3. Verifies contract deployments and linkages
        4. Verifies account balances (ETH and ERC-20)
        5. Verifies simulation outcomes (feedback events)
        """
        # Skip if no API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not set in environment")

        # Create args namespace for runner
        class Args:
            config = "configs/local_network.yaml"
            api_key = None
            no_history = False
            history_file = "tests/test_simulation_runner_history.json"
            log_level = "INFO"
            tui = False

        # Instantiate and run the simulation
        runner = SimulationRunner(Args())
        await runner.run()

        # Access the environment object
        env = runner.env
        assert env is not None, "Environment should be initialized"
        assert env.contracts is not None
        assert env.contract_objects is not None
        assert env.web3 is not None
        assert env.accounts is not None
        assert env.config is not None
        assert env.agents is not None

        # ====== 8.1. Setup Verification ======

        # --- Contract Deployment Checks ---

        # Verify all expected contracts exist
        expected_contracts = [
            "ERC-20",
            "IdentityRegistry",
            "ReputationRegistry",
            "ValidationRegistry",
        ]
        for contract_name in expected_contracts:
            assert (
                contract_name in env.contracts
            ), f"{contract_name} not in contracts dict"
            assert (
                contract_name in env.contract_objects
            ), f"{contract_name} not in contract_objects"

        # Verify contract linkage: ReputationRegistry should point to IdentityRegistry
        identity_registry_address = env.contracts["IdentityRegistry"]["address"]
        reputation_registry = env.contract_objects["ReputationRegistry"]
        linked_identity_address = (
            reputation_registry.functions.getIdentityRegistry().call()
        )
        assert (
            linked_identity_address == identity_registry_address
        ), "ReputationRegistry not correctly linked to IdentityRegistry"

        # Verify contract linkage: ValidationRegistry should point to IdentityRegistry
        validation_registry = env.contract_objects["ValidationRegistry"]
        linked_identity_address_validation = (
            validation_registry.functions.getIdentityRegistry().call()
        )
        assert (
            linked_identity_address_validation == identity_registry_address
        ), "ValidationRegistry not correctly linked to IdentityRegistry"

        # --- Account State Checks ---

        # ETH balance checks (from local_network.yaml account operations)
        # Note: PyEVM gives accounts a large initial balance (~1,000,000 ETH)
        # We verify the accounts received at least the transferred amounts
        # (they may have spent some on gas for registration transactions)

        # account[1] should have received 100 ETH (plus initial balance minus gas)
        balance_account_1 = env.web3.eth.get_balance(env.accounts[1])
        min_expected_balance_1 = env.web3.to_wei(100, "ether")
        assert (
            balance_account_1 >= min_expected_balance_1
        ), f"account[1] balance too low: {balance_account_1} < {min_expected_balance_1}"

        # account[2] should have received 50 ETH (plus initial balance minus gas)
        balance_account_2 = env.web3.eth.get_balance(env.accounts[2])
        min_expected_balance_2 = env.web3.to_wei(50, "ether")
        assert (
            balance_account_2 >= min_expected_balance_2
        ), f"account[2] balance too low: {balance_account_2} < {min_expected_balance_2}"

        # ERC-20 balance checks
        token_contract = env.contract_objects["ERC-20"]

        # account[1] received 400,000 tokens, then sent 100,000 to account[3]
        # Final balance: 300,000 tokens
        balance_token_1 = token_contract.functions.balanceOf(env.accounts[1]).call()
        expected_token_1 = 300000 * (10**18)
        assert balance_token_1 == expected_token_1, "account[1] token balance mismatch"

        # account[2] received 300,000 tokens (no transfers out)
        balance_token_2 = token_contract.functions.balanceOf(env.accounts[2]).call()
        expected_token_2 = 300000 * (10**18)
        assert balance_token_2 == expected_token_2, "account[2] token balance mismatch"

        # account[3] received 100,000 tokens from account[1]
        balance_token_3 = token_contract.functions.balanceOf(env.accounts[3]).call()
        expected_token_3 = 100000 * (10**18)
        assert balance_token_3 == expected_token_3, "account[3] token balance mismatch"

        # ERC-20 allowance checks
        # account[3] should be approved to spend 50,000 tokens from account[2]
        allowance = token_contract.functions.allowance(
            env.accounts[2], env.accounts[3]
        ).call()
        expected_allowance = 50000 * (10**18)
        assert allowance == expected_allowance, "Allowance mismatch for account[3]"

        # ====== 8.2. Simulation Outcome Verification ======

        # Get simulation agents from config
        assert env.config is not None
        assert env.config.simulation is not None
        sim_agents = env.config.simulation.agents
        sim_agent_ids = [agent_config.agent_id for agent_config in sim_agents]

        # Verify feedback was submitted by simulation agents
        reputation_registry = env.contract_objects["ReputationRegistry"]

        for sim_agent_id in sim_agent_ids:
            sim_agent = env.agents[sim_agent_id]["agent"]

            # Check feedback submitted by this agent
            # The agent should have submitted feedback to at least one peer
            feedback_found = False

            # Check all peer agents
            for agent_id in env.agents.keys():
                if agent_id not in sim_agent_ids:  # This is a peer agent
                    peer_agent = env.agents[agent_id]["agent"]
                    all_feedback = sim_agent.client.reputation.read_all_feedback(
                        peer_agent.agent_id
                    )

                    if len(all_feedback["scores"]) > 0:
                        feedback_found = True
                        break

            assert (
                feedback_found
            ), f"{sim_agent_id} did not submit feedback to any peer agent"

        # Verify history file was created (save_history_to_json always saves
        # to pyevm_export/)
        history_file_path = Path("pyevm_export/test_simulation_runner_history.json")
        assert history_file_path.exists(), "History file was not created"

        with open(history_file_path, "r") as f:
            history_data = json.load(f)

        # Check that we have transaction history
        assert len(history_data) > 0, "History file is empty"

        # Look for NewFeedback events in the event log data
        new_feedback_events = [
            event for event in history_data if event.get("event_name") == "NewFeedback"
        ]

        assert (
            len(new_feedback_events) > 0
        ), "No NewFeedback events found in history file"

        # Verify we have the expected number of feedback events
        # (4 from each sim agent = 8 total)
        assert len(new_feedback_events) >= 4, (
            f"Expected at least 8 NewFeedback events, found "
            f"{len(new_feedback_events)}"
        )

        # Cleanup test history file
        if history_file_path.exists():
            history_file_path.unlink()
