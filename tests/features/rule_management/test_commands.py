import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open

from damien_cli import cli_entry
from damien_cli.features.rule_management.models import RuleModel # For constructing mock return values

# Sample rule data for mocking rule_storage return values
MOCK_RULE_1_DICT = {
    "id": "rule_abc", "name": "Newsletter Rule", "is_enabled": True,
    "conditions": [{"field": "from", "operator": "contains", "value": "news@example.com"}],
    "condition_conjunction": "AND",
    "actions": [{"type": "trash"}]
}
MOCK_RULE_1_MODEL = RuleModel(**MOCK_RULE_1_DICT)

MOCK_RULE_2_DICT = {
    "id": "rule_def", "name": "Urgent Subject Rule", "is_enabled": True,
    "conditions": [{"field": "subject", "operator": "contains", "value": "URGENT"}],
    "condition_conjunction": "AND",
    "actions": [{"type": "add_label", "label_name": "Important"}]
}
MOCK_RULE_2_MODEL = RuleModel(**MOCK_RULE_2_DICT)


@pytest.fixture
def runner():
    return CliRunner()

# Autouse fixture to mock logging for all rule command tests
@pytest.fixture(autouse=True)
def mock_logging_setup_for_rule_cli_tests():
    with patch('damien_cli.cli_entry.setup_logging') as mock_setup:
        mock_logger = MagicMock()
        mock_setup.return_value = mock_logger
        yield mock_logger


# --- Tests for 'damien rules list' ---
@patch('damien_cli.features.rule_management.commands.rule_storage.load_rules')
def test_rules_list_empty_human(mock_load_rules, runner):
    mock_load_rules.return_value = []
    result = runner.invoke(cli_entry.damien, ['rules', 'list'])
    assert result.exit_code == 0
    assert "No rules configured yet." in result.output

@patch('damien_cli.features.rule_management.commands.rule_storage.load_rules')
def test_rules_list_empty_json(mock_load_rules, runner):
    mock_load_rules.return_value = []
    result = runner.invoke(cli_entry.damien, ['rules', 'list', '--output-format', 'json'])
    assert result.exit_code == 0
    try:
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert output_data["command_executed"] == "damien rules list"
        assert output_data["message"] == "No rules configured yet."
        assert output_data["data"] == []
        assert output_data["error_details"] is None
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")

@patch('damien_cli.features.rule_management.commands.rule_storage.load_rules')
def test_rules_list_with_data_human(mock_load_rules, runner):
    mock_load_rules.return_value = [MOCK_RULE_1_MODEL, MOCK_RULE_2_MODEL]
    result = runner.invoke(cli_entry.damien, ['rules', 'list'])
    assert result.exit_code == 0
    assert "ID: rule_abc" in result.output
    assert "Name: Newsletter Rule" in result.output
    assert "Field: from, Operator: contains, Value: 'news@example.com'" in result.output
    assert "Type: trash" in result.output
    assert "ID: rule_def" in result.output
    assert "Name: Urgent Subject Rule" in result.output

@patch('damien_cli.features.rule_management.commands.rule_storage.load_rules')
def test_rules_list_with_data_json(mock_load_rules, runner):
    mock_load_rules.return_value = [MOCK_RULE_1_MODEL, MOCK_RULE_2_MODEL]
    result = runner.invoke(cli_entry.damien, ['rules', 'list', '--output-format', 'json'])
    assert result.exit_code == 0
    try:
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert output_data["command_executed"] == "damien rules list"
        assert "Successfully listed 2 rule(s)" in output_data["message"]
        assert len(output_data["data"]) == 2
        assert output_data["data"][0]['name'] == "Newsletter Rule"
        assert output_data["data"][1]['id'] == "rule_def"
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")


# --- Tests for 'damien rules add' ---
@patch('damien_cli.features.rule_management.commands.rule_storage.add_rule')
def test_rules_add_success_json_string(mock_add_rule, runner):
    mock_add_rule.return_value = True
    rule_json_string = json.dumps(MOCK_RULE_1_DICT)
    
    result = runner.invoke(cli_entry.damien, ['rules', 'add', '--rule-json', rule_json_string])
    
    assert result.exit_code == 0
    # Check that add_rule was called with a RuleModel instance
    mock_add_rule.assert_called_once()
    called_arg = mock_add_rule.call_args[0][0]
    assert isinstance(called_arg, RuleModel)
    assert called_arg.name == MOCK_RULE_1_DICT['name']
    assert f"Rule '{MOCK_RULE_1_DICT['name']}'" in result.output
    assert "added successfully." in result.output

@patch('builtins.open', new_callable=mock_open) # Mock the file open operation
@patch('damien_cli.features.rule_management.commands.rule_storage.add_rule')
def test_rules_add_success_from_file(mock_add_rule, mock_file_open, runner, tmp_path):
    # ARRANGE
    mock_add_rule.return_value = True
    rule_file_content = json.dumps(MOCK_RULE_1_DICT)
    # Configure mock_open to return the content when the file is read
    mock_file_open.return_value.read.return_value = rule_file_content
    
    fake_file_path = "dummy_path/my_rule.json" # Path doesn't need to exist because open is mocked

    # ACT
    result = runner.invoke(cli_entry.damien, ['rules', 'add', '--rule-json', fake_file_path])

    # ASSERT
    assert result.exit_code == 0
    mock_file_open.assert_called_once_with(fake_file_path, 'r') # Check file was "opened"
    mock_add_rule.assert_called_once()
    called_arg = mock_add_rule.call_args[0][0]
    assert isinstance(called_arg, RuleModel)
    assert called_arg.name == MOCK_RULE_1_DICT['name']
    assert f"Rule '{MOCK_RULE_1_DICT['name']}'" in result.output

def test_rules_add_missing_rule_json_option(runner):
    result = runner.invoke(cli_entry.damien, ['rules', 'add'])
    assert result.exit_code != 0 # Should indicate error or print help
    assert "Error: --rule-json option is required" in result.output
    assert "Example JSON structure for a rule:" in result.output

def test_rules_add_invalid_json_string(runner):
    result = runner.invoke(cli_entry.damien, ['rules', 'add', '--rule-json', "{not_json}"])
    assert result.exit_code != 0
    assert "Error: Could not parse --rule-json." in result.output

@patch('damien_cli.features.rule_management.commands.rule_storage.add_rule')
def test_rules_add_pydantic_validation_error(mock_add_rule, runner):
    # Simulate Pydantic validation error by passing incomplete data
    invalid_rule_data_str = json.dumps({"conditions": [], "actions": []}) # Missing 'name'
    
    result = runner.invoke(cli_entry.damien, ['rules', 'add', '--rule-json', invalid_rule_data_str])
    
    assert result.exit_code != 0 # Or however your command handles this error
    assert "Error: Rule data is invalid" in result.output
    assert "Validation details" in result.output
    mock_add_rule.assert_not_called() # add_rule shouldn't be called if validation fails before


# --- Tests for 'damien rules delete' ---
@patch('damien_cli.features.rule_management.commands.click.confirm')
@patch('damien_cli.features.rule_management.commands.rule_storage.delete_rule')
def test_rules_delete_success(mock_delete_rule, mock_confirm, runner):
    mock_confirm.return_value = True # User confirms deletion
    mock_delete_rule.return_value = True # rule_storage.delete_rule reports success
    rule_id_to_delete = "rule_abc"

    result = runner.invoke(cli_entry.damien, ['rules', 'delete', '--id', rule_id_to_delete])

    assert result.exit_code == 0
    mock_confirm.assert_called_once()
    mock_delete_rule.assert_called_once_with(rule_id_to_delete)
    assert f"Rule '{rule_id_to_delete}' deleted successfully." in result.output

@patch('damien_cli.features.rule_management.commands.click.confirm')
@patch('damien_cli.features.rule_management.commands.rule_storage.delete_rule')
def test_rules_delete_aborted_by_user(mock_delete_rule, mock_confirm, runner):
    mock_confirm.return_value = False # User says NO to confirmation

    result = runner.invoke(cli_entry.damien, ['rules', 'delete', '--id', 'some_id'])

    assert result.exit_code == 0 # Command itself doesn't fail
    mock_confirm.assert_called_once()
    mock_delete_rule.assert_not_called() # delete_rule should not be called
    assert "Rule deletion aborted by user." in result.output

@patch('damien_cli.features.rule_management.commands.click.confirm') # Still mock confirm as it's called first
@patch('damien_cli.features.rule_management.commands.rule_storage.delete_rule')
def test_rules_delete_not_found(mock_delete_rule, mock_confirm, runner):
    mock_confirm.return_value = True # User confirms, but rule_storage will fail
    mock_delete_rule.return_value = False # rule_storage.delete_rule reports not found/failure
    rule_id_to_delete = "non_existent_rule"

    result = runner.invoke(cli_entry.damien, ['rules', 'delete', '--id', rule_id_to_delete])
    
    assert result.exit_code == 0 # Command doesn't fail, just reports outcome
    mock_delete_rule.assert_called_once_with(rule_id_to_delete)
    assert f"Failed to delete rule '{rule_id_to_delete}'." in result.output