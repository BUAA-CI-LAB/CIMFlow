# Contributing to CIMFlow

Thank you for your interest in contributing to CIMFlow! We welcome contributions from the community to help improve the framework.

## Getting Started

1.  **Fork the repository**: Click the "Fork" button on the GitHub repository page.
2.  **Clone your fork**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/CIMFlow.git
    cd CIMFlow
    ./install.sh
    ```
3.  **Create a branch**:
    ```bash
    git checkout -b feature/my-new-feature
    ```

## Development Workflow

1.  **Make your changes**: Implement your feature or fix.
2.  **Run tests**: Ensure all tests pass.
    ```bash
    pytest
    ```
3.  **Lint your code**: We use `ruff` for linting.
    ```bash
    pip install ruff
    ruff check src/
    ```

## Submitting a Pull Request

1.  Push your branch to your fork.
2.  Open a Pull Request (PR) against the `main` branch of the official repository.
3.  Provide a clear description of your changes and link to any relevant issues.

## Reporting Issues

If you find a bug or have a feature request, please open an issue on the [GitHub Issues](https://github.com/BUAA-CI-LAB/CIMFlow/issues) page.
