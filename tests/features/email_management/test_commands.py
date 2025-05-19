import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock # Removed call

from damien_cli import cli_entry
from damien_cli.core_api.exceptions import (
    GmailApiError,
    InvalidParameterError,
)  # For simulating errors

# Mock data remains the same
MOCK_MESSAGE_STUBS_PAGE1 = {
    "messages": [{"id": "111", "threadId": "aaa"}, {"id": "222", "threadId": "bbb"}],
    "nextPageToken": "page2_token",
}
MOCK_MESSAGE_STUBS_EMPTY = {"messages": [], "nextPageToken": None}
MOCK_MESSAGE_DETAIL_111 = {
    "id": "111",
    "threadId": "aaa",
    "snippet": "Hello from 111",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Test Subject 1"},
            {"name": "From", "value": "sender1@example.com"},
            {"name": "Date", "value": "Some Date 1"},
        ]
    },
}


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_gmail_service_in_context():  # This represents the raw Google API client resource
    return MagicMock(name="MockedRawGoogleServiceClient")


@pytest.fixture(autouse=True)
def mock_logging_setup_for_cli_tests():
    with patch("damien_cli.cli_entry.setup_logging") as mock_setup:
        mock_logger = MagicMock(name="MockLoggerFromCLIEntry")
        mock_setup.return_value = mock_logger
        # The nested patch below was causing the AttributeError and is not needed
        # if commands correctly get the logger from ctx.obj.
        yield mock_logger


# --- Tests for Read Commands ---
@patch("damien_cli.core_api.gmail_api_service.get_message_details")
@patch("damien_cli.core_api.gmail_api_service.list_messages")
def test_emails_list_human_output(
    mock_api_list_messages,
    mock_api_get_details,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_api_list_messages.return_value = MOCK_MESSAGE_STUBS_PAGE1

    def side_effect_get_details(service_client, msg_id, email_format):
        assert (
            service_client == mock_gmail_service_in_context
        )  # Ensure correct service passed
        if msg_id == "111":
            return MOCK_MESSAGE_DETAIL_111
        if msg_id == "222":
            return (
                MOCK_MESSAGE_DETAIL_111  # Using same detail for simplicity for stub 2
            )
        return None

    mock_api_get_details.side_effect = side_effect_get_details

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "list"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_api_list_messages.assert_called_once_with(
        mock_gmail_service_in_context,
        query_string=None,
        max_results=10,
        page_token=None,
    )
    assert mock_api_get_details.call_count == 2
    assert "ID: 111" in result.output
    assert 'To see more, use --page-token "page2_token"' in result.output


@patch("damien_cli.core_api.gmail_api_service.get_message_details")
@patch("damien_cli.core_api.gmail_api_service.list_messages")
def test_emails_list_json_output(
    mock_api_list_messages,
    mock_api_get_details,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_api_list_messages.return_value = MOCK_MESSAGE_STUBS_PAGE1

    def side_effect_get_details(service_client, msg_id, email_format):
        if msg_id == "111":
            return MOCK_MESSAGE_DETAIL_111
        if msg_id == "222":
            return (
                MOCK_MESSAGE_DETAIL_111  # Using same detail for simplicity for stub 2
            )
        return None

    mock_api_get_details.side_effect = side_effect_get_details

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "list", "--output-format", "json"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert mock_api_get_details.call_count == 2
    try:
        full_response_obj = json.loads(result.output)
        assert full_response_obj["status"] == "success"
        assert "data" in full_response_obj
        data_payload = full_response_obj["data"]
        assert len(data_payload["messages"]) == 2
        assert data_payload["messages"][0]["id"] == "111"
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")


@patch("damien_cli.core_api.gmail_api_service.list_messages")
def test_emails_list_no_results_human(
    mock_api_list_messages,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_api_list_messages.return_value = MOCK_MESSAGE_STUBS_EMPTY
    result = runner.invoke(
        cli_entry.damien,
        ["emails", "list"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )
    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert "No emails found." in result.output  # Adjusted message for no query


@patch("damien_cli.core_api.gmail_api_service.get_message_details")
def test_emails_get_human_output(
    mock_api_get_details,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_api_get_details.return_value = MOCK_MESSAGE_DETAIL_111
    result = runner.invoke(
        cli_entry.damien,
        ["emails", "get", "--id", "111", "--format", "full"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )
    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_api_get_details.assert_called_once_with(
        mock_gmail_service_in_context, "111", email_format="full"
    )
    assert "Details for Email ID: 111" in result.output


@patch("damien_cli.core_api.gmail_api_service.get_message_details")
def test_emails_get_json_output(
    mock_api_get_details,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_api_get_details.return_value = MOCK_MESSAGE_DETAIL_111

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "get", "--id", "111", "--output-format", "json"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )
    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    try:
        full_response_obj = json.loads(result.output)
        assert full_response_obj["status"] == "success"
        assert "data" in full_response_obj
        output_data = full_response_obj["data"]
        assert output_data["id"] == "111"
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to decode JSON: {e}\nOutput was:\n{result.output}")


@patch("damien_cli.core_api.gmail_api_service.get_message_details")
def test_emails_get_not_found_human(
    mock_api_get_details,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    # Simulate API raising an error for not found
    mock_api_get_details.side_effect = GmailApiError(
        "Message with ID ghost_id not found.",
        original_exception=Exception("Simulated 404"),
    )

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "get", "--id", "ghost_id"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 1
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert (
        "Error during 'damien emails get': Message with ID ghost_id not found."
        in result.output
    )


# --- NEW TESTS for Phase 2 Write Commands ---
@patch("damien_cli.features.email_management.commands.click.confirm")
@patch("damien_cli.core_api.gmail_api_service.batch_trash_messages")
def test_emails_trash_cmd_dry_run(
    mock_api_batch_trash,
    mock_click_confirm,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    result = runner.invoke(
        cli_entry.damien,
        ["emails", "trash", "--ids", "id1,id2", "--dry-run"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )
    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert (
        "DRY RUN: 2 email(s) would be moved to Trash. No actual changes made."
        in result.output
    )
    mock_api_batch_trash.assert_not_called()
    mock_click_confirm.assert_not_called()


@patch("damien_cli.features.email_management.commands.click.confirm")
@patch("damien_cli.core_api.gmail_api_service.batch_trash_messages")
def test_emails_trash_cmd_confirmed(
    mock_api_batch_trash,
    mock_click_confirm,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_click_confirm.return_value = True
    # mock_api_batch_trash.return_value = True # API function now returns None on success or raises error

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "trash", "--ids", "id1,id2"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_click_confirm.assert_called_once()
    mock_api_batch_trash.assert_called_once_with(
        mock_gmail_service_in_context, ["id1", "id2"]
    )
    assert "Successfully moved 2 email(s) to Trash." in result.output


@patch("damien_cli.features.email_management.commands.click.confirm")
@patch("damien_cli.core_api.gmail_api_service.batch_trash_messages")
def test_emails_trash_cmd_aborted(
    mock_api_batch_trash,
    mock_click_confirm,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_click_confirm.return_value = False

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "trash", "--ids", "id1"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_click_confirm.assert_called_once()
    mock_api_batch_trash.assert_not_called()
    assert "Action aborted by user." in result.output


# Tests for 'damien emails delete'
@patch("damien_cli.features.email_management.commands.click.prompt")
@patch("damien_cli.features.email_management.commands._confirm_action")
@patch("damien_cli.core_api.gmail_api_service.batch_delete_permanently")
def test_emails_delete_cmd_confirmed(
    mock_api_batch_delete,
    mock_internal_confirm_action,
    mock_click_prompt,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_internal_confirm_action.side_effect = [True, True]
    mock_click_prompt.return_value = "YESIDO"
    # mock_api_batch_delete.return_value = True # API returns None on success or raises

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "delete", "--ids", "id_perm_del"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert mock_internal_confirm_action.call_count == 2
    mock_click_prompt.assert_called_once()
    mock_api_batch_delete.assert_called_once_with(
        mock_gmail_service_in_context, ["id_perm_del"]
    )
    assert "Successfully PERMANENTLY DELETED 1 email(s)." in result.output


@patch("damien_cli.features.email_management.commands.click.prompt")
@patch("damien_cli.features.email_management.commands._confirm_action")
@patch("damien_cli.core_api.gmail_api_service.batch_delete_permanently")
def test_emails_delete_cmd_abort_at_type_yesido(
    mock_api_batch_delete,
    mock_internal_confirm_action,
    mock_click_prompt,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_internal_confirm_action.return_value = True
    mock_click_prompt.return_value = "NOPE"

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "delete", "--ids", "id_perm_del"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_internal_confirm_action.assert_called_once()
    mock_click_prompt.assert_called_once()
    mock_api_batch_delete.assert_not_called()
    assert (
        "Confirmation text did not match. Permanent deletion aborted." in result.output
    )


# Tests for 'damien emails label'
@patch("damien_cli.core_api.gmail_api_service.batch_modify_message_labels")
def test_emails_label_cmd_add_label(
    mock_api_batch_modify,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    # mock_api_batch_modify.return_value = True # API returns None on success

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "label", "--ids", "id1", "--add-labels", "NewLabel,TRASH"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_api_batch_modify.assert_called_once_with(
        mock_gmail_service_in_context,
        ["id1"],
        add_label_names=["NewLabel", "TRASH"],
        remove_label_names=[],  # Explicitly check for empty list if that's the default
    )
    assert "Successfully applied label changes" in result.output


# Tests for 'damien emails mark'
@patch("damien_cli.core_api.gmail_api_service.batch_mark_messages")
def test_emails_mark_cmd_read(
    mock_api_batch_mark,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    # mock_api_batch_mark.return_value = True # API returns None or raises

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "mark", "--ids", "id1,id2", "--action", "read"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 0
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_api_batch_mark.assert_called_once_with(
        mock_gmail_service_in_context, ["id1", "id2"], mark_as="read"
    )
    assert "Successfully marked 2 email(s) as read." in result.output


# Example tests for API error handling by CLI commands
@patch("damien_cli.features.email_management.commands.click.confirm")
@patch("damien_cli.core_api.gmail_api_service.batch_trash_messages")
def test_emails_trash_cmd_api_error(
    mock_api_batch_trash,
    mock_click_confirm,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_click_confirm.return_value = True  # User confirms
    mock_api_batch_trash.side_effect = GmailApiError(
        "API error trashing", original_exception=Exception("Original")
    )

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "trash", "--ids", "id1,id2", "--output-format", "human"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 1
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    mock_api_batch_trash.assert_called_once_with(
        mock_gmail_service_in_context, ["id1", "id2"]
    )
    assert "Error during 'damien emails trash': API error trashing" in result.output


@patch("damien_cli.features.email_management.commands.click.confirm")
@patch("damien_cli.core_api.gmail_api_service.batch_trash_messages")
def test_emails_trash_cmd_invalid_param_error_from_api(
    mock_api_batch_trash,
    mock_click_confirm,
    runner,
    mock_gmail_service_in_context,
    mock_logging_setup_for_cli_tests,
):
    mock_click_confirm.return_value = True  # User confirms
    mock_api_batch_trash.side_effect = InvalidParameterError("Invalid ID from API")

    result = runner.invoke(
        cli_entry.damien,
        ["emails", "trash", "--ids", "invalid_id_for_api"],
        obj={
            "logger": mock_logging_setup_for_cli_tests,
            "gmail_service": mock_gmail_service_in_context,
        },
    )

    assert (
        result.exit_code == 1
    ), f"CLI exited with {result.exit_code}, output: {result.output}"
    assert (
        "Error during 'damien emails trash': Invalid ID from API" in result.output
    )  # Check for the specific message from the exception
