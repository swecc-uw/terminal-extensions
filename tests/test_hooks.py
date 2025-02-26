import pytest
from typing import List
from terminal_extensions.cli import terminal_hook, registered_hooks, process_command


def setup_function() -> None:
    registered_hooks.clear()


def test_hook_registration() -> None:
    @terminal_hook("test")
    def test_hook(command: str) -> bool:
        return True

    assert len(registered_hooks) == 1
    assert registered_hooks[0][0] == "test"


def test_global_hook() -> None:
    called: List[str] = []

    @terminal_hook()
    def global_hook(command: str) -> bool:
        called.append(command)
        return True

    process_command("any command")
    assert called == ["any command"]


def test_prefix_hook() -> None:
    called: List[str] = []

    @terminal_hook("git")
    def git_hook(command: str) -> bool:
        called.append(command)
        return True

    process_command("git status")
    process_command("other command")
    assert called == ["git status"]


def test_hook_chain_stopping() -> None:
    called: List[int] = []

    @terminal_hook()
    def hook1(command: str) -> bool:
        called.append(1)
        return False

    @terminal_hook()
    def hook2(command: str) -> bool:
        called.append(2)
        return True

    process_command("test")
    assert called == [1]
