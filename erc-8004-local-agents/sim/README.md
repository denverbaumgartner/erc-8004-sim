# ERC-8004 Local Agent Simulation Runner

This directory contains a standalone script for running ERC-8004 agent simulations. It allows you to execute complex interaction scenarios defined in YAML configuration files without needing the `pytest` test framework.

## 1. Setup

### Dependencies

Ensure all project dependencies are installed using Poetry:

```bash
poetry install
```

### Environment Variables

The simulation requires an API key for the language model provider. Set it as an environment variable:

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Alternatively, you can pass the key directly using the `--api-key` command-line argument.

## 2. Usage

The main script is `run.py`. You can execute it from the root of the `erc-8004-local-agents` directory.

### Basic Command

To run the simulation with the default configuration (`tests/configs/local_network.yaml`):

```bash
python sim/run.py
```

### Command-Line Options

You can customize the simulation run with the following options:

| Argument | Description | Default |
|---|---|---|
| `--network-config <path>` | Path to the main `local_network.yaml` configuration file. | `tests/configs/local_network.yaml` |
| `--agent-configs <dir>` | Path to the directory containing agent YAML files. | `tests/configs/agents` |
| `--api-key <key>` | Your OpenRouter API key. Overrides the environment variable. | `None` |
| `--no-history` | Disable saving of the transaction history to a JSON file. | `False` |
| `--log-level <level>` | Set the console logging level. Choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`. | `INFO` |

### Examples

**Run with a custom network configuration:**
```bash
python sim/run.py --network-config path/to/your/custom_scenario.yaml
```

**Run with `DEBUG` logging to see detailed output:**
```bash
python sim/run.py --log-level DEBUG
```

**Run without saving the transaction history:**
```bash
python sim/run.py --no-history
```

## 3. Configuration

The simulation's behavior is primarily controlled by the `local_network.yaml` file provided via the `--network-config` argument. This file defines:
- Which smart contracts to deploy.
- Initial account setup (e.g., ETH and token transfers).
- The agents participating in the simulation.
- The simulation scenario itself, including which agents to run, what prompts to use, and how many times to loop.

See `tests/configs/local_network.yaml` for a detailed example.
