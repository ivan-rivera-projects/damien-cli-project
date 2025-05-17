import os
from pathlib import Path

# Usually your project root is where pyproject.toml is
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json" # Path to your credentials.json
TOKEN_FILE = DATA_DIR / "token.json" # Where we'll save the login token

# Make sure DATA_DIR exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# These are the 'permissions' Damien will ask for from Gmail.
# 'gmail.modify' allows reading, moving to trash, deleting, labeling.
# Start with 'gmail.readonly' if you want to be cautious first, then change later.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
