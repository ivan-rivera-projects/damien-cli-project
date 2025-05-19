import click
import json
import sys
from typing import Optional
from pydantic import ValidationError

# Updated import to use the new API service layer
from damien_cli.core_api import rules_api_service
from damien_cli.core_api.exceptions import (
    RuleNotFoundError,
    RuleStorageError,
    InvalidParameterError,
)

# Models are still used for creating new rules from JSON, if that's how add_rule_cmd works
from .models import RuleModel  # Assuming models.py is still in features/rule_management


@click.group("rules")
@click.pass_context
def rules_group(ctx):
    """Manage filtering rules for Damien."""
    logger = ctx.obj.get("logger")
    # No specific setup needed here for now, as API calls don't need a 'gmail_service' object passed
    # unlike email commands. If rule application needed it, that would be handled in 'apply' cmd.
    if logger:
        logger.debug("Rules command group invoked.")


@rules_group.command("list")
@click.option(
    "--output-format",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
)
@click.pass_context
def list_rules_cmd(ctx, output_format):
    """Lists all configured rules."""
    logger = ctx.obj.get("logger")
    if logger:
        logger.info("Executing 'rules list'")

    try:
        rules = rules_api_service.load_rules()
    except RuleStorageError as e:
        click.secho(f"Error loading rules: {e}", fg="red")
        if logger:
            logger.error(f"Rule storage error during list: {e}", exc_info=True)
        if output_format == "json":
            sys.stdout.write(
                json.dumps(
                    {
                        "status": "error",
                        "command_executed": "damien rules list",
                        "message": str(e),
                        "data": None,
                        "error_details": {
                            "code": "RULE_STORAGE_ERROR",
                            "details": str(
                                e.original_exception
                                if hasattr(e, "original_exception")
                                else e
                            ),
                        },
                    },
                    indent=2,
                )
                + "\n"
            )
        ctx.exit(1)
        return
    if not rules:
        if output_format == "json":
            # Standard JSON response for success but no data
            response_obj = {
                "status": "success",
                "command_executed": "damien rules list",
                "message": "No rules configured yet.",
                "data": [],
                "error_details": None,
            }
            sys.stdout.write(json.dumps(response_obj, indent=2) + "\n")
        else:
            click.echo("No rules configured yet.")
        return

    if output_format == "json":
        rules_data = [rule.model_dump(mode="json") for rule in rules]
        response_obj = {
            "status": "success",
            "command_executed": "damien rules list",
            "message": f"Successfully listed {len(rules_data)} rules.",
            "data": rules_data,
            "error_details": None,
        }
        sys.stdout.write(json.dumps(response_obj, indent=2) + "\n")
    else:  # human format
        click.echo("Configured Rules:")
        for i, rule in enumerate(rules):
            click.echo(
                f"\n--- Rule {i+1} ({'Enabled' if rule.is_enabled else 'Disabled'}) ---"
            )
            click.echo(f" ID: {rule.id}")
            click.echo(f" Name: {rule.name}")
            if rule.description:
                click.echo(f" Description: {rule.description}")
            click.echo(f" Condition Logic: {rule.condition_conjunction}")
            click.echo(" Conditions:") # Removed f-string
            for cond in rule.conditions:
                click.echo(
                    f" - Field: {cond.field}, Operator: {cond.operator}, Value: '{cond.value}'"
                )
            click.echo(" Actions:") # Removed f-string
            for action in rule.actions:
                click.echo(
                    f" - Type: {action.type}"
                    + (f", Label: {action.label_name}" if action.label_name else "")
                )
    if logger:
        logger.info(f"Listed {len(rules)} rules.")


@rules_group.command("add")
@click.option(
    "--rule-json", help="Rule definition as a JSON string or path to a JSON file."
)
@click.option(
    "--output-format",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
    help="Output format for success/error messages.",
)  # Added for consistency
@click.pass_context
def add_rule_cmd(ctx, rule_json, output_format):
    """Adds a new rule from a JSON definition."""
    logger = ctx.obj.get("logger")
    cmd_name = "damien rules add"

    def _output_error(message: str, code: str, details: Optional[str] = None):
        if output_format == "json":
            err_obj = {
                "status": "error",
                "command_executed": cmd_name,
                "message": message,
                "data": None,
                "error_details": {"code": code, "details": details or message},
            }
            sys.stdout.write(json.dumps(err_obj, indent=2) + "\n")
        else:
            click.secho(message, fg="red")
        ctx.exit(1)

    if not rule_json:
        msg = "Error: --rule-json option is required to define the rule."
        if output_format == "human":
            click.echo(msg)
            example_structure = {
                "name": "Sample Rule Name",
                "description": "Optional description",
                "is_enabled": True,
                "conditions": [
                    {
                        "field": "from",
                        "operator": "contains",
                        "value": "newsletter@example.com",
                    }
                ],
                "condition_conjunction": "AND",
                "actions": [{"type": "trash"}],
            }
            click.echo("\nExample JSON structure for a rule:")
            click.echo(json.dumps(example_structure, indent=2))
        else:  # JSON output
            _output_error(msg, "MISSING_PARAMETER", "--rule-json is required.")
        ctx.exit(1)  # Exit after printing help or JSON error
    try:
        rule_data_dict = json.loads(rule_json)
    except json.JSONDecodeError:
        try:
            with open(rule_json, "r") as f:
                rule_data_dict = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            msg = f"Error: Could not parse --rule-json. Not valid JSON or readable file: {e}"
            if logger:
                logger.error(f"Failed to parse rule_json: {e}", exc_info=True)
            _output_error(msg, "INVALID_INPUT_JSON", str(e))
            # ctx.exit(1) is handled by _output_error

    try:
        new_rule_model = RuleModel(**rule_data_dict)
        if logger:
            logger.info(f"Attempting to add rule: {new_rule_model.name}")

        added_rule = rules_api_service.add_rule(
            new_rule_model
        )  # API now returns the added rule or raises

        msg = f"Rule '{added_rule.name}' (ID: {added_rule.id}) added successfully."
        if output_format == "json":
            response_obj = {
                "status": "success",
                "command_executed": cmd_name,
                "message": msg,
                "data": added_rule.model_dump(mode="json"),
                "error_details": None,
            }
            sys.stdout.write(json.dumps(response_obj, indent=2) + "\n")
        else:
            click.echo(msg)
        if logger:
            logger.info(f"Rule '{added_rule.name}' added.")
    except ValidationError as e:
        msg = "Error: Rule data is invalid according to the expected schema."
        details_str = (
            json.dumps(e.errors(), indent=2) if hasattr(e, "errors") else str(e)
        )
        if logger:
            logger.error(f"Rule validation failed: {details_str}")
        if output_format == "human":
            click.secho(msg, fg="red")
            click.echo(f"Validation details:\n{details_str}")
        _output_error(msg, "VALIDATION_ERROR", details_str)
    except (RuleStorageError, InvalidParameterError) as e:
        msg = f"Error adding rule: {e}"
        if logger:
            logger.error(msg, exc_info=True)
        _output_error(
            msg,
            e.__class__.__name__.upper(),
            str(e.original_exception if hasattr(e, "original_exception") else e),
        )
    except Exception as e:  # Catch-all for other unexpected errors
        msg = f"An unexpected error occurred while adding the rule: {e}"
        if logger:
            logger.error(msg, exc_info=True)
        _output_error(msg, "UNEXPECTED_ERROR", str(e))


@rules_group.command("delete")
@click.option(
    "--id", "rule_identifier", required=True, help="ID or Name of the rule to delete."
)
@click.option(
    "--output-format",
    type=click.Choice(["human", "json"]),
    default="human",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def delete_rule_cmd(ctx, rule_identifier, output_format):
    """Deletes a rule by its ID or Name."""
    logger = ctx.obj.get("logger")
    cmd_name = "damien rules delete"

    def _output_error(
        message: str, code: str, details: Optional[str] = None
    ):  # Local helper for this command
        if output_format == "json":
            err_obj = {
                "status": "error",
                "command_executed": cmd_name,
                "message": message,
                "data": None,
                "error_details": {"code": code, "details": details or message},
            }
            sys.stdout.write(json.dumps(err_obj, indent=2) + "\n")
        else:
            click.secho(message, fg="red")
        ctx.exit(1)

    if logger:
        logger.info(f"Attempting to delete rule: {rule_identifier}")
    if not click.confirm(
        f"Are you sure you want to delete the rule '{rule_identifier}'?",
        default=False,
        abort=False,
    ):
        msg = "Rule deletion aborted by user."
        if output_format == "json":
            # For user abort, status is "success" or "aborted" but not an error from the app's perspective
            response_obj = {
                "status": "aborted_by_user",
                "command_executed": cmd_name,
                "message": msg,
                "data": None,
                "error_details": None,
            }
            sys.stdout.write(json.dumps(response_obj, indent=2) + "\n")
        else:
            click.echo(msg)
        if logger:
            logger.info("User aborted rule deletion.")
        return
    try:
        rules_api_service.delete_rule(rule_identifier)  # Returns True or raises
        msg = f"Rule '{rule_identifier}' deleted successfully."
        if output_format == "json":
            response_obj = {
                "status": "success",
                "command_executed": cmd_name,
                "message": msg,
                "data": {"deleted_identifier": rule_identifier},
                "error_details": None,
            }
            sys.stdout.write(json.dumps(response_obj, indent=2) + "\n")
        else:
            click.echo(msg)
        if logger:
            logger.info(f"Rule '{rule_identifier}' deleted.")
    except RuleNotFoundError as e:
        msg = str(e)  # API service already provides a good message
        if logger:
            logger.warning(msg)  # It's a warning if not found
        if output_format == "json":
            # Technically, command was valid but resource not found. Could be error or specific success.
            # Let's call it an error for the CLI user trying to delete something specific.
            _output_error(msg, "RULE_NOT_FOUND", str(e))
        else:
            click.secho(msg, fg="yellow")  # Yellow for not found
    except RuleStorageError as e:
        msg = f"Error deleting rule: {e}"
        if logger:
            logger.error(msg, exc_info=True)
        _output_error(
            msg,
            "RULE_STORAGE_ERROR",
            str(e.original_exception if hasattr(e, "original_exception") else e),
        )
    except Exception as e:  # Catch-all
        msg = f"An unexpected error occurred: {e}"
        if logger:
            logger.error(msg, exc_info=True)
        _output_error(msg, "UNEXPECTED_ERROR", str(e))
