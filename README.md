# Terminal Extensions

A lightweight Python library for extending your terminal environment with custom hooks. This library allows you to easily add custom functionality to your terminal by writing simple Python functions.

## Features

- Simple decorator-based API for registering hooks
- Support for both prefix-specific and global hooks
- Automatic loading of hooks from a `.hooks` directory
- Minimal overhead and easy integration

## Installation

```bash
pip install terminal-extensions
```

## Quick Start

1. Create a `.hooks` directory in your project
2. Add Python files with your hooks:

```python
from terminal_extensions import terminal_hook

# Hook that runs for all commands
@terminal_hook()
def log_commands(command: str) -> bool:
    print(f"Executing: {command}")
    return True  # Continue processing other hooks

# Hook that only runs for commands starting with "git"
@terminal_hook("git")
def git_helper(command: str) -> bool:
    if command == "git status":
        print("Nice job checking in!")
    return True
```

3. Run the terminal extensions:

```bash
terminal-ext
```

## Writing Hooks

### Hook Types

1. **Global Hooks** - Run for every command:
```python
@terminal_hook()
def my_hook(command: str) -> bool:
    # Process any command
    return True
```

2. **Prefix Hooks** - Run only for commands with specific prefixes:
```python
@terminal_hook("docker")
def docker_hook(command: str) -> bool:
    # Process only docker commands
    return True
```

### Hook Return Values

- Return `True` to continue processing other hooks and execute the command
- Return `False` to stop processing and prevent command execution

### Hook Organization

Place your hooks in `.py` files within the `.hooks` directory:

```
your_project/
├── .hooks/
│   ├── git_hooks.py
│   ├── docker_hooks.py
│   └── general_hooks.py
└── ...
```

## Examples

### Command Logging
```python
@terminal_hook()
def log_commands(command: str) -> bool:
    with open("command_history.log", "a") as f:
        f.write(f"{command}\n")
    return True
```

### Security Check
```python
@terminal_hook("rm")
def confirm_delete(command: str) -> bool:
    response = input("Are you sure you want to delete? [y/N] ")
    return response.lower() == 'y'
```

### Command Enhancement
```python
@terminal_hook("git")
def git_shortcuts(command: str) -> bool:
    if command == "git st":
        print("Expanding to git status...")
        return "git status"
    return True
```

## Configuration

The library automatically looks for hooks in the `.hooks` directory of your current working directory.

## Error Handling

Hooks are executed in a safe environment. If a hook raises an exception:
- The error is logged to stderr
- Processing continues with the next hook
- The original command is still executed (unless explicitly prevented)

## Contributing

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for guidelines on contributing to this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
