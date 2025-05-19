# damien_cli/core_api/rules_api_service.py
import json
import logging
from typing import List, Dict, Any # Removed Optional
from pathlib import Path  # For consistency with gmail_api_service
from pydantic import ValidationError  # Keep this import
from damien_cli.core import config as app_config

# Assuming models stay in features for now, adjust if you move them to core_api/models.py
from damien_cli.features.rule_management.models import RuleModel, ConditionModel
from .exceptions import ( # Removed DamienError from this specific file's direct imports if not used
    RuleNotFoundError,
    RuleStorageError,
    InvalidParameterError,
)

logger = logging.getLogger(__name__)
RULES_FILE_PATH = Path(app_config.RULES_FILE)  # Ensure RULES_FILE is defined in config


# --- Rule Storage (CRUD) ---
def load_rules() -> List[RuleModel]:
    """Loads rules from the JSON rules file. Raises RuleStorageError on issues."""
    if not RULES_FILE_PATH.exists():
        logger.info(f"Rules file not found at {RULES_FILE_PATH}. Returning empty list.")
        return []
    try:
        with open(RULES_FILE_PATH, "r") as f:
            rules_data_from_file = json.load(f)

        valid_rules: List[RuleModel] = []
        invalid_rule_count = 0
        for i, rule_dict in enumerate(rules_data_from_file):
            try:
                valid_rules.append(RuleModel(**rule_dict))
            except ValidationError as e:
                invalid_rule_count += 1
                logger.warning(
                    f"Skipping invalid rule #{i+1} due to validation error: {e.errors()} in rule data: {rule_dict}"
                )

        if invalid_rule_count > 0:
            logger.warning(
                f"Loaded {len(valid_rules)} valid rules and skipped {invalid_rule_count} invalid rules."
            )
        else:
            logger.info(
                f"Successfully loaded {len(valid_rules)} rules from {RULES_FILE_PATH}."
            )
        return valid_rules

    except json.JSONDecodeError as e:
        logger.error(
            f"Error decoding JSON from rules file {RULES_FILE_PATH}: {e}", exc_info=True
        )
        raise RuleStorageError(
            f"Invalid JSON in rules file: {RULES_FILE_PATH}", original_exception=e
        )
    except IOError as e:
        logger.error(
            f"IOError reading rules file {RULES_FILE_PATH}: {e}", exc_info=True
        )
        raise RuleStorageError(
            f"Could not read rules file: {RULES_FILE_PATH}", original_exception=e
        )
    except Exception as e:  # Catch any other unexpected error during loading/validation
        logger.error(f"Unexpected error loading rules: {e}", exc_info=True)
        raise RuleStorageError(
            f"An unexpected error occurred while loading rules: {e}",
            original_exception=e,
        )


def save_rules(rules: List[RuleModel]) -> None:
    """Saves the list of rules to the JSON rules file. Raises RuleStorageError on issues."""
    try:
        logger.debug(f"Attempting to save {len(rules)} rules to {RULES_FILE_PATH}.")
        # Ensure parent directory exists
        RULES_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        rules_data_to_save = [rule.model_dump(mode="json") for rule in rules]

        with open(RULES_FILE_PATH, "w") as f:
            json.dump(rules_data_to_save, f, indent=2)
        logger.info(f"Successfully saved {len(rules)} rules to {RULES_FILE_PATH}.")
    except IOError as e:
        logger.error(f"IOError saving rules file {RULES_FILE_PATH}: {e}", exc_info=True)
        raise RuleStorageError(
            f"Could not write to rules file: {RULES_FILE_PATH}", original_exception=e
        )
    except (
        Exception
    ) as e:  # Catch other potential errors like Pydantic model issues if not properly handled before
        logger.error(
            f"An unexpected error occurred while saving rules: {e}", exc_info=True
        )
        raise RuleStorageError(
            f"An unexpected error occurred while saving rules: {e}",
            original_exception=e,
        )


def add_rule(new_rule_model: RuleModel) -> RuleModel:
    """Adds a new rule and saves. Raises RuleStorageError or InvalidParameterError."""
    if not isinstance(new_rule_model, RuleModel):
        raise InvalidParameterError("Invalid rule object provided to add_rule.")

    rules = load_rules()  # load_rules can raise RuleStorageError
    # Optional: Check for duplicate rule names (IDs are unique by factory)
    for existing_rule in rules:
        if existing_rule.name.lower() == new_rule_model.name.lower():
            err_msg = f"A rule with the name '{new_rule_model.name}' already exists (ID: {existing_rule.id})."
            logger.warning(err_msg)
            raise InvalidParameterError(err_msg)  # Or a specific DuplicateRuleError
    rules.append(new_rule_model)
    save_rules(rules)  # save_rules can raise RuleStorageError
    logger.info(f"Rule '{new_rule_model.name}' (ID: {new_rule_model.id}) added.")
    return new_rule_model


def delete_rule(rule_id_or_name: str) -> bool:
    """Deletes a rule by its ID or name. Raises RuleNotFoundError or RuleStorageError."""
    if not rule_id_or_name:
        raise InvalidParameterError("Rule ID or name must be provided for deletion.")
    rules = load_rules()
    # initial_len = len(rules) # Removed unused variable

    rule_to_delete = None
    for rule in rules:
        if rule.id == rule_id_or_name or rule.name.lower() == rule_id_or_name.lower():
            rule_to_delete = rule
            break

    if not rule_to_delete:
        logger.warning(
            f"Rule with ID or name '{rule_id_or_name}' not found for deletion."
        )
        raise RuleNotFoundError(f"Rule '{rule_id_or_name}' not found.")

    rules.remove(rule_to_delete)  # Remove the found rule object
    save_rules(rules)  # save_rules can raise RuleStorageError
    logger.info(f"Rule '{rule_to_delete.name}' (ID: {rule_to_delete.id}) deleted.")
    return True  # Indicates deletion attempt was processed (save_rules would raise if failed)


# --- Rule Matching Logic (from features/rule_management/service.py) ---
def _email_field_matches_condition(
    email_data: Dict[str, Any], condition: ConditionModel
) -> bool:
    """Checks if a single email field matches a single condition.
    Helper function for internal use.
    """
    # Ensure field value is a string for string operations; handle list for 'label'
    field_name = condition.field
    condition_val = condition.value.lower()
    if field_name == "label":  # Special handling for labels (list of strings)
        email_field_value_list = email_data.get(field_name, [])
        if not isinstance(email_field_value_list, list):
            logger.warning(
                f"Expected list for email field '{field_name}', got {type(email_field_value_list)}. Treating as no match."
            )
            return False

        # For 'label', 'contains' means the label is present in the list
        # 'equals' could mean the list of labels is exactly this one label (less common)
        # Adjust logic based on desired behavior for label matching
        if condition.operator == "contains":
            return any(
                condition_val == label.lower() for label in email_field_value_list
            )
        elif condition.operator == "not_contains":
            return all(
                condition_val != label.lower() for label in email_field_value_list
            )
        else:
            logger.warning(
                f"Operator '{condition.operator}' not fully supported for 'label' field in this basic matcher. Treating as no match."
            )
            return False  # Or implement other operators for lists
    else:  # For other fields, assume string comparison
        email_field_value_str = str(
            email_data.get(field_name, "")
        ).lower()  # Convert to str just in case

        if condition.operator == "contains":
            return condition_val in email_field_value_str
        elif condition.operator == "not_contains":
            return condition_val not in email_field_value_str
        elif condition.operator == "equals":
            return condition_val == email_field_value_str
        elif condition.operator == "not_equals":
            return condition_val != email_field_value_str
        elif condition.operator == "starts_with":
            return email_field_value_str.startswith(condition_val)
        elif condition.operator == "ends_with":
            return email_field_value_str.endswith(condition_val)

        logger.warning(
            f"Unknown operator '{condition.operator}' for field '{field_name}'."
        )
        return False


def does_email_match_rule(email_data: Dict[str, Any], rule: RuleModel) -> bool:
    """
    Checks if the given email data matches a rule based on its conditions and conjunction.
    Assumes email_data keys correspond to ConditionModel.field values.
    """
    if not isinstance(email_data, dict):
        logger.error("email_data must be a dictionary for rule matching.")
        return False  # Or raise InvalidParameterError
    if not isinstance(rule, RuleModel):
        logger.error("rule must be a RuleModel instance for rule matching.")
        return False  # Or raise InvalidParameterError
    if not rule.is_enabled:
        logger.debug(f"Rule '{rule.name}' is disabled, skipping match.")
        return False
    if not rule.conditions:
        logger.debug(
            f"Rule '{rule.name}' has no conditions, evaluating as non-match by default."
        )
        return False
    condition_matches: List[bool] = []
    for cond in rule.conditions:
        match = _email_field_matches_condition(email_data, cond)
        condition_matches.append(match)
        logger.debug(
            f"Rule '{rule.name}', Condition '{cond.field} {cond.operator} {cond.value}', Email Value '{email_data.get(cond.field)}', Match: {match}"
        )
    if not condition_matches:  # Should not happen if rule.conditions is not empty
        return False
    final_match = False
    if rule.condition_conjunction == "AND":
        final_match = all(condition_matches)
    elif rule.condition_conjunction == "OR":
        final_match = any(condition_matches)

    logger.debug(
        f"Rule '{rule.name}' overall match for email: {final_match} (Conjunction: {rule.condition_conjunction}, Individual matches: {condition_matches})"
    )
    return final_match
