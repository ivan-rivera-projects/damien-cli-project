import click
import json
import sys # For sys.stdout.write
from pydantic import ValidationError # For catching Pydantic errors

from . import rule_storage # To use load_rules, add_rule, etc.
from .models import RuleModel, ConditionModel, ActionModel # Pydantic models

@click.group("rules")
@click.pass_context
def rules_group(ctx):
    """Manage filtering rules for Damien."""
    # logger = ctx.obj.get('logger') # Get logger if needed
    pass # No common setup needed for now

@rules_group.command("list")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True)
@click.pass_context
def list_rules_cmd(ctx, output_format):
    """Lists all configured rules."""
    logger = ctx.obj.get('logger')
    if logger: logger.info("Executing 'rules list'")
    
    rules = rule_storage.load_rules()
    
    if output_format == 'json':
        if not rules:
            output_obj = {
                "status": "success",
                "command_executed": "damien rules list",
                "parameters_provided": {},
                "message": "No rules configured yet.",
                "data": [],
                "error_details": None
            }
        else:
            rules_json = [rule.model_dump(mode='json') for rule in rules]
            output_obj = {
                "status": "success",
                "command_executed": "damien rules list",
                "parameters_provided": {},
                "message": f"Successfully listed {len(rules)} rule(s).",
                "data": rules_json,
                "error_details": None
            }
        sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
    else: # human format
        if not rules:
            click.echo("No rules configured yet.")
        else:
            click.echo("Configured Rules:")
            for i, rule in enumerate(rules):
                click.echo(f"\n--- Rule {i+1} ({'Enabled' if rule.is_enabled else 'Disabled'}) ---")
                click.echo(f"  ID: {rule.id}")
                click.echo(f"  Name: {rule.name}")
                if rule.description:
                    click.echo(f"  Description: {rule.description}")
                click.echo(f"  Condition Logic: {rule.condition_conjunction}")
                click.echo(f"  Conditions:")
                for cond in rule.conditions:
                    click.echo(f"    - Field: {cond.field}, Operator: {cond.operator}, Value: '{cond.value}'")
                click.echo(f"  Actions:")
                for action in rule.actions:
                    click.echo(f"    - Type: {action.type}" + (f", Label: {action.label_name}" if action.label_name else ""))
    if logger: logger.info(f"Listed {len(rules)} rules.")


@rules_group.command("add")
@click.option('--rule-json', help="Rule definition as a JSON string or path to a JSON file.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True)
@click.pass_context
def add_rule_cmd(ctx, rule_json, output_format):
    """Adds a new rule from a JSON definition."""
    logger = ctx.obj.get('logger')
    if not rule_json:
        if output_format == 'json':
            example_structure = {
                "name": "Sample Rule Name", "description": "Optional description", "is_enabled": True,
                "conditions": [{"field": "from", "operator": "contains", "value": "newsletter@example.com"}],
                "condition_conjunction": "AND", "actions": [{"type": "trash"}]
            }
            output_obj = {
                "status": "error",
                "command_executed": "damien rules add",
                "parameters_provided": {"rule_json": None},
                "message": "Error: --rule-json option is required to define the rule.",
                "data": {"example_structure": example_structure},
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "--rule-json option is required to define the rule."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("Error: --rule-json option is required to define the rule.")
            example_structure = {
                "name": "Sample Rule Name", "description": "Optional description", "is_enabled": True,
                "conditions": [{"field": "from", "operator": "contains", "value": "newsletter@example.com"}],
                "condition_conjunction": "AND", "actions": [{"type": "trash"}]
            }
            click.echo("\nExample JSON structure for a rule:")
            click.echo(json.dumps(example_structure, indent=2))
        ctx.exit(1)

    try:
        rule_data = json.loads(rule_json)
    except json.JSONDecodeError:
        try:
            with open(rule_json, 'r') as f:
                rule_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            err_msg = f"Error: Could not parse --rule-json. It's not valid JSON nor a readable JSON file: {e}"
            if output_format == 'json':
                output_obj = {
                    "status": "error",
                    "command_executed": "damien rules add",
                    "parameters_provided": {"rule_json": rule_json},
                    "message": err_msg,
                    "data": None,
                    "error_details": {
                        "code": "INVALID_INPUT_JSON",
                        "details": str(e)
                    }
                }
                sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            else:
                click.echo(err_msg)
            if logger: logger.error(f"Failed to parse rule_json: {e}", exc_info=True)
            ctx.exit(1)
    
    try:
        new_rule = RuleModel(**rule_data)
        if logger: logger.info(f"Attempting to add rule: {new_rule.name}")
        
        if rule_storage.add_rule(new_rule):
            if output_format == 'json':
                output_obj = {
                    "status": "success",
                    "command_executed": "damien rules add",
                    "parameters_provided": {"rule_json": "..."},
                    "message": f"Rule '{new_rule.name}' (ID: {new_rule.id}) added successfully.",
                    "data": {
                        "rule_id": new_rule.id,
                        "name": new_rule.name,
                        "rule": new_rule.model_dump(mode='json')
                    },
                    "error_details": None
                }
                sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            else:
                click.echo(f"Rule '{new_rule.name}' (ID: {new_rule.id}) added successfully.")
            if logger: logger.info(f"Rule '{new_rule.name}' added.")
        else:
            err_msg = f"Failed to add rule '{new_rule.name}'. It might already exist or there was a save error."
            if output_format == 'json':
                output_obj = {
                    "status": "error",
                    "command_executed": "damien rules add",
                    "parameters_provided": {"rule_json": "..."},
                    "message": err_msg,
                    "data": None,
                    "error_details": {
                        "code": "STORAGE_ERROR",
                        "details": "Rule might already exist or there was a problem saving to storage."
                    }
                }
                sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            else:
                click.echo(err_msg)
            if logger: logger.error(f"Failed to add rule '{new_rule.name}' (storage reported failure).")
            # Consider if this case should also ctx.exit(1) if storage failure is an error
    except ValidationError as e:
        if output_format == 'json':
            # For Pydantic V2, e.errors() gives a list of dicts
            try:
                validation_details = e.errors()
            except (TypeError, AttributeError):
                validation_details = str(e)
                
            output_obj = {
                "status": "error",
                "command_executed": "damien rules add",
                "parameters_provided": {"rule_json": "..."},
                "message": "Error: Rule data is invalid according to the expected schema.",
                "data": None,
                "error_details": {
                    "code": "VALIDATION_ERROR",
                    "details": validation_details
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("Error: Rule data is invalid according to the expected schema.")
            # For Pydantic V2, e.errors() gives a list of dicts. For V1 it was e.json()
            try:
                click.echo(f"Validation details:\n{json.dumps(e.errors(), indent=2)}")
            except TypeError: # If e.errors() is not directly serializable (less common for Pydantic)
                click.echo(f"Validation details:\n{str(e.errors())}")
        if logger: logger.error(f"Rule validation failed: {json.dumps(e.errors()) if hasattr(e, 'errors') else str(e)}")
        ctx.exit(1)
    except Exception as e:
        err_msg = f"An unexpected error occurred while adding the rule: {e}"
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien rules add",
                "parameters_provided": {"rule_json": "..."},
                "message": err_msg,
                "data": None,
                "error_details": {
                    "code": "UNEXPECTED_ERROR",
                    "details": str(e)
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo(err_msg)
        if logger: logger.error(f"Unexpected error adding rule: {e}", exc_info=True)
        ctx.exit(1)


@rules_group.command("delete")
@click.option('--id', 'rule_identifier', required=True, help="ID or Name of the rule to delete.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True)
@click.pass_context
def delete_rule_cmd(ctx, rule_identifier, output_format):
    """Deletes a rule by its ID or Name."""
    logger = ctx.obj.get('logger')
    if logger: logger.info(f"Attempting to delete rule: {rule_identifier}")

    if output_format == 'json':
        if not click.confirm(f"Are you sure you want to delete the rule '{rule_identifier}'?", default=False, abort=False):
            output_obj = {
                "status": "success",
                "command_executed": "damien rules delete",
                "parameters_provided": {"rule_identifier": rule_identifier},
                "message": "Rule deletion aborted by user.",
                "data": {"deleted_identifier": None, "action_taken": False},
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("User aborted rule deletion.")
            return
        
        if rule_storage.delete_rule(rule_identifier):
            output_obj = {
                "status": "success",
                "command_executed": "damien rules delete",
                "parameters_provided": {"rule_identifier": rule_identifier},
                "message": f"Rule '{rule_identifier}' deleted successfully.",
                "data": {"deleted_identifier": rule_identifier, "action_taken": True},
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info(f"Rule '{rule_identifier}' deleted.")
        else:
            output_obj = {
                "status": "error",
                "command_executed": "damien rules delete",
                "parameters_provided": {"rule_identifier": rule_identifier},
                "message": f"Failed to delete rule '{rule_identifier}'. See previous messages or logs.",
                "data": None,
                "error_details": {
                    "code": "RULE_NOT_FOUND_OR_STORAGE_ERROR",
                    "details": f"Rule '{rule_identifier}' might not exist or there was a problem deleting from storage."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.error(f"Failed to delete rule '{rule_identifier}' (storage reported failure).")
    else: # human format
        if not click.confirm(f"Are you sure you want to delete the rule '{rule_identifier}'?", default=False, abort=False):
            click.echo("Rule deletion aborted by user.")
            if logger: logger.info("User aborted rule deletion.")
            return

        if rule_storage.delete_rule(rule_identifier):
            click.echo(f"Rule '{rule_identifier}' deleted successfully.")
            if logger: logger.info(f"Rule '{rule_identifier}' deleted.")
        else:
            click.echo(f"Failed to delete rule '{rule_identifier}'. See previous messages or logs.")
            if logger: logger.error(f"Failed to delete rule '{rule_identifier}' (storage reported failure).")
            # Consider if this case should ctx.exit(1) if it's considered a command failure