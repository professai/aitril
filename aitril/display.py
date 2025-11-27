"""
Rich CLI display and progress tracking for AiTril.

Provides visual feedback with thinking indicators, progress bars,
token tracking, and task status updates.
"""

import sys
import time
from typing import Optional, List


class ProgressDisplay:
    """Manages rich progress display for CLI operations."""

    # Visual symbols
    THOUGHT_SYMBOL = "∴"
    TASK_SYMBOL = "✶"
    NEXT_SYMBOL = "⎿"
    CHECK_SYMBOL = "✓"
    ERROR_SYMBOL = "✗"
    ARROW_SYMBOL = "→"

    def __init__(self, show_timing: bool = True):
        """
        Initialize progress display.

        Args:
            show_timing: Whether to show timing information
        """
        self.show_timing = show_timing
        self.start_time = None
        self.current_task = None

    def thinking(self, duration: Optional[float] = None, show_ctrl_hint: bool = True) -> None:
        """
        Display thinking indicator.

        Args:
            duration: Duration of thinking in seconds (if already complete)
            show_ctrl_hint: Whether to show ctrl+o hint
        """
        if duration is not None:
            hint = " (ctrl+o to show thinking)" if show_ctrl_hint else ""
            print(f"\n{self.THOUGHT_SYMBOL} Thought for {duration:.1f}s{hint}", flush=True)
        else:
            print(f"\n{self.THOUGHT_SYMBOL} Thinking...", end="", flush=True)
            self.start_time = time.time()

    def task_start(self, task_name: str, next_task: Optional[str] = None, show_interrupt: bool = True) -> None:
        """
        Display task start with progress indicator.

        Args:
            task_name: Name of current task
            next_task: Name of next task (optional)
            show_interrupt: Whether to show escape to interrupt hint
        """
        self.current_task = task_name
        self.start_time = time.time()

        interrupt_hint = " (esc to interrupt)" if show_interrupt else ""
        print(f"\n{self.TASK_SYMBOL} {task_name}…{interrupt_hint}", flush=True)

        if next_task:
            print(f"  {self.NEXT_SYMBOL}  Next: {next_task}", flush=True)

    def task_complete(self, task_name: Optional[str] = None, show_timing: bool = True) -> None:
        """
        Display task completion.

        Args:
            task_name: Name of completed task (uses current if None)
            show_timing: Whether to show elapsed time
        """
        task = task_name or self.current_task or "Task"
        timing = ""

        if show_timing and self.show_timing and self.start_time:
            elapsed = time.time() - self.start_time
            timing = f" ({elapsed:.1f}s)"

        print(f"{self.CHECK_SYMBOL} {task}{timing}", flush=True)
        self.current_task = None
        self.start_time = None

    def task_error(self, task_name: Optional[str] = None, error_msg: Optional[str] = None) -> None:
        """
        Display task error.

        Args:
            task_name: Name of failed task (uses current if None)
            error_msg: Error message to display
        """
        task = task_name or self.current_task or "Task"
        error = f": {error_msg}" if error_msg else ""
        print(f"{self.ERROR_SYMBOL} {task} failed{error}", flush=True)
        self.current_task = None
        self.start_time = None

    def provider_thinking(self, provider_name: str) -> None:
        """
        Display provider-specific thinking indicator.

        Args:
            provider_name: Name of the provider
        """
        print(f"  {self.ARROW_SYMBOL} {provider_name} is thinking...", end="", flush=True)

    def provider_complete(self, provider_name: str, token_count: Optional[int] = None) -> None:
        """
        Display provider completion.

        Args:
            provider_name: Name of the provider
            token_count: Number of tokens used (if available)
        """
        tokens = f" [{token_count} tokens]" if token_count else ""
        print(f"\r  {self.CHECK_SYMBOL} {provider_name} responded{tokens}    ", flush=True)

    def show_stats(
        self,
        total_time: float,
        provider_stats: Optional[dict] = None,
        token_stats: Optional[dict] = None
    ) -> None:
        """
        Display statistics summary.

        Args:
            total_time: Total elapsed time
            provider_stats: Dictionary of provider statistics
            token_stats: Dictionary of token usage statistics
        """
        print(f"\n{self.THOUGHT_SYMBOL} Summary", flush=True)
        print(f"  Total time: {total_time:.2f}s", flush=True)

        if provider_stats:
            print(f"  Providers: {', '.join(provider_stats.keys())}", flush=True)

        if token_stats:
            total_tokens = sum(token_stats.values())
            print(f"  Tokens: {total_tokens:,}", flush=True)

    def show_cache_info(self, session_name: str, history_count: int) -> None:
        """
        Display cache/session information.

        Args:
            session_name: Current session name
            history_count: Number of items in history
        """
        print(f"\n{self.ARROW_SYMBOL} Session: {session_name} ({history_count} items in history)", flush=True)

    def divider(self, char: str = "─", length: int = 60) -> None:
        """
        Print a divider line.

        Args:
            char: Character to use for divider
            length: Length of divider
        """
        print(char * length, flush=True)

    def section_header(self, title: str, width: int = 60) -> None:
        """
        Print a section header.

        Args:
            title: Section title
            width: Width of section
        """
        print(f"\n{'=' * width}", flush=True)
        print(f"{title}", flush=True)
        print('=' * width, flush=True)

    def subsection_header(self, title: str, width: int = 60) -> None:
        """
        Print a subsection header.

        Args:
            title: Subsection title
            width: Width of subsection
        """
        print(f"\n{'─' * width}", flush=True)
        print(f"  {title}", flush=True)
        print('─' * width, flush=True)

    def bullet_list(self, items: List[str], indent: int = 2) -> None:
        """
        Print a bullet list.

        Args:
            items: List of items to display
            indent: Number of spaces to indent
        """
        for item in items:
            print(f"{' ' * indent}• {item}", flush=True)

    def key_value(self, key: str, value: any, indent: int = 2) -> None:
        """
        Print a key-value pair.

        Args:
            key: Key name
            value: Value to display
            indent: Number of spaces to indent
        """
        print(f"{' ' * indent}{key}: {value}", flush=True)

    def progress_bar(
        self,
        current: int,
        total: int,
        prefix: str = "",
        suffix: str = "",
        length: int = 40,
        fill: str = "█"
    ) -> None:
        """
        Display a progress bar.

        Args:
            current: Current progress value
            total: Total value
            prefix: Prefix text
            suffix: Suffix text
            length: Length of progress bar
            fill: Fill character
        """
        percent = current / total if total > 0 else 0
        filled_length = int(length * percent)
        bar = fill * filled_length + '-' * (length - filled_length)
        percent_str = f"{100 * percent:.1f}%"

        print(f'\r{prefix} |{bar}| {percent_str} {suffix}', end='', flush=True)

        if current >= total:
            print()  # New line when complete


# Global display instance
display = ProgressDisplay()
