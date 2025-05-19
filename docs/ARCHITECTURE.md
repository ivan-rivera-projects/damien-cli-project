# Damien-CLI Architecture

## Overview

Damien-CLI is a Python-based command-line interface (CLI) application built using the Click framework. It follows a feature-sliced architecture to promote modularity and maintainability.

## System Diagram

```mermaid
graph TD
subgraph User/External_LLM_Orchestrator
U[User via Terminal]
ELO[External LLM Orchestrator]
end

subgraph Damien_CLI_Application [Damien-CLI Application]
DC[damien_cli.cli_entry.py <br> (Click, Cmd Dispatch)]

subgraph Core_Components [damien_cli.core]
CONF[config.py]
LOGS[logging_setup.py]
EXC[exceptions.py]
UTIL[utils.py]
end

subgraph Feature_Slices [damien_cli.features]
EM[email_management <br> (commands.py, service.py, models.py)]
RM[rule_management <br> (commands.py, service.py, models.py, rule_storage.py)]
LLMA[llm_analysis <br> (Planned)]
end

subgraph Integrations_Layer [damien_cli.integrations]
GI[gmail_integration.py <br> (Gmail API Wrapper)]
end

subgraph Data_Storage_Local [Local Data (in ./data/)]
TOK[token.json]
RULES[rules.json]
LOGF[damien_session.log]
end
end

subgraph External_Services_APIs
G_API[Google Gmail API]
LLM_API_EXT[External LLM APIs <br> (Planned for Orchestrator)]
end

U --> DC; ELO --> DC;
DC --> CONF; DC --> LOGS;
DC --> EM; DC --> RM;
EM --> GI; RM --> GI; RM --> RULES;
GI --> G_API;
CONF --> TOK; CONF --> RULES; LOGS --> LOGF;

classDef user fill:#c9f,stroke:#333;
classDef cli fill:#f9f,stroke:#333;
classDef core fill:#ffc,stroke:#333;
classDef feature fill:#cff,stroke:#333;
classDef integration fill:#9cf,stroke:#333;
classDef storage fill:#lightgrey,stroke:#333;
classDef external fill:#9f9,stroke:#333;

class U,ELO user; class DC cli;
class CONF,LOGS,EXC,UTIL core;
class EM,RM,LLMA feature;
class GI integration;
class TOK,RULES,LOGF storage;
class G_API,LLM_API_EXT external;
```

## Key Modules

* **damien_cli/cli_entry.py**: The main entry point for the CLI using Click. Defines top-level commands and registers command groups from feature slices.
* **damien_cli/core/**: Contains shared, cross-cutting concerns:
  * **config.py**: Application configuration (paths, API scopes).
  * **logging_setup.py**: Configures logging for the application.
  * **exceptions.py** (Optional): Custom exception classes.
  * **utils.py** (Optional): Common utility functions.
* **damien_cli/features/**: Houses the feature slices. Each slice typically contains:
  * **commands.py**: Click command definitions specific to the feature.
  * **service.py**: Business logic for the feature.
  * **models.py**: Pydantic data models relevant to the feature.
  * (Other specific modules like rule_storage.py).
* **damien_cli/integrations/**: Modules for interacting with external services.
  * **gmail_integration.py**: Wraps all direct calls to the Google Gmail API.
* **data/**: Directory (created by the app) for storing runtime user data like token.json, rules.json, and logs. This directory is typically in .gitignore.
* **tests/**: Contains all automated tests, mirroring the application structure.

## Design Principles

* **Modularity & Separation of Concerns**: Each part of the application has a distinct responsibility.
* **Feature-Sliced Architecture**: Code is grouped by feature for easier navigation and development.
* **Testability**: Designed with unit and integration testing in mind.
* **Extensibility**: Structured to allow for new features and integrations to be added.
* **Clear CLI Interface**: Uses Click for a user-friendly command-line experience.
* **Programmatic Use**: Provides JSON output for integration with other scripts or LLM orchestrators.
