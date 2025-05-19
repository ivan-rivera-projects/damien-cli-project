# Damien-CLI Developer Guide

This guide is for developers looking to contribute to or understand the internals of Damien-CLI.

## Project Structure

Refer to `docs/ARCHITECTURE.md` for a detailed overview of the project structure.

Key directories:
* `damien_cli/`: Main application package.
  * `core/`: Shared components.
  * `features/`: Feature-sliced modules (e.g., `email_management`, `rule_management`).
  * `integrations/`: Wrappers for external APIs (e.g., `gmail_integration.py`).
* `tests/`: Automated tests, mirroring the `damien_cli` structure.
* `data/`: Runtime data (tokens, rules, logs) - ignored by Git.

## Setup for Development

1. **Prerequisites:** Python 3.13+, Poetry.
2. **Clone:** `git clone <repository_url>`
3. **Navigate:** `cd damien-cli`
4. **Install Dependencies (including dev dependencies):** `poetry install`
5. **Activate Virtual Environment:** `poetry shell` (This allows you to run `damien` directly instead of `poetry run damien`).
6. **Set up `credentials.json`:** Follow `docs/GMAIL_API_SETUP.md`.
7. **Initial Login:** Run `damien login` (or `poetry run damien login` if not in poetry shell).

## Running the CLI during Development

* Using Poetry: `poetry run damien <command> [options]`
* If inside Poetry shell: `damien <command> [options]`

## Running Tests

Pytest is used for testing.

* Run all tests:
```bash
poetry run pytest
```
* Run with verbose output:
```bash
poetry run pytest -v
```
* Run a specific test file:
```bash
poetry run pytest -v tests/features/email_management/test_commands.py
```
* Run a specific test function:
```bash
poetry run pytest -v tests/features/email_management/test_commands.py::test_emails_list_human_output
```
* Run tests and generate a coverage report:
```bash
poetry run pytest --cov=damien_cli
```
This will show test coverage for the `damien_cli` package. An HTML report can often be generated in `htmlcov/`.

## Coding Conventions

* **Formatting:** Black is used for code formatting. Consider setting up your IDE to format with Black on save.
```bash
poetry run black .
```
* **Linting:** Flake8 is used for linting.
```bash
poetry run flake8 damien_cli tests
```
* **Type Hinting:** Use Python type hints for all function signatures and important variables.
* **Docstrings:** Add docstrings to modules, classes, and functions (e.g., Google style or reStructuredText).

## Adding a New CLI Command

1. **Identify the Feature Slice:** Determine if the command fits into an existing feature (e.g., `email_management`) or needs a new one under `damien_cli/features/`.
2. **Create/Update `commands.py`:** In the relevant feature slice, add your new Click command function(s).
3. **Implement Logic:** Add business logic to the feature's `service.py` and interaction with external APIs to the relevant module in `damien_cli/integrations/`.
4. **Register Command:** If it's a new command group or a top-level command, register it in `damien_cli/cli_entry.py`.
5. **Add Models:** If your command handles new data structures, define Pydantic models in the feature's `models.py`.
6. **Write Unit Tests:** Create corresponding tests in the `tests/` directory.
7. **Update Documentation:** Add the new command to `docs/USER_GUIDE.md`.

## Git Workflow (Example)

* Work on feature branches (e.g., `feature/add-rule-application`).
* Make small, atomic commits.
* Open Pull Requests for review (if collaborating).
* Ensure tests pass before merging.
