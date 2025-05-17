import logging
import sys
from . import config # To get DATA_DIR

LOG_FILE_PATH = config.DATA_DIR / "damien_session.log"

def setup_logging(log_level=logging.INFO):
    """Configures basic logging for the application."""
    
    # Create a logger
    logger = logging.getLogger('damien_cli') # Get the root logger for our app
    logger.setLevel(log_level) # Set the minimum level of messages to handle

    # Prevent multiple handlers if setup_logging is called more than once
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter - defines how log messages will look
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
    )

    # Console Handler - to print logs to the screen
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level) # Or a different level for console if you want
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler - to write logs to a file
    try:
        file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a') # 'a' for append
        file_handler.setLevel(log_level) # Log everything at this level and above to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Failed to set up file handler for logging: {e}", exc_info=True)


    logger.info(f"Logging initialized. Log file: {LOG_FILE_PATH}")
    return logger

# You can get the logger by calling this function
# Example: app_logger = setup_logging()
# Then use: app_logger.info("Something happened")
