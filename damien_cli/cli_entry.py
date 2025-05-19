import click
import logging
import os # Often useful for CLI apps, e.g. checking env vars

# Import core utilities
from damien_cli.core.logging_setup import setup_logging
# We will import get_gmail_service directly in the login command to avoid potential
# early import issues if gmail_integration itself had complex top-level dependencies.

# Import feature command groups
from damien_cli.features.email_management.commands import emails_group
from damien_cli.features.rule_management.commands import rules_group

@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose (DEBUG level) logging.")
@click.option('--config-dir', envvar='DAMIEN_CONFIG_DIR', type=click.Path(), default=None, help="Path to an alternative config/data directory.") # Example for future config
@click.pass_context
def damien(ctx, verbose, config_dir):
    """
    Damien-CLI: Your Pythonic Gmail Assistant.
    Damien helps you manage your Gmail inbox with smarts and power.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Determine if running in a test environment (simplistic check for now)
    # A more robust way might be a dedicated environment variable for testing.
    # For now, assume regular CLI runs are not 'testing_mode=True' for logging.
    running_tests = "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or \
                    os.environ.get("DAMIEN_TEST_MODE") == "1"

    logger = setup_logging(log_level=log_level, testing_mode=running_tests)
    
    # Initialize context object to share data with subcommands
    ctx.obj = {} 
    ctx.obj['logger'] = logger
    ctx.obj['config_dir'] = config_dir # Store custom config dir if provided
    # The gmail_service will be added to ctx.obj by the login command or by groups that need it.

    logger.debug(f"Damien CLI started. Verbose: {verbose}, Config Dir: {config_dir}, Testing Mode: {running_tests}")
    logger.debug(f"Effective log level: {logging.getLevelName(logger.getEffectiveLevel())}")


# Register command groups from feature slices
damien.add_command(emails_group)
damien.add_command(rules_group)


@damien.command()
@click.pass_context
def hello(ctx):
    """Greets the user."""
    logger = ctx.obj.get('logger', logging.getLogger('damien_cli_fallback')) # Get logger, provide fallback
    logger.info("Executing hello command.")
    click.echo("Damien says: Hello! I'm ready to assist with your Gmail.")
    logger.debug("Hello command finished successfully.")


@damien.command()
@click.pass_context
def login(ctx):
    """Logs into Gmail and ensures authentication token is valid."""
    logger = ctx.obj.get('logger', logging.getLogger('damien_cli_fallback'))
    logger.info("Attempting Gmail login and service initialization...")
    
    # Import get_gmail_service here to ensure it's fresh and avoids complex startup imports
    from damien_cli.integrations.gmail_integration import get_gmail_service 
    
    service = get_gmail_service() 
    
    if service:
        logger.info("Login successful! Damien is connected to Gmail.")
        click.echo("Login successful! Damien is connected to Gmail.")
        # Store the authenticated service object in the context for other commands to use
        ctx.obj['gmail_service'] = service 
    else:
        logger.error("Login failed. Could not establish Gmail service.")
        click.echo("Login failed. Please check the messages above or try again.")
        # Optionally, you might want to exit here if login is critical for all operations
        # ctx.exit(1) 

# This block is useful if you were to run this script directly (e.g., python cli_entry.py)
# However, with Poetry scripts (`poetry run damien`), this __main__ block isn't the primary entry point.
# It's good practice to keep it for direct script execution testing.
if __name__ == '__main__':
    # When running directly, ctx.obj won't be pre-populated by Click in the same way.
    # We pass an empty dict for obj to avoid errors if subcommands expect ctx.obj.
    damien(obj={})