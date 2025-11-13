# ERC-8004 Simulation

This repository contains code for running agent simulations on the ERC-8004 framework.

## Prerequisites

Before running the simulation, ensure you have:
- **Python 3.13.x** installed
- **Poetry** installed ([installation guide](https://python-poetry.org/docs/#installation))
- **Git** (for submodule initialization)
- **An OpenRouter API key** for the DSPy agents

## Project Structure

```
erc-8004-sim/
├── erc-8004-contracts/         # ERC-8004 contracts
├── erc-8004-local-agents/      # ERC-8004 agents and simulation environment
└── erc-8004-py                 # ERC-8004 python sdk
```

## Quick Start

For the fastest setup, run these commands in sequence:

```bash
# 0. Ensure the script is executable
chmod +x run.sh

# 1. Install dependencies and submodules
./run.sh install

# 2. Setup environment (will prompt for API key)
./run.sh setup-env

# 3. Run the simulation TUI
./run.sh run-tui
```

Alternatively, you can manually create a `.env` file in the project root:
```bash
cp .env.example .env
# Edit .env and add: OPENROUTER_API_KEY=your_api_key_here
```

Session output, by default, is recorded to `pyevm_export/erc_8004_sim_history.json`.

## Deeper Dive

For more detailed information about the different components of this simulation, please refer to the following `README` files:

- [Simulation Configs](./erc-8004-local-agents/configs/README.md)
- [Underlying Agent and Tools](./erc-8004-local-agents/src/erc_8004_local_agents/dspy_base_agent/README.md)
- [A2A Agent](./erc-8004-local-agents/src/erc_8004_local_agents/agents/README.md)
- [Simulation Runner](./erc-8004-local-agents/sim/README.md)
- [The Simulation TUI](./erc-8004-local-agents/src/erc_8004_local_agents/tui/README.md)

## Troubleshooting

### Environment Variables Not Loading

Ensure the `.env` file is in the project root directory (not in `erc-8004-local-agents/`) and contains:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Poetry Command Not Found

Make sure Poetry is installed and in your PATH. Install it following the [official installation guide](https://python-poetry.org/docs/#installation).

### Python Version Mismatch

This project requires Python 3.13.x. Verify your Python version:

```bash
python --version
# or
python3 --version
```

If you need to install Python 3.13, visit [python.org](https://www.python.org/downloads/).

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
