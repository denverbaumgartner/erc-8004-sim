# ERC-8004 Local Agents

This directory contains the code for the ERC-8004 local agents.

## Project Setup

We use poetry to manage dependencies. Ensure you have it installed (see [python-poetry/poetry](https://github.com/python-poetry/poetry)). One can use the `dev.sh` script to setup the project.

```bash
chmod +x dev.sh
./dev.sh dev
```

This will install the dependencies with the development dependencies. One can then run the following to perform ci/cd checks:

```bash
./dev.sh commit
```

This will run the following checks:

- Format the code
- Format the docstrings
- Sort imports with isort
- Lint the code
- Check the PEP8 compliance
- Run the tests
- Generate requirements.txt

One can then run the following to run the simulation:

```bash
poetry run python sim/run.py --tui
```