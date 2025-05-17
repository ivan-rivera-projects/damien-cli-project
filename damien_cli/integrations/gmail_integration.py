import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from damien_cli.core import config # Our config file

def get_gmail_service():
    """
    Authenticates with Gmail and returns a service object to interact with the API.
    Handles token loading, refreshing, and the initial OAuth flow.
    """
    creds = None
    # The TOKEN_FILE stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if config.TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), config.SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                click.echo("Damien is refreshing your Gmail access token...")
                creds.refresh(Request())
            except Exception as e:
                click.echo(f"Damien couldn't refresh token: {e}. Please log in again.")
                creds = None # Force re-login
        
        if not creds: # creds might have become None if refresh failed
            click.echo("Damien needs to open your web browser to authorize Gmail access.")
            click.echo(f"Using credentials from: {config.CREDENTIALS_FILE}")
            if not config.CREDENTIALS_FILE.exists():
                click.echo(f"ERROR: Credentials file not found at {config.CREDENTIALS_FILE}")
                click.echo("Please ensure 'credentials.json' from Google Cloud is in the project root.")
                return None # Cannot proceed

            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.CREDENTIALS_FILE), config.SCOPES)
            # port=0 makes it find a random available port
            creds = flow.run_local_server(port=0,
                                          prompt='consent',
                                          authorization_prompt_message='Please authorize Damien-CLI in the browser window that just opened (or will open shortly)...')
        
        # Save the credentials for the next run
        with open(config.TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())
        click.echo(f"Damien has stored your access token at: {config.TOKEN_FILE}")

    try:
        service = build('gmail', 'v1', credentials=creds)
        click.echo("Damien has successfully connected to your Gmail account!")
        return service
    except HttpError as error:
        click.echo(f'An API error occurred: {error}')
        return None
    except Exception as e:
        click.echo(f'An unexpected error occurred building service: {e}')
        return None

# Example function to test the service (we'll use this soon)
def list_labels(service):
    if not service:
        click.echo("Cannot list labels, Gmail service not available.")
        return
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            click.echo('No labels found.')
            return
        click.echo('Labels:')
        for label in labels:
            click.echo(label['name'])
    except HttpError as error:
        click.echo(f'An API error occurred while listing labels: {error}')
    except Exception as e:
        click.echo(f'An unexpected error occurred while listing labels: {e}')
