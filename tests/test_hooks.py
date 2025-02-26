"""
Tests for the terminal hooks API.

This module contains comprehensive tests for both the interceptor and callback
hook functionality, ensuring proper registration, execution, and error handling.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, cast

import pytest
from unittest.mock import MagicMock, patch

from terminal_extensions.cli import (
    HookRegistry,
    registry,
    terminal_interceptor,
    terminal_callback,
    process_command,
    load_hooks_from_directory,
    execute_command,
    TerminalSession,
)


# Setup and teardown for each test
@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    original_registry = registry
    test_registry = HookRegistry()
    # Replace the global registry instance
    globals()["registry"] = test_registry
    yield test_registry
    # Restore the original registry
    globals()["registry"] = original_registry


# Tests for hook registration
class TestHookRegistration:
    def test_interceptor_registration(self, clean_registry):
        """Test that interceptors are properly registered."""

        @terminal_interceptor("test")
        def test_hook(command: str) -> bool:
            return True

        interceptors = clean_registry.get_interceptors()
        assert len(interceptors) == 1
        assert interceptors[0][0] == "test"
        assert interceptors[0][1] == test_hook

    def test_callback_registration(self, clean_registry):
        """Test that callbacks are properly registered."""

        @terminal_callback("test")
        def test_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            pass

        callbacks = clean_registry.get_callbacks()
        assert len(callbacks) == 1
        assert callbacks[0][0] == "test"
        assert callbacks[0][1] == test_callback

    def test_global_hook_registration(self, clean_registry):
        """Test that global hooks (no prefix) are properly registered."""

        @terminal_interceptor()
        def global_interceptor(command: str) -> bool:
            return True

        @terminal_callback()
        def global_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            pass

        interceptors = clean_registry.get_interceptors()
        callbacks = clean_registry.get_callbacks()

        assert len(interceptors) == 1
        assert interceptors[0][0] is None

        assert len(callbacks) == 1
        assert callbacks[0][0] is None

    def test_multiple_hook_registration(self, clean_registry):
        """Test that multiple hooks can be registered."""

        @terminal_interceptor("git")
        def git_interceptor(command: str) -> bool:
            return True

        @terminal_interceptor("ls")
        def ls_interceptor(command: str) -> bool:
            return True

        @terminal_callback("git")
        def git_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            pass

        interceptors = clean_registry.get_interceptors()
        callbacks = clean_registry.get_callbacks()

        assert len(interceptors) == 2
        assert len(callbacks) == 1

    def test_registry_clear(self, clean_registry):
        """Test that registry can be cleared."""

        @terminal_interceptor("test")
        def test_hook(command: str) -> bool:
            return True

        @terminal_callback("test")
        def test_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            pass

        assert len(clean_registry.get_interceptors()) == 1
        assert len(clean_registry.get_callbacks()) == 1

        clean_registry.clear()

        assert len(clean_registry.get_interceptors()) == 0
        assert len(clean_registry.get_callbacks()) == 0


# Tests for interceptor functionality
class TestInterceptors:
    def test_global_interceptor(self, clean_registry):
        """Test that global interceptors are called for all commands."""
        called: List[str] = []

        @terminal_interceptor()
        def global_hook(command: str) -> bool:
            called.append(command)
            return True

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            process_command("any command")
            process_command("another command")

        assert called == ["any command", "another command"]

    def test_prefix_interceptor(self, clean_registry):
        """Test that prefix interceptors are only called for matching commands."""
        called: List[str] = []

        @terminal_interceptor("git")
        def git_hook(command: str) -> bool:
            called.append(command)
            return True

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            process_command("git status")
            process_command("other command")

        assert called == ["git status"]

    def test_interceptor_chain_stopping(self, clean_registry):
        """Test that the interceptor chain stops when a hook returns False."""
        called: List[int] = []

        @terminal_interceptor()
        def hook1(command: str) -> bool:
            called.append(1)
            return False

        @terminal_interceptor()
        def hook2(command: str) -> bool:
            called.append(2)
            return True

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            result = process_command("test")

        assert called == [1]
        assert result is None  # Command execution should be blocked

    def test_interceptor_command_modification(self, clean_registry):
        """Test that interceptors can modify commands."""

        @terminal_interceptor()
        def modify_command(command: str) -> str:
            return "modified command"

        with patch(
            "terminal_extensions.cli.execute_command", return_value=(0, "", "")
        ) as mock_execute:
            process_command("original command")

        mock_execute.assert_called_once_with("modified command", False)

    def test_interceptor_exception_handling(self, clean_registry):
        """Test that exceptions in interceptors are properly handled."""

        @terminal_interceptor()
        def failing_hook(command: str) -> bool:
            raise ValueError("Test error")

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            with patch("sys.stderr"):  # Suppress error output
                process_command("test")

        assert True  # The fact that we got here means the exception was handled


# Tests for callback functionality
class TestCallbacks:
    def test_callback_execution(self, clean_registry):
        """Test that callbacks are executed after command execution."""
        callback_calls = []

        @terminal_callback()
        def record_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            callback_calls.append((command, return_code, stdout, stderr))

        with patch(
            "terminal_extensions.cli.execute_command", return_value=(0, "output", "")
        ):
            process_command("test command")

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test command", 0, "output", "")

    def test_prefix_callback(self, clean_registry):
        """Test that prefix callbacks are only called for matching commands."""
        callback_calls = []

        @terminal_callback("git")
        def git_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            callback_calls.append(command)

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            process_command("git status")
            process_command("other command")

        assert callback_calls == ["git status"]

    def test_callback_exception_handling(self, clean_registry):
        """Test that exceptions in callbacks are properly handled."""

        @terminal_callback()
        def failing_callback(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            raise ValueError("Test error")

        with patch("terminal_extensions.cli.execute_command", return_value=(0, "", "")):
            with patch("sys.stderr"):  # Suppress error output
                process_command("test")

        assert True  # The fact that we got here means the exception was handled


# Tests for command execution
class TestCommandExecution:
    def test_execute_command_success(self):
        """Test that commands are properly executed."""
        # Use 'echo' as a simple cross-platform command
        return_code, stdout, stderr = execute_command("echo test", capture_output=True)

        assert return_code == 0
        assert stdout is not None
        assert "test" in stdout
        assert stderr == ""

    def test_execute_command_failure(self):
        """Test that command failures are properly handled."""
        # Use a non-existent command
        return_code, stdout, stderr = execute_command(
            "nonexistent_command_12345", capture_output=True
        )

        assert return_code != 0
        assert stderr is not None


# Tests for hook loading from directory
class TestHookLoading:
    def test_load_hooks_from_directory(self, clean_registry, tmp_path):
        """Test loading hooks from a directory."""
        # Create a temporary hook file
        hook_dir = tmp_path / ".hooks"
        hook_dir.mkdir()

        hook_file = hook_dir / "test_hooks.py"
        hook_file.write_text(
            """
from terminal_extensions.cli import terminal_interceptor, terminal_callback
from typing import Optional

@terminal_interceptor("test")
def test_interceptor(command: str) -> bool:
    return True

@terminal_callback("test")
def test_callback(command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]) -> None:
    pass
"""
        )

        # Load hooks from the directory
        hook_counts = load_hooks_from_directory(hook_dir)

        # Check that hooks were loaded
        assert hook_counts["interceptors"] == 1
        assert hook_counts["callbacks"] == 1

        # Check registry
        assert len(clean_registry.get_interceptors()) == 1
        assert len(clean_registry.get_callbacks()) == 1

    def test_load_hooks_nonexistent_directory(self):
        """Test loading hooks from a non-existent directory."""
        with pytest.raises(FileNotFoundError):
            load_hooks_from_directory("/nonexistent/directory")

    def test_load_hooks_with_errors(self, clean_registry, tmp_path):
        """Test loading hooks from a directory with errors."""
        # Create a temporary hook file with syntax error
        hook_dir = tmp_path / ".hooks"
        hook_dir.mkdir()

        hook_file = hook_dir / "error_hooks.py"
        hook_file.write_text(
            """
from terminal_extensions.cli import terminal_interceptor

# Syntax error
@terminal_interceptor("test)  # Missing closing quote
def test_hook(command):
    return True
"""
        )

        # Suppress stderr during the test
        with patch("sys.stderr"):
            # Should not raise exception
            hook_counts = load_hooks_from_directory(hook_dir)

        # Check that no hooks were loaded due to error
        assert hook_counts["interceptors"] == 0
        assert hook_counts["callbacks"] == 0


# Tests for TerminalSession
class TestTerminalSession:
    def test_terminal_session_initialization(self):
        """Test terminal session initialization."""
        session = TerminalSession(prompt=">>> ")
        assert session.prompt == ">>> "
        assert session.running is False

    def test_terminal_session_with_hooks_dir(self, tmp_path):
        """Test terminal session with hooks directory."""
        hook_dir = tmp_path / ".hooks"
        hook_dir.mkdir()

        # Create a valid hook file
        hook_file = hook_dir / "test_hooks.py"
        hook_file.write_text(
            """
from terminal_extensions.cli import terminal_interceptor

@terminal_interceptor("test")
def test_hook(command: str) -> bool:
    return True
"""
        )

        with patch("builtins.print"):  # Suppress output
            session = TerminalSession(hooks_directory=hook_dir)

        # One interceptor should be registered
        assert len(registry.get_interceptors()) > 0

    def test_terminal_session_nonexistent_hooks_dir(self):
        """Test terminal session with non-existent hooks directory."""
        # Should not raise exception
        session = TerminalSession(hooks_directory="/nonexistent/directory")
        assert session.running is False

    def test_terminal_session_start_stop(self):
        """Test starting and stopping terminal session."""
        session = TerminalSession()

        # Mock input to return "exit" when called
        with patch("builtins.input", return_value="exit"):
            session.start()

        assert session.running is False

        # Test manual stop
        session.running = True
        session.stop()
        assert session.running is False


# Tests for integration between components
class TestIntegration:
    def test_interceptor_prevents_command_execution(self, clean_registry):
        """Test that when an interceptor returns False, the command is not executed."""

        @terminal_interceptor()
        def block_command(command: str) -> bool:
            return False

        mock_execute = MagicMock()
        with patch("terminal_extensions.cli.execute_command", mock_execute):
            process_command("test")

        # execute_command should not be called
        mock_execute.assert_not_called()

    def test_interceptor_then_callback(self, clean_registry):
        """Test interceptor modifying command and callback seeing results."""
        interceptor_called = []
        callback_called = []

        @terminal_interceptor()
        def modify_command(command: str) -> str:
            interceptor_called.append(command)
            return "modified " + command

        @terminal_callback()
        def check_results(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            # Original command is passed to callback, not modified command
            callback_called.append((command, return_code))

        with patch(
            "terminal_extensions.cli.execute_command", return_value=(0, "output", "")
        ):
            process_command("original")

        assert interceptor_called == ["original"]
        assert callback_called == [("original", 0)]

    def test_process_command_full_flow(self, clean_registry):
        """Test the full flow of process_command with real command execution."""
        interceptor_called = []
        callback_called = []

        @terminal_interceptor()
        def log_command(command: str) -> bool:
            interceptor_called.append(command)
            return True

        @terminal_callback()
        def log_result(
            command: str, return_code: int, stdout: Optional[str], stderr: Optional[str]
        ) -> None:
            callback_called.append((command, return_code))

        # Use a simple echo command that should work cross-platform
        result = process_command("echo test", capture_output=True)

        assert interceptor_called == ["echo test"]
        assert len(callback_called) == 1
        assert callback_called[0][0] == "echo test"
        assert callback_called[0][1] == 0  # Success return code

        # Check results
        assert result is not None
        return_code, stdout, stderr = result
        assert return_code == 0
        assert stdout is not None
        assert "test" in stdout


if __name__ == "__main__":
    pytest.main(["-v", __file__])
