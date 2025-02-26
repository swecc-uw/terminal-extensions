import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

registered_hooks: List[Tuple[Optional[str], Callable]] = []


def terminal_hook(prefix: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        registered_hooks.append((prefix, func))
        return func

    return decorator


def load_hooks_from_directory(directory: Path) -> None:
    if not directory.exists():
        return

    sys.path.insert(0, str(directory.parent))

    for file in directory.glob("*.py"):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)


def process_command(command: str) -> bool:
    should_continue = True

    for prefix, hook in registered_hooks:
        if prefix is None or command.startswith(prefix):
            try:
                result = hook(command)
                should_continue = result if isinstance(result, bool) else True
                if not should_continue:
                    break
            except Exception as e:
                print(f"Error in hook {hook.__name__}: {e}", file=sys.stderr)

    return should_continue


def main() -> None:
    hooks_dir = Path(".hooks")
    load_hooks_from_directory(hooks_dir)

    while True:
        try:
            command = input("$ ")
            if command.strip() == "exit":
                break

            should_continue = process_command(command)

            if should_continue:
                try:
                    subprocess.run(command, shell=True, check=False)
                except Exception as e:
                    print(f"Error executing command: {e}", file=sys.stderr)

        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()
