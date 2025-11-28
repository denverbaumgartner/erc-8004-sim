# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env python3
"""Export simulation history from JSON to CSV files."""

import argparse
import sys
from pathlib import Path

import polars as pl

from erc_8004_local_agents.data.decoder import process_event_logs


def export_sim_history_to_csv(history_file: Path, output_dir: Path) -> None:
    """
    Processes a simulation history JSON file and exports the events to CSV files.

    Args:
        history_file: Path to the simulation history JSON file.
        output_dir: Directory where the CSV files will be saved.
    """
    # --- 1. Check if the history file exists ---
    if not history_file.exists():
        print(
            f"Error: History file not found: {history_file}. "
            "Run a simulation to generate it, e.g., with `python sim/run.py`.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- 2. Process logs into dataframes ---
    print(f"\nProcessing logs from: {history_file.resolve()}")
    event_dfs = process_event_logs(history_file)
    print(f"Found {len(event_dfs)} event types: {list(event_dfs.keys())}")

    # --- 3. Save dataframes to CSV files ---
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving CSV files to: {output_dir.resolve()}")

    for event_name, df in event_dfs.items():
        assert isinstance(df, pl.DataFrame)
        output_path = output_dir / f"{event_name}.csv"
        df.write_csv(output_path)
        print(f"  - Saved {len(df):>4} '{event_name}' events to {output_path.name}")

    print("\nExport complete.")


def main():
    """Parse arguments and run the export script."""
    parser = argparse.ArgumentParser(
        description="Export ERC-8004 simulation history from JSON to CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export with default paths
  python sim/export_logs.py

  # Specify a different history file
  python sim/export_logs.py --history-file my_custom_history.json

  # Specify a different output directory
  python sim/export_logs.py --history-file my_custom_history.json --output-dir /tmp/my_csvs
        """,
    )

    parser.add_argument(
        "--history-file",
        "-f",
        default="pyevm_export/erc_8004_sim_history.json",
        help="Path to the simulation history JSON file (default: pyevm_export/erc_8004_sim_history.json)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Directory to save CSV files (default: 'csv_export' inside the history file's directory)",
    )

    args = parser.parse_args()

    history_file_path = Path(args.history_file)

    if args.output_dir:
        output_directory = Path(args.output_dir)
    else:
        output_directory = history_file_path.parent / "csv_export"

    export_sim_history_to_csv(history_file_path, output_directory)


if __name__ == "__main__":
    # poetry run python sim/export_logs.py --history-file pyevm_export/erc_8004_sim_history.json --output-dir csv_export
    main()
