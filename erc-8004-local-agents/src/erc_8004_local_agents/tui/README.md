<!--
SPDX-FileCopyrightText: 2025 Semiotic Labs

SPDX-License-Identifier: Apache-2.0
-->

# ERC-8004 Simulation TUI

This directory contains a Textual-based Terminal User Interface (TUI) for monitoring the ERC-8004 agent simulation.

## Overview

The TUI provides a real-time view of the simulation, helping to visualize the interactions between agents and the state of the simulation environment.

## Features

- **Simulation Activity Log**: A live-updating panel that streams log messages from the simulation. This includes agent actions, contract events, and other important information.
- **Agent Status Panel**: A panel displaying the current status of all participating agents, including:
  - Agent ID
  - Ethereum Address
  - Current Reputation Score
  - Role (Client or Server)
  - Status

## Usage

The TUI is launched automatically when you run the simulation via `sim/run.py`. It provides a user-friendly way to observe the simulation without having to manually parse raw log files.
