# SPDX-FileCopyrightText: 2025 Semiotic AI, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Textual TUI application for ERC-8004 simulation monitoring."""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, RichLog, Static


class TextualLogHandler(logging.Handler):
    """Custom logging handler that writes to a Textual RichLog widget."""

    def __init__(self, log_widget: RichLog):
        """Initialize the handler.

        Args:
            log_widget: The Textual RichLog widget to write logs to
        """
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the TUI.

        Args:
            record: The log record to emit
        """
        try:
            msg = self.format(record)
            # Use call_from_thread for thread-safe updates
            self.log_widget.write(msg)
        except Exception:
            self.handleError(record)


class SimulationTUI(App):
    """A Textual app to monitor ERC-8004 simulation activity."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 100%;
    }

    #log-container {
        width: 70%;
        height: 100%;
        border: solid $primary;
    }

    #log {
        height: 100%;
        overflow-y: auto;
    }

    #agents-container {
        width: 30%;
        height: 100%;
        border: solid $secondary;
    }

    #agents {
        height: 100%;
        overflow-y: auto;
    }

    .panel-title {
        background: $boost;
        color: $text;
        text-align: center;
        padding: 1;
    }
    """

    def __init__(
        self,
        agents_info: str,
        simulation_coro: Optional[Callable[[], Coroutine]] = None,
        post_simulation_callback: Optional[Callable[[], Coroutine]] = None,
        *args,
        **kwargs,
    ):
        """Initialize the TUI app.

        Args:
            agents_info: Formatted string containing agent information
            simulation_coro: Optional coroutine factory for running simulation
                as worker
            post_simulation_callback: Optional callback to run after simulation
                completes
        """
        super().__init__(*args, **kwargs)
        self.agents_info = agents_info
        self.simulation_coro = simulation_coro
        self.post_simulation_callback = post_simulation_callback
        self._tui_logger_configured = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(name="ERC-8004 Simulation Monitor")

        with Horizontal(id="main-container"):
            # Left panel: Simulation Activity
            with Container(id="log-container"):
                yield Static("Simulation Activity", classes="panel-title")
                yield RichLog(id="log", highlight=True, markup=True)

            # Right panel: Agents
            with Container(id="agents-container"):
                yield Static("Agents", classes="panel-title")
                yield Static(self.agents_info, id="agents")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mounting of the app."""
        # Set focus to log widget so it scrolls properly
        log = self.query_one("#log", RichLog)
        log.focus()

        # Set up TUI logging now that widgets are ready
        self.setup_tui_logging()

        # Start simulation worker if provided
        if self.simulation_coro:
            self.run_worker(self._run_simulation_worker())

    def setup_tui_logging(self) -> None:
        """Configure the TUI logger to write to the log widget."""
        if self._tui_logger_configured:
            return

        log_widget = self.query_one("#log", RichLog)
        tui_handler = TextualLogHandler(log_widget)
        tui_handler.setFormatter(logging.Formatter("%(message)s"))

        tui_logger = logging.getLogger("simulation.tui")
        tui_logger.setLevel(logging.INFO)
        tui_logger.addHandler(tui_handler)
        tui_logger.propagate = False

        self._tui_logger_configured = True

    def update_agents_panel(self, agents_data: Dict[str, Dict[str, Any]]) -> None:
        """Update the agents panel with current status and reputation.

        Args:
            agents_data: Dictionary mapping agent_id to agent data
                        (status, reputation, address, role)
        """
        if not agents_data:
            return

        try:
            lines = []
            lines.append("[bold cyan]ERC-8004 Simulation[/bold cyan]")
            lines.append("")

            for agent_id, data in agents_data.items():
                address = data.get("address", "N/A")
                status = data.get("status", "Unknown")
                reputation = data.get("reputation", 0)
                role = data.get("role", "unknown")

                # Determine role display
                if role == "simulation":
                    role_display = "[green]Client Agent[/green]"
                else:
                    role_display = "[blue]Server Agent[/blue]"

                # Format agent display
                lines.append(
                    f"[bold]{agent_id}[/bold] ({address[:10]}...) - Rep: {reputation}"
                )
                lines.append(f"  Role: {role_display}")
                lines.append(f"  [italic]Status: {status}[/italic]")
                lines.append("")

            # Update the agents widget
            agents_widget = self.query_one("#agents", Static)
            agents_widget.update("\n".join(lines))

        except Exception as e:
            # Silently fail to avoid disrupting the TUI
            logging.getLogger(__name__).debug(f"Failed to update agents panel: {e}")

    async def _run_simulation_worker(self) -> None:
        """Run the simulation as a background worker."""
        if not self.simulation_coro:
            return

        tui_logger = logging.getLogger("simulation.tui")

        # Wait for TUI to fully render before starting simulation
        tui_logger.info(
            "[dim]TUI initialized. Starting simulation in 2 seconds...[/dim]"
        )
        await asyncio.sleep(2)

        try:
            await self.simulation_coro()

            # Run post-simulation callback if provided (e.g., generate summary)
            if self.post_simulation_callback:
                await self.post_simulation_callback()

        except Exception as e:
            tui_logger.error(f"[red bold]Simulation error:[/red bold] {e}")
        finally:
            # Notify user that simulation is complete and they can exit
            tui_logger.info("")
            tui_logger.info(
                "[bold yellow]Simulation complete. Press Ctrl+C to exit.[/bold yellow]"
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def on_key(self, event) -> None:
        """Handle key press events."""
        if event.key == "ctrl+c":
            self.exit()
