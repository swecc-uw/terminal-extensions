"""
Terminal Extensions - An extensible framework for intercepting and augmenting terminal commands.

This module provides an API for creating two types of hooks:
1. terminal_interceptor: Can modify, block, or replace commands before execution
2. terminal_callback: Executed after a command completes, with access to command results

Hooks can be registered via decorators or loaded from external Python modules.
"""

import importlib.util
import os
import platform
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from terminal_extensions.type_alias import CallbackFunc, InterceptorFunc


class HookType(Enum):
    """Types of terminal hooks available."""

    INTERCEPTOR = "interceptor"  # runs before command execution, can modify or block
    CALLBACK = "callback"  # runs after command execution


class HookRegistry:
    """Registry for managing terminal hooks."""

    def __init__(self) -> None:
        """Initialize the hook registry."""
        self._interceptors: List[Tuple[Optional[str], InterceptorFunc]] = []
        self._callbacks: List[Tuple[Optional[str], CallbackFunc]] = []

    def register_interceptor(
        self, func: InterceptorFunc, prefix: Optional[str] = None
    ) -> InterceptorFunc:
        """
        Register a terminal interceptor hook.

        Args:
            func: Function that receives a command string and returns either:
                 - A boolean: True to allow execution, False to block
                 - A string: Modified command to execute instead
            prefix: Optional command prefix this hook should apply to
                   If None, hook applies to all commands

        Returns:
            The original function (for decorator usage)
        """
        self._interceptors.append((prefix, func))
        return func

    def register_callback(self, func: CallbackFunc, prefix: Optional[str] = None) -> CallbackFunc:
        """
        Register a terminal callback hook.

        Args:
            func: Function called after command execution with signature:
                 func(command, return_code, stdout, stderr)
            prefix: Optional command prefix this hook should apply to
                   If None, hook applies to all commands

        Returns:
            The original function (for decorator usage)
        """
        self._callbacks.append((prefix, func))
        return func

    def get_interceptors(self) -> List[Tuple[Optional[str], InterceptorFunc]]:
        """Get all registered interceptor hooks."""
        return self._interceptors.copy()

    def get_callbacks(self) -> List[Tuple[Optional[str], CallbackFunc]]:
        """Get all registered callback hooks."""
        return self._callbacks.copy()

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._interceptors.clear()
        self._callbacks.clear()


# global registry instance
registry = HookRegistry()


# decorator functions
def terminal_interceptor(
    prefix: Optional[str] = None,
) -> Callable[[InterceptorFunc], InterceptorFunc]:
    """
    Decorator to register a terminal interceptor hook.

    Args:
        prefix: Optional command prefix this hook should apply to
               If None, hook applies to all commands

    Returns:
        Decorator function

    Example:
        @terminal_interceptor(prefix="git")
        def intercept_git(command: str) -> Union[bool, str]:
            # Log git commands
            print(f"Git command: {command}")
            return True  # Allow command to execute normally
    """

    def decorator(func: InterceptorFunc) -> InterceptorFunc:
        return registry.register_interceptor(func, prefix)

    return decorator


def terminal_callback(
    prefix: Optional[str] = None,
) -> Callable[[CallbackFunc], CallbackFunc]:
    """
    Decorator to register a terminal callback hook.

    Args:
        prefix: Optional command prefix this hook should apply to
               If None, hook applies to all commands

    Returns:
        Decorator function

    Example:
        @terminal_callback(prefix="ls")
        def after_ls(command: str, return_code: int,
          stdout: Optional[str], stderr: Optional[str]) -> None:
            if return_code == 0 and stdout:
                print(f"Directory contains {stdout.count('\\n')} items")
    """

    def decorator(func: CallbackFunc) -> CallbackFunc:
        return registry.register_callback(func, prefix)

    return decorator


def load_hooks_from_directory(directory: Union[str, Path]) -> Dict[str, int]:
    """
    Load hooks from Python files in the specified directory.

    Args:
        directory: Path to directory containing hook files

    Returns:
        Dict with counts of hooks loaded by type

    Raises:
        FileNotFoundError: If directory doesn't exist
        ImportError: If a hook file cannot be imported
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Hook directory not found: {directory_path}")

    # add hook directory to path
    parent_dir = str(directory_path.parent.absolute())
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    hook_counts: Dict[str, int] = {"interceptors": 0, "callbacks": 0}

    # track current hook counts to determine how many were added
    initial_interceptors = len(registry.get_interceptors())
    initial_callbacks = len(registry.get_callbacks())

    # import all Python files in the directory
    for file in directory_path.glob("*.py"):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        if spec and spec.loader:
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Error loading hook file {file.name}: {e}", file=sys.stderr)
                continue

    # calculate how many hooks were added
    hook_counts["interceptors"] = len(registry.get_interceptors()) - initial_interceptors
    hook_counts["callbacks"] = len(registry.get_callbacks()) - initial_callbacks

    return hook_counts


def execute_command(
    command: str, capture_output: bool = False
) -> Tuple[int, Optional[str], Optional[str]]:
    """
    Execute a shell command with appropriate platform-specific settings.

    Args:
        command: The command to execute
        capture_output: Whether to capture and return stdout/stderr

    Returns:
        Tuple of (return_code, stdout, stderr)
        stdout and stderr are None if capture_output is False
    """
    # use different shell on Windows vs Unix-like systems
    shell = True

    if platform.system() == "Windows":
        # use cmd.exe on Windows
        process_args = ["cmd.exe", "/c", command]
        shell = True
    else:
        # use system shell on Unix-like systems
        shell_path = os.environ.get("SHELL", "/bin/sh")
        process_args = [shell_path, "-c", command]
        shell = False

    try:
        if capture_output:
            result = subprocess.run(
                process_args, shell=shell, check=False, text=True, capture_output=True
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(process_args, shell=shell, check=False, text=True)
            return result.returncode, None, None
    except Exception as e:
        error_message = str(e)
        print(f"Error executing command: {error_message}", file=sys.stderr)
        return 1, None, error_message


def process_command(
    command: str, capture_output: bool = False
) -> Optional[Tuple[int, Optional[str], Optional[str]]]:
    """
    Process a command through all registered interceptors and execute if allowed.

    Args:
        command: The command to execute
        capture_output: Whether to capture and return stdout/stderr

    Returns:
        If command is executed: Tuple of (return_code, stdout, stderr)
        If command is blocked: None
    """
    # run through interceptors and get final command
    modified_command = command
    should_execute = True

    for prefix, interceptor in registry.get_interceptors():
        if prefix is None or command.startswith(prefix):
            try:
                result = interceptor(modified_command)
                if isinstance(result, bool):
                    # bool result determines whether to continue
                    should_execute = result
                    if not should_execute:
                        break
                elif isinstance(result, str):
                    # string result replaces the command
                    modified_command = result
            except Exception as e:
                print(f"Error in interceptor {interceptor.__name__}: {e}", file=sys.stderr)

    # execute the command if allowed
    if should_execute:
        return_code, stdout, stderr = execute_command(modified_command, capture_output)

        # run callbacks
        for prefix, callback in registry.get_callbacks():
            if prefix is None or command.startswith(prefix):
                try:
                    callback(command, return_code, stdout, stderr)
                except Exception as e:
                    print(f"Error in callback {callback.__name__}: {e}", file=sys.stderr)

        return return_code, stdout, stderr

    return None


class TerminalSession:
    """
    A simple terminal session that provides an interface for executing commands
    with hook support. Focuses on command processing while letting the system
    handle shell environment details.
    """

    def __init__(
        self, prompt: str = "$ ", hooks_directory: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Initialize a new terminal session.

        Args:
            prompt: The prompt to display before each command
            hooks_directory: Optional directory to load hooks from
        """
        self.prompt = prompt
        self.running = False

        # load hooks if directory provided
        if hooks_directory:
            try:
                hook_counts = load_hooks_from_directory(hooks_directory)
                print(
                    f"Loaded {hook_counts['interceptors']} interceptors and "
                    f"{hook_counts['callbacks']} callbacks"
                )
            except FileNotFoundError:
                pass

    def start(self) -> None:
        """Start the terminal session."""
        self.running = True
        print("Terminal Extensions Activated")

        while self.running:
            try:
                command = input(self.prompt).strip()

                if not command:
                    continue

                if command.lower() in ("exit", "quit"):
                    self.running = False
                    break

                # process command through hooks and execute
                result = process_command(command)
                if result is None:
                    print("Command was blocked by an interceptor")

            except KeyboardInterrupt:
                print()  # print newline after ^C
                continue
            except EOFError:
                # handle Ctrl+D (EOF)
                self.running = False
                break
            except Exception as e:
                print(f"Error in terminal session: {e}", file=sys.stderr)
                self.running = False
                break

    def stop(self) -> None:
        """Stop the terminal session."""
        self.running = False


def main() -> None:
    """
    Main entry point for the terminal extensions application.

    This function creates a terminal session with hooks loaded from
    the default .hooks directory.
    """
    # default hooks directory is in the current working directory
    hooks_dir = Path(".hooks")

    # create terminal session and start it
    terminal = TerminalSession(hooks_directory=hooks_dir)
    try:
        terminal.start()
    except Exception as e:
        print(f"Terminal session error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
