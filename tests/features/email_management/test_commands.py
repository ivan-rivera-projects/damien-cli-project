import pytest
import json
from click.testing import CliRunner 
from unittest.mock import patch, MagicMock, call # Added 'call'

from damien_cli import cli_entry 

MOCK_MESSAGE_STUBS_PAGE1 = {
    'messages': [{'id': '111', 'threadId': 'aaa'}, {'id': '222', 'threadId': 'bbb'}],
    'nextPageToken': 'page2_token'
}
MOCK_MESSAGE_STUBS_EMPTY = {'messages': [], 'nextPageToken': None}

MOCK_MESSAGE_DETAIL_111 = {
    'id': '111', 'threadId': 'aaa', 'snippet': 'Hello from 111',
    'payload': {'headers': [
        {'name': 'Subject', 'value': 'Test Subject 1'},
        {'name': 'From', 'value': 'sender1@example.com'},
        {'name': 'Date', 'value': 'Some Date 1'}
    ]}
}
MOCK_MESSAGE_DETAIL_222 = { # Not strictly needed for these tests, but good to have if used elsewhere
    'id': '222', 'threadId': 'bbb', 'snippet': 'Hi from 222',
    'payload': {'headers': [
        {'name': 'Subject', 'value': 'Test Subject 2'},
        {'name': 'From', 'value': 'sender2@example.com'},
        {'name': 'Date', 'value': 'Some Date 2'}
    ]}
}

@pytest.fixture
def runner():
    return CliRunner() 

@pytest.fixture
def mock_gmail_service_in_context(): # This mock is what the commands will find in ctx.obj['gmail_service']
    mock_svc = MagicMock()
    # Configure any default behaviors for this mock_svc if needed by the command group's initial setup
    return mock_svc

# Helper to mock the setup_logging to prevent actual log file writes and console noise during most tests
@pytest.fixture(autouse=True) # Apply to all tests in this file
def mock_logging_setup_for_cli_tests():
    with patch('damien_cli.cli_entry.setup_logging') as mock_setup:
        mock_logger = MagicMock()
        mock_setup.return_value = mock_logger
        yield mock_logger # The test can use this if it wants to assert logging calls


# --- Tests for Read Commands (Existing, ensure they still pass) ---
@patch('damien_cli.features.email_management.commands.gmail_integration.get_message_details')
@patch('damien_cli.features.email_management.commands.gmail_integration.list_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service') 
def test_emails_list_human_output(mock_get_service_call, mock_list_messages, mock_get_details, runner, mock_gmail_service_in_context, caplog):
    import logging
    # caplog fixture is from pytest-cov or pytest itself, allow capturing logs by our app's logger
    # The autouse fixture mock_logging_setup_for_cli_tests replaces the actual logger with a MagicMock.
    # If we want to test what's logged, we'd pass that mock_logger from the fixture.
    # For now, let's assume the mock_logger from autouse fixture handles silencing.

    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_list_messages.return_value = MOCK_MESSAGE_STUBS_PAGE1
    
    def side_effect_get_details(service, msg_id, email_format):
        if msg_id == '111': return MOCK_MESSAGE_DETAIL_111
        if msg_id == '222': return MOCK_MESSAGE_DETAIL_222
        return None
    mock_get_details.side_effect = side_effect_get_details

    result = runner.invoke(cli_entry.damien, ['emails', 'list'])

    assert result.exit_code == 0 
    mock_list_messages.assert_called_once_with(mock_gmail_service_in_context, query_string=None, max_results=10, page_token=None)
    assert mock_get_details.call_count == 2 
    
    assert "ID: 111" in result.output
    assert "To see more, use --page-token \"page2_token\"" in result.output


@patch('damien_cli.features.email_management.commands.gmail_integration.get_message_details')
@patch('damien_cli.features.email_management.commands.gmail_integration.list_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_list_json_output(mock_get_service_call, mock_list_messages, mock_get_details, runner, mock_gmail_service_in_context):
    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_list_messages.return_value = MOCK_MESSAGE_STUBS_PAGE1
    def side_effect_get_details(service, msg_id, email_format): # Simulate fetching details for JSON
        if msg_id == '111': return MOCK_MESSAGE_DETAIL_111
        if msg_id == '222': return MOCK_MESSAGE_DETAIL_222
        return None
    mock_get_details.side_effect = side_effect_get_details
            
    result = runner.invoke(cli_entry.damien, ['emails', 'list', '--output-format', 'json'])

    assert result.exit_code == 0
    assert mock_get_details.call_count == 2 # Should be called for detailed JSON output

    try:
        output_data = json.loads(result.output) # result.output should be clean JSON
        assert output_data["status"] == "success"
        assert output_data["command_executed"] == "damien emails list"
        assert "Successfully listed 2 email(s)" in output_data["message"]
        assert output_data["data"]["count_returned"] == 2
        assert output_data["data"]["next_page_token"] == "page2_token"
        assert len(output_data["data"]["messages"]) == 2
        assert output_data["error_details"] is None
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")


@patch('damien_cli.features.email_management.commands.gmail_integration.list_messages') # Only list_messages needed for this one
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_list_no_results_human(mock_get_service_call, mock_list_messages, runner, mock_gmail_service_in_context):
    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_list_messages.return_value = MOCK_MESSAGE_STUBS_EMPTY 
    result = runner.invoke(cli_entry.damien, ['emails', 'list'])
    assert result.exit_code == 0
    assert "Damien found no emails matching your criteria." in result.output


@patch('damien_cli.features.email_management.commands.gmail_integration.get_message_details')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_get_human_output(mock_get_service_call, mock_get_details, runner, mock_gmail_service_in_context):
    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_get_details.return_value = MOCK_MESSAGE_DETAIL_111
    result = runner.invoke(cli_entry.damien, ['emails', 'get', '--id', '111', '--format', 'full'])
    assert result.exit_code == 0
    mock_get_details.assert_called_once_with(mock_gmail_service_in_context, '111', email_format='full')
    assert "Details for Email ID: 111" in result.output


@patch('damien_cli.features.email_management.commands.gmail_integration.get_message_details')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_get_json_output(mock_get_service_call, mock_get_details, runner, mock_gmail_service_in_context):
    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_get_details.return_value = MOCK_MESSAGE_DETAIL_111 # This is the raw email data
    
    # Patch setup_logging for this specific test to ensure clean JSON output
    with patch('damien_cli.cli_entry.setup_logging') as mock_setup_logging_cli:
        mock_logger_cli = MagicMock()
        mock_setup_logging_cli.return_value = mock_logger_cli

        result = runner.invoke(cli_entry.damien, ['emails', 'get', '--id', '111', '--output-format', 'json'])
    
    assert result.exit_code == 0
    try:
        # The result.output should be the full JSON response object
        # as printed by sys.stdout.write(json.dumps(response_obj, indent=2) + '\n')
        # in your get_cmd
        full_response_obj = json.loads(result.output)
        
        # Verify the standard response structure
        assert full_response_obj['status'] == 'success'
        assert 'data' in full_response_obj
        
        # The actual email data is nested within the 'data' key
        output_data = full_response_obj['data'] # <--- ACCESS THE 'data' KEY
        
        assert output_data['id'] == '111' # Now check 'id' within the 'data' object
        assert output_data['snippet'] == 'Hello from 111' # And other fields from MOCK_MESSAGE_DETAIL_111
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")
    except KeyError as e: # Catch KeyError specifically for better debugging if 'data' or 'id' is missing
        pytest.fail(f"KeyError: {e} in parsed JSON. \nParsed object: {full_response_obj}\nOriginal output:\n{result.output}")


@patch('damien_cli.features.email_management.commands.gmail_integration.get_message_details')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_get_not_found_human(mock_get_service_call, mock_get_details, runner, mock_gmail_service_in_context):
    mock_get_service_call.return_value = mock_gmail_service_in_context
    mock_get_details.return_value = None 
    result = runner.invoke(cli_entry.damien, ['emails', 'get', '--id', 'ghost_id'])
    assert result.exit_code == 0 
    assert "Damien could not retrieve details for email ID ghost_id" in result.output

# --- NEW TESTS for Phase 2 Write Commands ---

@patch('damien_cli.features.email_management.commands.click.confirm') # Mock click.confirm
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_trash_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_trash_cmd_dry_run(mock_get_service, mock_batch_trash, mock_confirm, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    result = runner.invoke(cli_entry.damien, ['emails', 'trash', '--ids', 'id1,id2', '--dry-run'])
    assert result.exit_code == 0
    assert "DRY RUN: Emails would be moved to Trash." in result.output
    mock_batch_trash.assert_not_called()
    mock_confirm.assert_not_called()

@patch('damien_cli.features.email_management.commands.click.confirm')
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_trash_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_trash_cmd_confirmed(mock_get_service, mock_batch_trash, mock_confirm, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_confirm.return_value = True # User confirms 'yes'
    mock_batch_trash.return_value = True # Gmail integration reports success

    result = runner.invoke(cli_entry.damien, ['emails', 'trash', '--ids', 'id1,id2'])
    
    assert result.exit_code == 0
    mock_confirm.assert_called_once()
    mock_batch_trash.assert_called_once_with(mock_gmail_service_in_context, ['id1', 'id2'])
    assert "Successfully moved 2 email(s) to Trash." in result.output

@patch('damien_cli.features.email_management.commands.click.confirm')
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_trash_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_trash_cmd_aborted(mock_get_service, mock_batch_trash, mock_confirm, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_confirm.return_value = False # User confirms 'no'

    result = runner.invoke(cli_entry.damien, ['emails', 'trash', '--ids', 'id1'])
    
    assert result.exit_code == 0 # Command itself doesn't error, just aborts
    mock_confirm.assert_called_once()
    mock_batch_trash.assert_not_called()
    assert "Action aborted by user." in result.output


# Tests for 'damien emails delete'
@patch('damien_cli.features.email_management.commands.click.prompt') # For the "YESIDO" prompt
@patch('damien_cli.features.email_management.commands._confirm_action') # For the yes/no prompts
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_delete_permanently')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_delete_cmd_confirmed(mock_get_service, mock_batch_delete, mock_confirm_action, mock_click_prompt, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_confirm_action.side_effect = [True, True] # First and third y/n confirmations pass
    mock_click_prompt.return_value = "YESIDO"      # Second "type YESIDO" confirmation passes
    mock_batch_delete.return_value = True          # Gmail integration reports success

    result = runner.invoke(cli_entry.damien, ['emails', 'delete', '--ids', 'id_perm_del'])
    
    assert result.exit_code == 0
    assert mock_confirm_action.call_count == 2 # Two yes/no prompts
    mock_click_prompt.assert_called_once()
    mock_batch_delete.assert_called_once_with(mock_gmail_service_in_context, ['id_perm_del'])
    assert "Successfully PERMANENTLY DELETED 1 email(s)." in result.output


@patch('damien_cli.features.email_management.commands.click.prompt')
@patch('damien_cli.features.email_management.commands._confirm_action')
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_delete_permanently')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_delete_cmd_abort_at_type_yesido(mock_get_service, mock_batch_delete, mock_confirm_action, mock_click_prompt, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_confirm_action.return_value = True # First y/n passes
    mock_click_prompt.return_value = "NOPE" # Fails "YESIDO"

    result = runner.invoke(cli_entry.damien, ['emails', 'delete', '--ids', 'id_perm_del'])
    
    assert result.exit_code == 0
    mock_confirm_action.assert_called_once() # Only first y/n prompt
    mock_click_prompt.assert_called_once()
    mock_batch_delete.assert_not_called()
    assert "Confirmation text did not match. Permanent deletion aborted." in result.output


# Tests for 'damien emails label'
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_modify_message_labels')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_label_cmd_add_label(mock_get_service, mock_batch_modify, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_batch_modify.return_value = True

    result = runner.invoke(cli_entry.damien, ['emails', 'label', '--ids', 'id1', '--add-labels', 'NewLabel,TRASH'])
    
    assert result.exit_code == 0
    mock_batch_modify.assert_called_once_with(
        mock_gmail_service_in_context, 
        ['id1'], 
        add_label_names=['NewLabel', 'TRASH'], 
        remove_label_names=[]
    )
    assert "Successfully applied label changes" in result.output


# Tests for 'damien emails mark'
@patch('damien_cli.features.email_management.commands.gmail_integration.batch_mark_messages')
@patch('damien_cli.features.email_management.commands.gmail_integration.get_gmail_service')
def test_emails_mark_cmd_read(mock_get_service, mock_batch_mark, runner, mock_gmail_service_in_context):
    mock_get_service.return_value = mock_gmail_service_in_context
    mock_batch_mark.return_value = True

    result = runner.invoke(cli_entry.damien, ['emails', 'mark', '--ids', 'id1,id2', '--action', 'read'])
    
    assert result.exit_code == 0
    mock_batch_mark.assert_called_once_with(mock_gmail_service_in_context, ['id1', 'id2'], mark_as='read')
    assert "Successfully marked 2 email(s) as read." in result.output