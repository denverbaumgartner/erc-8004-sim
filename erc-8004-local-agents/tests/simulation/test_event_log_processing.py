"""Test event log processing with Polars."""

from pathlib import Path

import polars as pl
import pytest

from erc_8004_local_agents.data.decoder import process_event_logs


def test_process_event_logs():
    """Test that we can process event logs into separate DataFrames."""
    # Use the simulation history file
    file_path = Path("pyevm_export/erc_8004_sim_history.json")

    if not file_path.exists():
        pytest.skip("Simulation history file not found")

    # Process the event logs
    event_dfs = process_event_logs(file_path)

    # Basic assertions
    assert isinstance(event_dfs, dict), "Should return a dictionary"
    assert len(event_dfs) > 0, "Should have at least one event type"

    # Check that all values are DataFrames
    for event_name, df in event_dfs.items():
        assert isinstance(df, pl.DataFrame), f"{event_name} should be a DataFrame"
        assert len(df) > 0, f"{event_name} DataFrame should not be empty"

        # Check common columns exist
        assert "event_name" in df.columns
        assert "blockNumber" in df.columns
        assert "transactionHash" in df.columns

    # Check specific event types we expect from the simulation
    assert "NewFeedback" in event_dfs, "Should have NewFeedback events"
    assert "Registered" in event_dfs, "Should have Registered events"

    # Verify NewFeedback DataFrame structure
    feedback_df = event_dfs["NewFeedback"]
    assert "agentId" in feedback_df.columns, "Should have unpacked agentId from args"
    assert "score" in feedback_df.columns, "Should have unpacked score from args"
    assert (
        "clientAddress" in feedback_df.columns
    ), "Should have unpacked clientAddress from args"

    # Verify Registered DataFrame structure
    registered_df = event_dfs["Registered"]
    assert "agentId" in registered_df.columns, "Should have unpacked agentId from args"
    assert "owner" in registered_df.columns, "Should have unpacked owner from args"
    assert (
        "tokenURI" in registered_df.columns
    ), "Should have unpacked tokenURI from args"

    print(f"✓ Successfully processed {len(event_dfs)} event types")
    for event_name, df in event_dfs.items():
        print(f"  - {event_name}: {len(df)} events")


def test_feedback_analysis():
    """Test that we can perform analysis on feedback data."""
    file_path = Path("pyevm_export/erc_8004_sim_history.json")

    if not file_path.exists():
        pytest.skip("Simulation history file not found")

    event_dfs = process_event_logs(file_path)

    feedback_df = event_dfs.get("NewFeedback")
    assert feedback_df is not None, "Should have NewFeedback events"

    # Example analysis: average score
    avg_score = feedback_df["score"].mean()
    assert avg_score is not None, "Should be able to calculate average score"
    assert isinstance(avg_score, float), "Average should be a float"

    # Group by agent
    agent_feedback = feedback_df.group_by("agentId").agg(
        [pl.len().alias("feedback_count"), pl.col("score").mean().alias("avg_score")]
    )

    assert len(agent_feedback) > 0, "Should have feedback grouped by agent"
    print(f"✓ Analyzed feedback for {len(agent_feedback)} agent(s)")
    print(f"  Overall average score: {avg_score:.2f}")
