# Contributing to Terminal Extensions

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/terminal-extensions.git
   cd terminal-extensions
   ```
3. Set up your development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Development Process

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b <branch name>
   ```

2. Make your changes, following our coding standards:
   - Use type hints for all function parameters and return values
   - Follow PEP 8 style guidelines
   - Write tests for new functionality
   - Update documentation as needed

3. Run the test suite:
   ```bash
   pytest
   ```

4. Run the linters:
   ```bash
   mypy .
   ruff check .
   black .
   ```

5. Commit your changes:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

## Pull Request Process

1. Update your fork with the latest changes from main:
   ```bash
   git remote add upstream https://github.com/swecc-uw/terminal-extensions.git
   git fetch upstream
   git rebase upstream/main
   ```

2. Push your changes:
   ```bash
   git push origin <branch name>
   ```

3. Create a Pull Request through GitHub

4. In your PR description:
   - Describe the changes you've made
   - Reference any related issues
   - Include examples if applicable

## Testing

- Write unit tests for new functionality

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions and classes
- Include example usage in docstrings
- Update type hints in function signatures

## Release Process

Version numbers follow semantic versioning (MAJOR.MINOR.PATCH). Update version in pyproject.toml

## License

By contributing to Terminal Extensions, you agree that your contributions will be licensed under the MIT License.
