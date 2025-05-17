import click
import logging
from damien_cli.integrations.gmail_integration import get_gmail_service, list_labels
from damien_cli.core.logging_setup import setup_logging

@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose (DEBUG level) logging.")
@click.pass_context # To pass context to subcommands if needed, and to store logger
def damien(ctx, verbose):
    """
    Damien-CLI: Your Pythonic Gmail Assistant.
    Damien helps you manage your Gmail inbox with smarts and power.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging(log_level=log_level)
    ctx.obj = {} # Create a context object if it doesn't exist
    ctx.obj['logger'] = logger # Store the logger in the context
    logger.debug("Damien CLI started. Logging configured.")


@damien.command()
@click.pass_context # So we can access the logger from context
def hello(ctx):
    """Greets the user."""
    logger = ctx.obj['logger']
    logger.info("Executing hello command.")
    click.echo("Damien says: Hello! I'm ready to assist with your Gmail.")
    logger.debug("Hello command finished successfully.")


@damien.command()
@click.pass_context
def login(ctx):
    """Logs into Gmail and stores authentication token."""
    logger = ctx.obj['logger']
    logger.info("Attempting Gmail login...")
    
    # Pass logger to functions that need it, or they can get it themselves
    # For now, get_gmail_service uses click.echo, which is fine for this stage.
    # Later, you might pass the logger instance around or have modules get it.
    service = get_gmail_service() 
    
    if service:
        logger.info("Login successful! Damien is connected.")
        click.echo("Login successful! Damien is connected.")
    else:
        logger.error("Login failed.")
        click.echo("Login failed. Please check the messages above.")

if __name__ == '__main__':
    # This part is mostly for when you run the script directly (python cli_entry.py)
    # Poetry scripts don't use this __main__ block when invoked as 'damien'
    damien(obj={}) # Pass an empty context object for direct script execution