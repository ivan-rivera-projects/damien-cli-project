# Damien-CLI Roadmap

This document outlines the current development status and future plans for Damien-CLI.

## Current Status (2024-05-18)

The project has successfully completed the initial development phases, establishing a core set of functionalities for Gmail management.

* **Phase 0: Foundation & Setup - COMPLETE**
* **Phase 1: Core Email Read Operations - COMPLETE**
* **Phase 2: Core Email Write Operations & Basic Rules - COMPLETE**
* **Phase 3 (A3.1): Refine JSON output for CLI commands - COMPLETE**

Key features implemented:
* Secure OAuth 2.0 authentication with Gmail.
* Listing and detailed viewing of emails.
* Email modification: trash, permanent delete (with safeguards), labeling, mark as read/unread.
* `--dry-run` mode for all write operations.
* User confirmation for destructive actions.
* Basic rule management: add, list, delete rules via JSON definitions.
* Core logic for rule matching against email fields.
* Consistent JSON output for programmatic use.
* Comprehensive unit test suite.

## Next Steps: Phase 3 - LLM Integration & Advanced Features

The immediate focus is on integrating Large Language Model (LLM) capabilities and enhancing rule application.

* **A3.2: Develop External LLM Orchestrator Prototype**
  * **Goal:** Create a separate Python application that uses an LLM (e.g., OpenAI API) to understand natural language commands from a user.
  * This orchestrator will translate user requests into Damien-CLI command invocations (using `subprocess` and Damien's JSON output).
  * It will parse Damien's JSON responses and use the LLM to present results back to the user or decide on follow-up actions.
  * **Key Tasks:**
    * Define Damien's commands as "tools/functions" for the LLM.
    * Implement the interaction loop: User -> LLM -> Damien -> LLM -> User.

* **A3.3: Implement Rule Application Logic (`damien rules apply`)**
  * **Goal:** Enable Damien to process emails against the configured rules and take the defined actions.
  * **Key Tasks:**
    * Create a `damien rules apply` command.
    * Implement logic to:
      * Fetch emails (potentially based on a query or all emails).
      * For each email, transform its data into the simplified format expected by the `does_email_match_rule` service.
      * If a rule matches, queue the defined actions.
      * Execute queued actions using `gmail_integration.py` (respecting `--dry-run`).
      * Provide clear feedback on actions taken.
      * Consider batching and API rate limits.

* **A3.4 (Optional Stretch Goal for Phase 3): Direct LLM Analysis within Damien (`damien analyze`)**
  * **Goal:** Allow Damien to directly use an LLM for tasks like spam classification, sentiment analysis, or summarization on specified emails.
  * **Key Tasks:**
    * Implement `llm_interface.py` to securely manage API keys and make calls to LLM providers.
    * Create a `damien analyze [--llm <provider>]` command.
    * Process and display LLM analysis results.

## Future Phases & Ideas (Beyond Phase 3)

* **Phase 4: Polish, Packaging & Distribution**
  * Advanced error handling and user feedback.
  * Comprehensive end-user documentation review.
  * Packaging for PyPI for easier installation (`pip install damien-cli`).
  * Potential for executable creation (e.g., using PyInstaller).
* **Advanced Rule Conditions:**
  * Date-based conditions (e.g., "older than 90 days").
  * Attachment-based conditions (name, type, size).
  * Regular expression matching.
* **User Interface:**
  * Explore a Terminal User Interface (TUI) using libraries like `Textual`.
  * Potential for a web GUI in the distant future if demand exists.
* **Performance Optimizations:** For extremely large mailboxes or complex rule sets.
* **Support for Other Email Providers:** (Major undertaking).
* **Real-time/Scheduled Processing:** Running Damien automatically in the background.
* **More Sophisticated LLM Integrations:**
  * Dynamic rule generation by an LLM based on email examples.
  * LLM-powered email summarization.
  * Automated email drafting/reply suggestions.

This roadmap will be updated as the project progresses.
