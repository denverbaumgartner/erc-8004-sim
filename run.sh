#!/bin/bash

# development and installation commands
install_submodules_command() {
    git submodule update --init --recursive
}

install_dependencies_command() {
    cd erc-8004-local-agents
    chmod +x dev.sh
    ./dev.sh install
    cd ..
}

install_command() {
    install_submodules_command
    install_dependencies_command
}

# set up .env file
setup_env_file() {
    cp .env.example .env
}

set_openrouter_api_key() {
    if [ -f .env ]; then
        sed -i '' '/^OPENROUTER_API_KEY=/d' .env
    fi

    read -p "Enter your OPENROUTER_API_KEY: " api_key
    echo "OPENROUTER_API_KEY=$api_key" >> .env
}

setup_env_command() {
    setup_env_file
    set_openrouter_api_key "$1"
}


# run commands
run_tui_command() {
    cd erc-8004-local-agents
    chmod +x dev.sh
    poetry run python sim/run.py --tui
    cd ..
}


# help menu
show_help() {
    echo "Usage: ./run.sh [option]"
    echo "Options:"
    echo "  install                Install dependencies"
    echo "  setup-env              Setup the .env file"
    echo "  run-tui                Run the simulation with the TUI"
}

# handle command line arguments
if [ -z "$1" ]; then
    show_help
else
    case "$1" in
        # installation commands
        "install") install_command ;;
        
        # setup commands
        "setup-env") setup_env_command ;;
        
        # run commands
        "run-tui") run_tui_command ;;
        *)
            echo "Usage: $0 {install|setup-env|run-tui}"
            exit 1
            ;;
    esac
fi