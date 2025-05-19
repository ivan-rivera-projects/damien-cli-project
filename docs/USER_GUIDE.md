# Damien-CLI User Guide

This guide provides instructions on how to use the Damien-CLI application.

## Installation & Setup

Please refer to the main `README.md` for installation and initial setup instructions, including Gmail API authentication.

## General Usage

All commands start with `poetry run damien`. You can get help for any command or subcommand by appending `--help`.

```bash
poetry run damien --help
poetry run damien emails --help
poetry run damien rules --help
```

## Global Options

* `--verbose` / `-v`: Enable verbose (DEBUG level) logging. Output will be more detailed, both to console and the log file.
* `--output-format json`: Many commands support this to output results in JSON format for programmatic use.

## Commands

### login

Authenticates Damien with your Gmail account. This will typically open a web browser for authorization.

```bash
poetry run damien login
```

### hello

A simple command to check if Damien is responsive.

```bash
poetry run damien hello
```

### emails

Group of commands for managing emails.

#### emails list

Lists emails from your Gmail account.

* `--query <TEXT>` or `-q <TEXT>`: Gmail search query (e.g., "is:unread", "from:boss@example.com subject:report").
* `--max-results <NUMBER>` or `-m <NUMBER>`: Maximum number of emails to retrieve (default: 10).
* `--page-token <TEXT>` or `-p <TEXT>`: Token for fetching the next page of results.
* `--output-format [human|json]`: Output format.

Example:
```bash
poetry run damien emails list --query "is:starred" --max-results 5
poetry run damien emails list --output-format json
```

#### emails get

Retrieves and displays details of a specific email.

* `--id <EMAIL_ID>`: The ID of the email (required).
* `--format [metadata|full|raw]`: The level of detail to retrieve (default: 'full').
* `--output-format [human|json]`: Output format.

Example:
```bash
poetry run damien emails get --id 196abc123def --format metadata
```

#### emails trash

Moves specified emails to the Trash folder.

* `--ids <ID1,ID2,...>`: Comma-separated list of email IDs (required).
* `--dry-run`: Show what would be done without making changes.

Example:
```bash
poetry run damien emails trash --ids 196abc123,197def456 --dry-run
poetry run damien emails trash --ids 198xyz789 # Will ask for confirmation
```

#### emails delete

PERMANENTLY deletes specified emails. This action is irreversible.

* `--ids <ID1,ID2,...>`: Comma-separated list of email IDs (required).
* `--dry-run`: Show what would be done without making changes.

Example:
```bash
poetry run damien emails delete --ids 196abc123 --dry-run
# poetry run damien emails delete --ids 198xyz789 # Will require multiple confirmations
```

#### emails label

Adds or removes labels from specified emails.

* `--ids <ID1,ID2,...>`: Comma-separated list of email IDs (required).
* `--add-labels <LABEL_NAME1,LABEL_NAME2,...>`: Labels to add.
* `--remove-labels <LABEL_NAME1,LABEL_NAME2,...>`: Labels to remove.
* `--dry-run`: Show what would be done without making changes.

Example:
```bash
poetry run damien emails label --ids 196abc --add-labels MyLabel,Important
poetry run damien emails label --ids 197def --remove-labels OldLabel --dry-run
```

#### emails mark

Marks specified emails as read or unread.

* `--ids <ID1,ID2,...>`: Comma-separated list of email IDs (required).
* `--action [read|unread]`: Action to perform (required).
* `--dry-run`: Show what would be done without making changes.

Example:
```bash
poetry run damien emails mark --ids 196abc,197def --action read
poetry run damien emails mark --ids 198xyz --action unread --dry-run
```

### rules

Group of commands for managing filtering rules.

#### rules list

Lists all configured filtering rules.

* `--output-format [human|json]`: Output format.

Example:
```bash
poetry run damien rules list
poetry run damien rules list --output-format json
```

#### rules add

Adds a new filtering rule. Rule definition must be provided as a JSON string or a path to a JSON file.

* `--rule-json <JSON_STRING_OR_FILEPATH>`: The rule definition (required).

Example JSON structure:
```json
{
  "name": "Trash Old Promos",
  "description": "Moves promotional emails older than 90 days to trash",
  "is_enabled": true,
  "conditions": [
    {"field": "from", "operator": "contains", "value": "promo@example.com"},
    {"field": "label", "operator": "contains", "value": "CATEGORY_PROMOTIONS"}
    // "age_days_gt": 90 (Age condition not yet implemented in matching logic)
  ],
  "condition_conjunction": "AND",
  "actions": [
    {"type": "trash"}
  ]
}
```

Example usage (assuming my_rule.json contains the above):
```bash
poetry run damien rules add --rule-json my_rule.json
poetry run damien rules add --rule-json '{"name": "Quick Rule", "conditions": [...], "actions": [{"type": "mark_read"}]}'
```

#### rules delete

Deletes a rule by its ID or Name.

* `--id <RULE_ID_OR_NAME>`: The ID or name of the rule to delete (required).

Example:
```bash
poetry run damien rules delete --id "Trash Old Promos" # Will ask for confirmation
poetry run damien rules delete --id "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" # Using rule ID
```

(Note: Rule application `damien rules apply` is a planned feature.)
