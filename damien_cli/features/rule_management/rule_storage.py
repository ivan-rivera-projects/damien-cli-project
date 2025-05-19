import json
from typing import List, Optional
from pathlib import Path
from pydantic import ValidationError

from damien_cli.core import config as app_config # To get RULES_FILE path
from .models import RuleModel # Your Pydantic RuleModel

RULES_FILE_PATH = app_config.RULES_FILE

def load_rules() -> List[RuleModel]:
    """Loads rules from the JSON rules file."""
    if not RULES_FILE_PATH.exists():
        return []
    try:
        with open(RULES_FILE_PATH, 'r') as f:
            rules_data = json.load(f)
        # Validate each rule data against Pydantic model
        valid_rules = []
        for rule_dict in rules_data:
            try:
                valid_rules.append(RuleModel(**rule_dict))
            except ValidationError as e:
                # Handle or log invalid rule structure
                print(f"Warning: Skipping invalid rule due to validation error: {e.errors()} in rule data: {rule_dict}") # Use click.echo or logger
        return valid_rules
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading rules file {RULES_FILE_PATH}: {e}") # Use click.echo or logger
        return [] # Return empty list on error

def save_rules(rules: List[RuleModel]) -> bool:
    """Saves the list of rules to the JSON rules file."""
    try:
        # Convert Pydantic models to dicts for JSON serialization
        rules_data_to_save = [rule.model_dump(mode='json') for rule in rules] # Pydantic v2
        # For Pydantic v1: rules_data_to_save = [rule.dict() for rule in rules]
        
        with open(RULES_FILE_PATH, 'w') as f:
            json.dump(rules_data_to_save, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving rules file {RULES_FILE_PATH}: {e}") # Use click.echo or logger
        return False
    except Exception as e: # Catch other potential errors like Pydantic model issues if not properly handled before
        print(f"An unexpected error occurred while saving rules: {e}")
        return False

def add_rule(new_rule: RuleModel) -> bool:
    """Adds a new rule and saves the updated list."""
    rules = load_rules()
    # Check for duplicate rule names or IDs if desired (optional)
    # for rule in rules:
    #     if rule.name == new_rule.name:
    #         print(f"Error: A rule with the name '{new_rule.name}' already exists.")
    #         return False
    rules.append(new_rule)
    return save_rules(rules)

def delete_rule(rule_id_or_name: str) -> bool:
    """Deletes a rule by its ID or name and saves the updated list."""
    rules = load_rules()
    initial_len = len(rules)
    # Filter out the rule to be deleted
    rules_after_delete = [rule for rule in rules if rule.id != rule_id_or_name and rule.name != rule_id_or_name]
    
    if len(rules_after_delete) == initial_len:
        print(f"Rule with ID or name '{rule_id_or_name}' not found.")
        return False # Rule not found
        
    return save_rules(rules_after_delete)