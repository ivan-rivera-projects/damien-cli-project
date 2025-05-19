import click
import json 
import sys # For sys.stdout.write
import base64 # For decoding email body

from damien_cli.integrations import gmail_integration
# from damien_cli.core.config import SCOPES # SCOPES not directly used here, but good to keep if ever needed for checks

# --- Helper Functions ---

def _extract_headers(message_payload: dict) -> dict:
    """Extracts common headers from a message payload."""
    headers_list = message_payload.get('headers', [])
    subject = next((h['value'] for h in headers_list if h['name'].lower() == 'subject'), 'N/A')
    sender = next((h['value'] for h in headers_list if h['name'].lower() == 'from'), 'N/A')
    date = next((h['value'] for h in headers_list if h['name'].lower() == 'date'), 'N/A')
    return {"subject": subject, "from": sender, "date": date}

def _parse_ids(ids_str: str) -> list:
    """Parses a comma-separated string of IDs into a list of non-empty stripped IDs."""
    if not ids_str:
        return []
    return [id_val.strip() for id_val in ids_str.split(',') if id_val.strip()]

def _confirm_action(prompt_message: str, abort_message: str = "Action aborted by user.") -> bool:
    """Prompts user for confirmation. Returns True if confirmed, False (and prints abort_message) otherwise."""
    if not click.confirm(prompt_message, default=False, abort=False): 
        click.echo(abort_message)
        return False
    return True

# --- Click Command Group ---

@click.group("emails") 
@click.pass_context
def emails_group(ctx):
    """Manage emails in your Gmail account."""
    logger = ctx.obj.get('logger')
    if not ctx.obj.get('gmail_service'):
        if logger: logger.debug("emails_group: Gmail service not in context, attempting to get it.")
        # Ensure get_gmail_service is available or imported if called directly here
        # from damien_cli.integrations.gmail_integration import get_gmail_service # Alt: import at top
        service = gmail_integration.get_gmail_service() # Assumes gmail_integration is imported
        if not service:
            if logger: logger.error("Failed to get Gmail service for 'emails' commands.")
            # Avoid click.echo here if we want clean JSON output in tests later
            # click.echo("Damien could not connect to Gmail. Please try `damien login` again.")
            ctx.abort() # Stops further execution of this command group
        ctx.obj['gmail_service'] = service
    elif logger:
            logger.debug("emails_group: Gmail service found in context.")

# --- Email Read Commands ---

@emails_group.command("list")
@click.option('--query', '-q', default=None, help="Gmail search query (e.g., 'is:unread from:newsletter@example.com').")
@click.option('--max-results', '-m', type=int, default=10, show_default=True, help="Maximum messages to list.")
@click.option('--page-token', '-p', default=None, help="Page token for pagination.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def list_cmd(ctx, query, max_results, page_token, output_format):
    """Lists emails matching criteria."""
    logger = ctx.obj.get('logger')
    if logger: logger.info(f"Executing 'emails list' with query='{query}', max_results={max_results}")
    
    service = ctx.obj.get('gmail_service')
    if not service: 
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails list",
                "parameters_provided": {
                    "query": query,
                    "max_results": max_results,
                    "page_token": page_token
                },
                "message": "Critical: Gmail service not available.",
                "data": None,
                "error_details": {
                    "code": "SERVICE_UNAVAILABLE",
                    "details": "Gmail service is not available. Try running 'damien login' first."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("Critical: Gmail service not available.")
        if logger: logger.error("Critical: Gmail service missing in list_cmd context.")
        return

    result_data = gmail_integration.list_messages(service, query_string=query, max_results=max_results, page_token=page_token)

    if result_data is None:
        if logger: logger.error("Failed to retrieve messages from gmail_integration.list_messages.")
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails list",
                "parameters_provided": {
                    "query": query,
                    "max_results": max_results,
                    "page_token": page_token
                },
                "message": "Damien could not retrieve messages. API error occurred.",
                "data": None,
                "error_details": {
                    "code": "GMAIL_API_ERROR",
                    "details": "Gmail API returned an error when listing messages."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("Damien could not retrieve messages.")
        return

    messages_stubs = result_data.get('messages', [])
    next_page = result_data.get('nextPageToken')

    if output_format == 'json':
        detailed_messages = []
        if messages_stubs:
            if logger: logger.info(f"Fetching metadata for {len(messages_stubs)} messages for JSON output...")
            for stub in messages_stubs:
                msg_detail = gmail_integration.get_message_details(service, stub['id'], email_format='metadata')
                if msg_detail:
                    headers = _extract_headers(msg_detail.get('payload', {}))
                    detailed_messages.append({
                        "id": msg_detail['id'],
                        "threadId": msg_detail['threadId'],
                        "subject": headers['subject'],
                        "from": headers['from'],
                        "date": headers['date'],
                        "snippet": msg_detail.get('snippet', '')
                    })
                else:
                    detailed_messages.append({"id": stub['id'], "error": "Could not fetch details"})
        
        message_text = f"Successfully listed {len(messages_stubs)} email(s) matching criteria."
        if not messages_stubs:
            message_text = "No emails found matching your criteria."
            
        output_obj = {
            "status": "success",
            "command_executed": "damien emails list",
            "parameters_provided": {
                "query": query,
                "max_results": max_results,
                "page_token": page_token
            },
            "message": message_text,
            "data": {
                "count_returned": len(messages_stubs),
                "next_page_token": next_page,
                "messages": detailed_messages
            },
            "error_details": None
        }
        sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
    else: # human format
        if not messages_stubs:
            click.echo("Damien found no emails matching your criteria.")
        else:
            click.echo(f"\nDamien found {len(messages_stubs)} email(s):")
            for stub in messages_stubs:
                msg_detail = gmail_integration.get_message_details(service, stub['id'], email_format='metadata')
                if msg_detail:
                    headers = _extract_headers(msg_detail.get('payload', {}))
                    click.echo("-" * 30)
                    click.echo(f"  ID: {msg_detail['id']}")
                    click.echo(f"  From: {headers['from']}")
                    click.echo(f"  Subject: {headers['subject']}")
                    click.echo(f"  Date: {headers['date']}")
                    click.echo(f"  Snippet: {msg_detail.get('snippet', '')[:70]}...") 
                else:
                    click.echo("-" * 30)
                    click.echo(f"  ID: {stub['id']} (Could not fetch details)")
            if next_page:
                click.echo("-" * 30)
                click.echo(f"\nTo see more, use --page-token \"{next_page}\"")
    if logger: logger.info("'emails list' command finished.")


@emails_group.command("get")
@click.option('--id', 'message_id', required=True, help="The ID of the email to retrieve.")
@click.option('--format', 'email_format', type=click.Choice(['metadata', 'full', 'raw']), default='full', show_default=True, help="Format of the email details.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def get_cmd(ctx, message_id, email_format, output_format):
    """Gets and displays details of a specific email."""
    logger = ctx.obj.get('logger')
    if logger: logger.info(f"Executing 'emails get' for ID='{message_id}', format='{email_format}'")

    service = ctx.obj.get('gmail_service')
    if not service:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails get",
                "parameters_provided": {
                    "message_id": message_id,
                    "email_format": email_format
                },
                "message": "Critical: Gmail service not available.",
                "data": None,
                "error_details": {
                    "code": "SERVICE_UNAVAILABLE",
                    "details": "Gmail service is not available. Try running 'damien login' first."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("Critical: Gmail service not available.")
        if logger: logger.error("Critical: Gmail service missing in get_cmd context.")
        return

    message_data = gmail_integration.get_message_details(service, message_id, email_format=email_format)

    if output_format == 'json':
        if not message_data:
            output_obj = {
                "status": "error",
                "command_executed": "damien emails get",
                "parameters_provided": {
                    "message_id": message_id,
                    "email_format": email_format
                },
                "message": f"Message with ID '{message_id}' not found or API error occurred.",
                "data": None,
                "error_details": {
                    "code": "MESSAGE_NOT_FOUND_OR_API_ERROR",
                    "details": "The requested message could not be retrieved. It may not exist or there was an API error."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails get",
                "parameters_provided": {
                    "message_id": message_id,
                    "email_format": email_format
                },
                "message": f"Successfully retrieved message with ID '{message_id}'.",
                "data": message_data,
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
    else: # human format
        if not message_data:
            if logger: logger.error(f"Failed to retrieve details for message ID {message_id}.")
            click.echo(f"Damien could not retrieve details for email ID {message_id}.")
        else:
            click.echo(f"\n--- Details for Email ID: {message_data['id']} ---")
            click.echo(f"Thread ID: {message_data['threadId']}")
            click.echo(f"Snippet: {message_data['snippet']}")
            
            payload = message_data.get('payload', {})
            headers_data = _extract_headers(payload) # Renamed to avoid conflict with 'headers' variable name
            click.echo(f"From: {headers_data['from']}")
            click.echo(f"Subject: {headers_data['subject']}")
            click.echo(f"Date: {headers_data['date']}")

            if email_format == 'full' or email_format == 'raw':
                parts = payload.get('parts', [])
                body_content = "Body content not easily displayed in this simple view. Try JSON output or a dedicated email viewer."
                if payload.get('body') and payload['body'].get('data'):
                    body_content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
                elif parts:
                    for part in parts:
                        if part.get('mimeType') == 'text/plain' and part.get('body') and part['body'].get('data'):
                            body_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                            break
                click.echo("\n--- Body (Plain Text Sample) ---")
                click.echo(body_content[:500] + "..." if len(body_content) > 500 else body_content)
            click.echo("-" * 30)
    if logger: logger.info(f"'emails get' for ID {message_id} finished.")

# --- Email Write Commands ---

@emails_group.command("trash")
@click.option('--ids', 'message_ids_str', required=True, help="Comma-separated list of email IDs to trash.")
@click.option('--dry-run', is_flag=True, help="Show what would be done without actually doing it.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def trash_cmd(ctx, message_ids_str, dry_run, output_format):
    """Moves specified emails to Trash."""
    logger = ctx.obj.get('logger')
    service = ctx.obj.get('gmail_service')
    message_ids = _parse_ids(message_ids_str)

    if not message_ids:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails trash",
                "parameters_provided": {
                    "message_ids": [],
                    "dry_run": dry_run
                },
                "message": "No message IDs provided to trash.",
                "data": None,
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "--ids option requires at least one valid message ID."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("No message IDs provided to trash.")
        if logger: logger.warning("Trash command called with no message IDs.")
        return

    if logger: logger.info(f"Executing 'emails trash' for IDs: {message_ids} (Dry run: {dry_run})")
    
    if output_format == 'json':
        if dry_run:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails trash",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "DRY RUN: Emails would be moved to Trash. No actual changes made.",
                "data": {
                    "processed_ids": message_ids,
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("Dry run: Trash operation completed.")
            return
        
        if not _confirm_action(f"Are you sure you want to move these {len(message_ids)} email(s) to Trash?"):
            output_obj = {
                "status": "aborted_by_user",
                "command_executed": "damien emails trash",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "Action aborted by user.",
                "data": {
                    "processed_ids": [],
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("User aborted trash operation.")
            return
        
        success = gmail_integration.batch_trash_messages(service, message_ids)
        if success:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails trash",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": f"Successfully moved {len(message_ids)} email(s) to Trash.",
                "data": {
                    "processed_ids": message_ids,
                    "action_taken": True
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info(f"Successfully trashed {len(message_ids)} emails.")
        else:
            output_obj = {
                "status": "error",
                "command_executed": "damien emails trash",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "Failed to move emails to Trash. Check logs for details.",
                "data": {
                    "processed_ids_attempted": message_ids,
                    "action_taken": False
                },
                "error_details": {
                    "code": "GMAIL_API_BATCH_MODIFY_ERROR",
                    "details": "API returned error for batchModify operation. Check logs for more details."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.error("Trash operation failed at integration level.")
    else: # human format
        click.echo(f"Preparing to move {len(message_ids)} email(s) to Trash...")

        if dry_run:
            click.echo("DRY RUN: Emails would be moved to Trash. No actual changes made.")
            if logger: logger.info("Dry run: Trash operation completed.")
            return

        if not _confirm_action(f"Are you sure you want to move these {len(message_ids)} email(s) to Trash?"):
            if logger: logger.info("User aborted trash operation.")
            return
        
        success = gmail_integration.batch_trash_messages(service, message_ids)
        if success:
            click.echo(f"Successfully moved {len(message_ids)} email(s) to Trash.")
            if logger: logger.info(f"Successfully trashed {len(message_ids)} emails.")
        else:
            click.echo("Failed to move emails to Trash. Check logs for details.")
            if logger: logger.error("Trash operation failed at integration level.")
        

@emails_group.command("delete")
@click.option('--ids', 'message_ids_str', required=True, help="Comma-separated list of email IDs to PERMANENTLY DELETE.")
@click.option('--dry-run', is_flag=True, help="Show what would be done without actually doing it.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def delete_permanently_cmd(ctx, message_ids_str, dry_run, output_format):
    """PERMANENTLY deletes specified emails. This action is IRREVERSIBLE."""
    logger = ctx.obj.get('logger')
    service = ctx.obj.get('gmail_service')
    message_ids = _parse_ids(message_ids_str)

    if not message_ids:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails delete",
                "parameters_provided": {
                    "message_ids": [],
                    "dry_run": dry_run
                },
                "message": "No message IDs provided to delete permanently.",
                "data": None,
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "--ids option requires at least one valid message ID."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("No message IDs provided to delete permanently.")
        if logger: logger.warning("Delete command called with no message IDs.")
        return

    if logger: logger.info(f"Executing 'emails delete' for IDs: {message_ids} (Dry run: {dry_run})")
    
    if output_format == 'json':
        if dry_run:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails delete",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "DRY RUN: Emails would be PERMANENTLY DELETED. No actual changes made.",
                "data": {
                    "processed_ids": message_ids,
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("Dry run: Permanent delete operation completed.")
            return
        
        # For JSON output, we'll simplify the confirmation process
        if not _confirm_action(f"Are you absolutely sure you want to PERMANENTLY DELETE these {len(message_ids)} email(s)? This is IRREVERSIBLE."):
            output_obj = {
                "status": "aborted_by_user",
                "command_executed": "damien emails delete",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "Action aborted by user.",
                "data": {
                    "processed_ids": [],
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("User aborted permanent delete operation.")
            return
        
        success = gmail_integration.batch_delete_permanently(service, message_ids)
        if success:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails delete",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": f"Successfully PERMANENTLY DELETED {len(message_ids)} email(s).",
                "data": {
                    "processed_ids": message_ids,
                    "action_taken": True
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info(f"Successfully permanently deleted {len(message_ids)} emails.")
        else:
            output_obj = {
                "status": "error",
                "command_executed": "damien emails delete",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "dry_run": dry_run
                },
                "message": "Failed to permanently delete emails. Check logs for details.",
                "data": {
                    "processed_ids_attempted": message_ids,
                    "action_taken": False
                },
                "error_details": {
                    "code": "GMAIL_API_BATCH_DELETE_ERROR",
                    "details": "API returned error for batchDelete operation. Check logs for more details."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.error("Permanent delete operation failed at integration level.")
    else: # human format
        click.secho(f"WARNING: Preparing to PERMANENTLY DELETE {len(message_ids)} email(s).", fg="red", bold=True)
        click.secho("This action CANNOT be undone.", fg="red")

        if dry_run:
            click.echo("DRY RUN: Emails would be PERMANENTLY DELETED. No actual changes made.")
            if logger: logger.info("Dry run: Permanent delete operation completed.")
            return

        if not _confirm_action(f"Are you absolutely sure you want to PERMANENTLY DELETE these {len(message_ids)} email(s)? This is IRREVERSIBLE."):
            if logger: logger.info("User aborted permanent delete operation at first prompt.")
            return
        
        confirmation_text = click.prompt(
            click.style("This action is IRREVERSIBLE. To proceed, type 'YESIDO' and press Enter", fg="yellow", bold=True),
            type=str,
            default="",
            show_default=False,
            prompt_suffix=': '
        )
        if confirmation_text.strip().upper() != 'YESIDO':
            click.echo("Confirmation text did not match. Permanent deletion aborted.")
            if logger: logger.info("User failed second confirmation (did not type YESIDO).")
            return
        
        if not _confirm_action(click.style("FINAL WARNING: All checks passed. Confirm PERMANENT DELETION of these emails?", fg="red", bold=True),
                            abort_message="Permanent deletion aborted at final warning."):
            if logger: logger.info("User aborted permanent delete at final warning.")
            return

        success = gmail_integration.batch_delete_permanently(service, message_ids)
        if success:
            click.echo(f"Successfully PERMANENTLY DELETED {len(message_ids)} email(s).")
            if logger: logger.info(f"Successfully permanently deleted {len(message_ids)} emails.")
        else:
            click.echo("Failed to permanently delete emails. Check logs for details.")
            if logger: logger.error("Permanent delete operation failed at integration level.")
        

@emails_group.command("label")
@click.option('--ids', 'message_ids_str', required=True, help="Comma-separated list of email IDs to label.")
@click.option('--add-labels', help="Comma-separated list of Label names to add.") # Changed help to Label names
@click.option('--remove-labels', help="Comma-separated list of Label names to remove.") # Changed help to Label names
@click.option('--dry-run', is_flag=True, help="Show what would be done without actually doing it.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def label_cmd(ctx, message_ids_str, add_labels, remove_labels, dry_run, output_format):
    """Adds or removes labels from specified emails."""
    logger = ctx.obj.get('logger')
    service = ctx.obj.get('gmail_service')
    message_ids = _parse_ids(message_ids_str)
    
    # These variables hold names, as parsed from user input
    add_label_names_list = _parse_ids(add_labels) if add_labels else []
    remove_label_names_list = _parse_ids(remove_labels) if remove_labels else []

    if not message_ids:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails label",
                "parameters_provided": {
                    "message_ids": [],
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "dry_run": dry_run
                },
                "message": "No message IDs provided to label.",
                "data": None,
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "--ids option requires at least one valid message ID."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("No message IDs provided to label.")
        if logger: logger.warning("Label command called with no message IDs.")
        return
    
    if not add_label_names_list and not remove_label_names_list:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails label",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "add_labels": [],
                    "remove_labels": [],
                    "dry_run": dry_run
                },
                "message": "No labels specified to add or remove.",
                "data": None,
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "Either --add-labels or --remove-labels must be specified."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("No labels specified to add or remove.")
        if logger: logger.warning("Label command called with no labels to change.")
        return

    if logger: logger.info(f"Executing 'emails label' for IDs: {message_ids} (Add: {add_label_names_list}, Remove: {remove_label_names_list}, Dry run: {dry_run})")
    
    action_summary = []
    if add_label_names_list: action_summary.append(f"add {add_label_names_list}")
    if remove_label_names_list: action_summary.append(f"remove {remove_label_names_list}")
    
    if output_format == 'json':
        if dry_run:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails label",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "dry_run": dry_run
                },
                "message": f"DRY RUN: Emails would have labels modified. No actual changes made.",
                "data": {
                    "processed_ids": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("Dry run: Label operation completed.")
            return
        
        success = gmail_integration.batch_modify_message_labels(
            service, 
            message_ids, 
            add_label_names=add_label_names_list,   
            remove_label_names=remove_label_names_list
        )
        
        if success:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails label",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "dry_run": dry_run
                },
                "message": f"Successfully applied label changes to {len(message_ids)} email(s).",
                "data": {
                    "processed_ids": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "action_taken": True
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info(f"Successfully labeled {len(message_ids)} emails.")
        else:
            output_obj = {
                "status": "error",
                "command_executed": "damien emails label",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "dry_run": dry_run
                },
                "message": "Failed to apply label changes. Check logs for details.",
                "data": {
                    "processed_ids_attempted": message_ids,
                    "add_labels": add_label_names_list,
                    "remove_labels": remove_label_names_list,
                    "action_taken": False
                },
                "error_details": {
                    "code": "GMAIL_API_BATCH_MODIFY_ERROR",
                    "details": "API returned error for batchModify operation. Check logs for more details."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.error("Label operation failed at integration level.")
    else: # human format
        click.echo(f"Preparing to {' and '.join(action_summary)} for {len(message_ids)} email(s)...")

        if dry_run:
            click.echo(f"DRY RUN: Emails would have labels modified. No actual changes made.")
            if logger: logger.info("Dry run: Label operation completed.")
            return
        
        success = gmail_integration.batch_modify_message_labels(
            service, 
            message_ids, 
            add_label_names=add_label_names_list,   
            remove_label_names=remove_label_names_list
        )
        if success:
            click.echo(f"Successfully applied label changes to {len(message_ids)} email(s).")
            if logger: logger.info(f"Successfully labeled {len(message_ids)} emails.")
        else:
            click.echo("Failed to apply label changes. Check logs for details.")
            if logger: logger.error("Label operation failed at integration level.")
        

@emails_group.command("mark")
@click.option('--ids', 'message_ids_str', required=True, help="Comma-separated list of email IDs to mark.")
@click.option('--action', 'mark_action', type=click.Choice(['read', 'unread'], case_sensitive=False), required=True, help="Action: 'read' or 'unread'.")
@click.option('--dry-run', is_flag=True, help="Show what would be done without actually doing it.")
@click.option('--output-format', type=click.Choice(['human', 'json']), default='human', show_default=True, help="Output format.")
@click.pass_context
def mark_cmd(ctx, message_ids_str, mark_action, dry_run, output_format):
    """Marks specified emails as read or unread."""
    logger = ctx.obj.get('logger')
    service = ctx.obj.get('gmail_service') # Ensure service is retrieved from context
    message_ids = _parse_ids(message_ids_str)

    if not message_ids:
        if output_format == 'json':
            output_obj = {
                "status": "error",
                "command_executed": "damien emails mark",
                "parameters_provided": {
                    "message_ids": [],
                    "mark_action": mark_action,
                    "dry_run": dry_run
                },
                "message": "No message IDs provided to mark.",
                "data": None,
                "error_details": {
                    "code": "MISSING_PARAMETER",
                    "details": "--ids option requires at least one valid message ID."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
        else:
            click.echo("No message IDs provided to mark.")
        if logger: logger.warning("Mark command called with no message IDs.")
        return

    if logger: logger.info(f"Executing 'emails mark' as {mark_action} for IDs: {message_ids} (Dry run: {dry_run})")
    
    if output_format == 'json':
        if dry_run:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails mark",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "mark_action": mark_action,
                    "dry_run": dry_run
                },
                "message": f"DRY RUN: Emails would be marked as {mark_action}. No actual changes made.",
                "data": {
                    "processed_ids": message_ids,
                    "mark_action": mark_action,
                    "action_taken": False
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info("Dry run: Mark operation completed.")
            return
        
        success = gmail_integration.batch_mark_messages(service, message_ids, mark_as=mark_action)
        if success:
            output_obj = {
                "status": "success",
                "command_executed": "damien emails mark",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "mark_action": mark_action,
                    "dry_run": dry_run
                },
                "message": f"Successfully marked {len(message_ids)} email(s) as {mark_action}.",
                "data": {
                    "processed_ids": message_ids,
                    "mark_action": mark_action,
                    "action_taken": True
                },
                "error_details": None
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.info(f"Successfully marked {len(message_ids)} emails as {mark_action}.")
        else:
            output_obj = {
                "status": "error",
                "command_executed": "damien emails mark",
                "parameters_provided": {
                    "message_ids": message_ids,
                    "mark_action": mark_action,
                    "dry_run": dry_run
                },
                "message": f"Failed to mark emails as {mark_action}. Check logs for details.",
                "data": {
                    "processed_ids_attempted": message_ids,
                    "mark_action": mark_action,
                    "action_taken": False
                },
                "error_details": {
                    "code": "GMAIL_API_BATCH_MODIFY_ERROR",
                    "details": "API returned error for batchModify operation. Check logs for more details."
                }
            }
            sys.stdout.write(json.dumps(output_obj, indent=2) + '\n')
            if logger: logger.error(f"Mark as {mark_action} operation failed at integration level.")
    else: # human format
        click.echo(f"Preparing to mark {len(message_ids)} email(s) as {mark_action}...")

        if dry_run:
            click.echo(f"DRY RUN: Emails would be marked as {mark_action}. No actual changes made.")
            if logger: logger.info("Dry run: Mark operation completed.")
            return

        success = gmail_integration.batch_mark_messages(service, message_ids, mark_as=mark_action)
        if success:
            click.echo(f"Successfully marked {len(message_ids)} email(s) as {mark_action}.")
            if logger: logger.info(f"Successfully marked {len(message_ids)} emails as {mark_action}.")
        else:
            click.echo(f"Failed to mark emails as {mark_action}. Check logs for details.")
            if logger: logger.error(f"Mark as {mark_action} operation failed at integration level.")