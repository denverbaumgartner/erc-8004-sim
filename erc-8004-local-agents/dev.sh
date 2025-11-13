#!/bin/bash

# development and installation commands
python_command() {
    poetry run python
}

shell_command() {
    poetry shell
}

install_command() {
    poetry install --without dev
}

dev_command() {
    poetry install --with dev
}

requirements_command() {
    poetry run pip freeze > requirements.txt
}

format_command() {
    poetry run black .
}

docstring_format_command() {
    poetry run docformatter --black --style sphinx --in-place --recursive src/erc_8004_local_agents/
    poetry run docformatter --black --style sphinx --in-place --recursive tests/
}

pep8_check_command() {
    poetry run flake8 src/erc_8004_local_agents/
    poetry run flake8 tests/
}

sort_command() {
    poetry run isort .
}

lint_command() {
    poetry run pyright .
}

test_command() {
    poetry run pytest --testmon -p no:warnings --ignore=tests/test_e2e_agent_arena.py
}

commit_command() {
    license_command
    format_command
    docstring_format_command
    sort_command
    lint_command
    pep8_check_command
    test_command
    requirements_command
}

license_command() {
    poetry run reuse annotate --copyright "2025 Semiotic Labs" --license "Apache-2.0" sim/ src/erc_8004_local_agents/ tests/
}

# help menu
show_help() {
    echo "Usage: ./nli [option]"
    echo "Options:"
    
    # development and installation commands
    echo "  python                 Run Python"
    echo "  shell                  Run shell"
    echo "  install                Install dependencies"
    echo "  dev                    Install dependencies with dev"
    echo "  requirements           Generate requirements.txt"
    echo "  format                 Format the code"
    echo "  docstring-format       Format the docstrings"
    echo "  pep-check              Check the PEP8 compliance"
    echo "  sort                   Sort imports with isort"
    echo "  lint                   Lint the code"
    echo "  test                   Run the tests"
    echo "  commit                 Format, lint, and test the code"
    echo "  license                Add license headers to files"
}

# handle command line arguments
if [ -z "$1" ]; then
    show_help
else
    case "$1" in

        # development and installation commands
        "python") python_command ;;
        "shell") shell_command ;;
        "install") install_command ;;
        "dev") dev_command ;;
        "requirements") requirements_command ;;
        "format") format_command ;;
        "docstring-format") docstring_format_command ;;
        "pep-check") pep8_check_command ;;
        "sort") sort_command ;;
        "lint") lint_command ;;
        "test") test_command ;;
        "commit") commit_command ;;
        "license") license_command ;;
        *)
            echo "Usage: $0 {test|lint|format|docstring-format|pep-check|lint|test|commit|license}"
            exit 1
            ;;
    esac
fi