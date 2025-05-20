import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from damien_cli import cli_entry
from damien_cli.features.rule_management.models import RuleModel


@pytest.fixture
def runner():
    return CliRunner()


# Autouse fixture to mock logging for all rule command tests
@pytest.fixture(autouse=True)
def mock_logging_setup_for_rule_cli_tests():
    with patch("damien_cli.cli_entry.setup_logging") as mock_setup:
        mock_logger = MagicMock()
        mock_setup.return_value = mock_logger
        yield mock_logger


# --- Tests for 'damien rules apply' ---
@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_basic_success(mock_apply_rules, runner):
    """Test basic successful execution of 'rules apply' command."""
    # Mock the API response
    mock_apply_rules.return_value = {
        "total_emails_scanned": 10,
        "emails_matching_any_rule": 3,
        "actions_planned_or_taken": {
            "add_label:Important": 2,
            "trash": 1
        },
        "rules_applied_counts": {
            "rule-id-1": 2,
            "rule-id-2": 1
        },
        "dry_run": False,
        "errors": []
    }
    
    # Run the command
    result = runner.invoke(cli_entry.damien, ["rules", "apply"])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    mock_apply_rules.assert_called_once()
    
    # Verify output contains key information
    assert "Rule Application Summary" in result.output
    assert "Total Emails Scanned: 10" in result.output
    assert "Emails Matching Any Rule: 3" in result.output
    assert "add_label:Important: 2 email(s)" in result.output
    assert "trash: 1 email(s)" in result.output


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_dry_run(mock_apply_rules, runner):
    """Test 'rules apply' with --dry-run flag."""
    # Mock the API response for dry run
    mock_apply_rules.return_value = {
        "total_emails_scanned": 10,
        "emails_matching_any_rule": 3,
        "actions_planned_or_taken": {
            "add_label:Important": 2,
            "trash": 1
        },
        "rules_applied_counts": {
            "rule-id-1": 2,
            "rule-id-2": 1
        },
        "dry_run": True,
        "errors": []
    }
    
    # Run the command with --dry-run
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--dry-run"])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    mock_apply_rules.assert_called_once()
    
    # Verify dry_run=True was passed to the API
    assert mock_apply_rules.call_args[1]["dry_run"] is True
    
    # Verify output indicates dry run
    assert "Dry Run: Yes" in result.output


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_with_options(mock_apply_rules, runner):
    """Test 'rules apply' with various command options."""
    # Mock a basic successful response
    mock_apply_rules.return_value = {
        "total_emails_scanned": 5,
        "emails_matching_any_rule": 1,
        "actions_planned_or_taken": {"trash": 1},
        "rules_applied_counts": {"rule-id-2": 1},
        "dry_run": False,
        "errors": []
    }
    
    # Run the command with options
    result = runner.invoke(cli_entry.damien, [
        "rules", "apply",
        "--query", "is:unread",
        "--rule-ids", "rule-id-1,rule-id-2",
        "--scan-limit", "100",
        "--date-after", "2024/05/01"
    ])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    mock_apply_rules.assert_called_once()
    
    # Verify options were passed correctly to the API
    call_kwargs = mock_apply_rules.call_args[1]
    assert "is:unread" in call_kwargs["gmail_query_filter"]
    assert call_kwargs["rule_ids_to_apply"] == ["rule-id-1", "rule-id-2"]
    assert call_kwargs["scan_limit"] == 100
    
    # Verify date filtering was applied
    assert "after:2024/05/01" in call_kwargs["gmail_query_filter"]


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_json_output(mock_apply_rules, runner):
    """Test 'rules apply' with JSON output format."""
    # Mock the API response
    mock_apply_rules.return_value = {
        "total_emails_scanned": 10,
        "emails_matching_any_rule": 3,
        "actions_planned_or_taken": {
            "add_label:Important": 2,
            "trash": 1
        },
        "rules_applied_counts": {
            "rule-id-1": 2,
            "rule-id-2": 1
        },
        "dry_run": False,
        "errors": []
    }
    
    # Run the command with JSON output
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--output-format", "json"])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    
    # Verify JSON output
    try:
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert output_data["command_executed"] == "damien rules apply"
        assert output_data["data"]["total_emails_scanned"] == 10
        assert output_data["data"]["emails_matching_any_rule"] == 3
        assert output_data["data"]["actions_planned_or_taken"]["trash"] == 1
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")


@patch("damien_cli.features.rule_management.commands.click.confirm")
@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_with_confirmation(mock_apply_rules, mock_confirm, runner):
    """Test 'rules apply' with --confirm flag."""
    # Mock confirmation and API response
    mock_confirm.return_value = True  # User confirms
    mock_apply_rules.return_value = {
        "total_emails_scanned": 5,
        "emails_matching_any_rule": 2,
        "actions_planned_or_taken": {"trash": 2},
        "rules_applied_counts": {"rule-id-1": 2},
        "dry_run": False,
        "errors": []
    }
    
    # Run the command with --confirm
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--confirm"])
    
    # Verify the confirmation prompt was shown
    mock_confirm.assert_called_once()
    
    # Verify the command proceeded after confirmation
    assert result.exit_code == 0
    mock_apply_rules.assert_called_once()


@patch("damien_cli.features.rule_management.commands.click.confirm")
@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_confirmation_aborted(mock_apply_rules, mock_confirm, runner):
    """Test 'rules apply' when user aborts at confirmation prompt."""
    # Mock user says "no" to confirmation
    mock_confirm.return_value = False
    
    # Run the command with --confirm
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--confirm"])
    
    # Verify the confirmation prompt was shown
    mock_confirm.assert_called_once()
    
    # Verify the command was aborted and API wasn't called
    assert "aborted" in result.output.lower()
    mock_apply_rules.assert_not_called()


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_error_handling(mock_apply_rules, runner):
    """Test error handling in 'rules apply' command."""
    # Mock API to raise an error
    from damien_cli.core_api.exceptions import GmailApiError
    mock_apply_rules.side_effect = GmailApiError("Failed to connect to Gmail API")
    
    # Run the command
    result = runner.invoke(cli_entry.damien, ["rules", "apply"])
    
    # Verify error was handled
    assert result.exit_code == 1  # Non-zero exit code
    assert "Error" in result.output
    assert "Failed to connect to Gmail API" in result.output


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_no_matched_emails(mock_apply_rules, runner):
    """Test 'rules apply' when no emails match any rules."""
    # Mock API response with no matches
    mock_apply_rules.return_value = {
        "total_emails_scanned": 10,
        "emails_matching_any_rule": 0,
        "actions_planned_or_taken": {},
        "rules_applied_counts": {},
        "dry_run": False,
        "errors": []
    }
    
    # Run the command
    result = runner.invoke(cli_entry.damien, ["rules", "apply"])
    
    # Verify the command executed successfully but shows no matches
    assert result.exit_code == 0
    assert "Total Emails Scanned: 10" in result.output
    assert "Emails Matching Any Rule: 0" in result.output
    assert "No actions were planned or taken" in result.output


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_with_errors_in_summary(mock_apply_rules, runner):
    """Test 'rules apply' when the summary contains errors."""
    # Mock API response with errors in summary
    mock_apply_rules.return_value = {
        "total_emails_scanned": 10,
        "emails_matching_any_rule": 3,
        "actions_planned_or_taken": {"trash": 2},
        "rules_applied_counts": {"rule-id-1": 3},
        "dry_run": False,
        "errors": [
            {"error_type": "EMAIL_FETCH_FAILURE", "details": "Rate limit exceeded"},
            {"error_type": "ACTION_EXECUTION_FAILURE", "action": "add_label:Important", "details": "Label not found"}
        ]
    }
    
    # Run the command
    result = runner.invoke(cli_entry.damien, ["rules", "apply"])
    
    # Verify errors are displayed
    assert result.exit_code == 0  # Command itself succeeds even if summary has errors from API
    assert "Errors Encountered During Application" in result.output
    assert "Rate limit exceeded" in result.output
    assert "Label not found" in result.output


@patch("damien_cli.core_api.gmail_api_service.get_authenticated_service", return_value=None) # Patch where it's defined, so cli_entry uses the mock
@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox") # This mock won't be hit by apply_rules_cmd
def test_rules_apply_no_gmail_service(mock_apply_rules_cmd_target, mock_get_auth_svc_gmail_api, runner): # Renamed mock_get_auth_svc
    """Test 'rules apply' when no Gmail service is found in context (user not logged in)."""
    # The critical part is that mock_get_auth_svc_gmail_api ensures gmail_service is None when cli_entry.py calls it.
    result = runner.invoke(cli_entry.damien, ["rules", "apply"])

    assert result.exit_code == 1
    assert "Damien is not connected to Gmail" in result.output
    mock_apply_rules_cmd_target.assert_not_called()
    mock_get_auth_svc_gmail_api.assert_called_once() # cli_entry should try to get it

@patch("damien_cli.core_api.gmail_api_service.get_authenticated_service", return_value=None) # Patch where it's defined
@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox") # This mock won't be hit
def test_rules_apply_no_gmail_service_json_output(mock_apply_rules_cmd_target, mock_get_auth_svc_gmail_api, runner): # Renamed mock_get_auth_svc
    """Test 'rules apply' with JSON output when no Gmail service is found."""
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--output-format", "json"])
    
    assert result.exit_code == 1
    try:
        output_data = json.loads(result.output)
        assert output_data["status"] == "error"
        assert "Damien is not connected to Gmail" in output_data["message"]
        assert output_data["error_details"]["code"] == "NO_GMAIL_SERVICE"
    except json.JSONDecodeError:
        pytest.fail(f"Failed to decode JSON output: {result.output}")
    mock_apply_rules_cmd_target.assert_not_called()
    mock_get_auth_svc_gmail_api.assert_called_once()


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_rule_storage_error(mock_apply_rules, runner):
    """Test 'rules apply' when RuleStorageError is raised by the API."""
    from damien_cli.core_api.exceptions import RuleStorageError
    mock_apply_rules.side_effect = RuleStorageError("Failed to load rules from disk.")
    
    # Need to pass a mock gmail_service in context for the command to proceed to API call
    mock_g_service = MagicMock()
    result = runner.invoke(cli_entry.damien, ["rules", "apply"], obj={'gmail_service': mock_g_service})
    
    assert result.exit_code == 1
    assert "Error" in result.output
    assert "Failed to load rules from disk" in result.output


@patch("damien_cli.core_api.rules_api_service.apply_rules_to_mailbox")
def test_rules_apply_api_error_json_output(mock_apply_rules, runner):
    """Test 'rules apply' with JSON output when a GmailApiError occurs."""
    from damien_cli.core_api.exceptions import GmailApiError
    error_message = "Mocked Gmail API failure"
    mock_apply_rules.side_effect = GmailApiError(error_message)

    # Need to pass a mock gmail_service in context
    mock_g_service = MagicMock()
    result = runner.invoke(cli_entry.damien, ["rules", "apply", "--output-format", "json"], obj={'gmail_service': mock_g_service})

    assert result.exit_code == 1
    try:
        output_data = json.loads(result.output)
        assert output_data["status"] == "error"
        assert error_message in output_data["message"]
        assert output_data["error_details"]["code"] == "GMAILAPIERROR" # Error class name to upper
        assert error_message in output_data["error_details"]["details"]
    except json.JSONDecodeError:
        pytest.fail(f"Failed to decode JSON output: {result.output}")
