from typing import Dict, Any
from .models import RuleModel, ConditionModel

def email_field_matches_condition(email_data: Dict[str, Any], condition: ConditionModel) -> bool:
    """Checks if a single email field matches a single condition."""
    field_value = email_data.get(condition.field, "").lower() # Get field, default to empty string, lowercase for case-insensitive
    condition_val = condition.value.lower()

    if condition.operator == "contains":
        return condition_val in field_value
    elif condition.operator == "not_contains":
        return condition_val not in field_value
    elif condition.operator == "equals":
        return condition_val == field_value
    elif condition.operator == "not_equals":
        return condition_val != field_value
    elif condition.operator == "starts_with":
        return field_value.startswith(condition_val)
    elif condition.operator == "ends_with":
        return field_value.endswith(condition_val)
    # Add more operators as needed
    return False

def does_email_match_rule(email_data: Dict[str, Any], rule: RuleModel) -> bool:
    """
    Checks if the given email data matches all conditions of a rule
    based on the rule's conjunction (AND/OR).
    
    Args:
        email_data: A dictionary representing the email (e.g., {'from': '...', 'subject': '...'}).
                    This should be a simplified version for matching, not the full Gmail API object.
        rule: The RuleModel object to check against.
    """
    if not rule.is_enabled:
        return False
    if not rule.conditions: # A rule with no conditions matches nothing by default (or everything, depending on philosophy)
        return False 

    condition_matches = [email_field_matches_condition(email_data, cond) for cond in rule.conditions]

    if rule.condition_conjunction == "AND":
        return all(condition_matches)
    elif rule.condition_conjunction == "OR":
        return any(condition_matches)
    return False