# ERC-8004 Simulation

This repository contains the code for the ERC-8004 simulation.

## Project Structure

```
erc-8004-sim/
├── erc-8004-contracts/         # ERC-8004 contracts
├── erc-8004-local-agents/      # ERC-8004 agents and simulation environment
└── erc-8004-py                 # ERC-8004 python sdk
```

## Running the Simulation

For convenience, one can use `run.sh` for setup and running the simulation. Ensure the script is executable (this project utilizes poetry, so ensure you have it installed (see [python-poetry/poetry](https://github.com/python-poetry/poetry))):

```bash
chmod +x run.sh
```

Then run the script to install dependencies:

```bash
./run.sh install
```

Then set the environment variables:

```bash
./run.sh setup-env
```

Then run the simulation:

```bash
./run.sh run-tui
```