import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file if it exists (for development)
load_dotenv()

# Determine the base directory of the project
# Assumes config.py is in backend/src/, so two levels up is the project root
# Adjust if your structure is different
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Determine the path to the React frontend build directory
# Default assumes frontend build is in frontend/build relative to project root
REACT_BUILD_FOLDER_DEFAULT = BASE_DIR / "frontend" / "build"
REACT_BUILD_FOLDER = Path(os.getenv("REACT_BUILD_FOLDER", str(REACT_BUILD_FOLDER_DEFAULT)))

# Check if the React build folder exists
if not REACT_BUILD_FOLDER.exists() or not (REACT_BUILD_FOLDER / "index.html").exists():
    logging.warning(
        f"React build folder not found or missing index.html at {REACT_BUILD_FOLDER}. "
        f"Static file serving might not work correctly. "
        f"Did you build the frontend (`npm run build`)?"
    )


class Config:
    """Base configuration class."""
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    STATIC_FOLDER: str = str(REACT_BUILD_FOLDER) # For Flask's static file serving config
    REACT_APP_BUILD_PATH: Path = REACT_BUILD_FOLDER # Keep Path object for internal use

    # --- Custom Application Settings ---
    # None defined in the plan yet

    # Check for missing SECRET_KEY in production
    if not DEBUG and not SECRET_KEY:
        logging.critical("FATAL ERROR: SECRET_KEY environment variable is not set in production.")
        # In a real app, you might want to raise an exception or exit here
        # For now, we'll let it potentially run with a default Flask would provide,
        # but Flask startup might fail depending on version/settings.
        # Using a default is highly insecure.
    elif DEBUG and not SECRET_KEY:
        logging.warning("SECRET_KEY is not set, using a default 'dev_secret_key'. DO NOT USE IN PRODUCTION.")
        SECRET_KEY = "dev_secret_key" # Insecure default for development ONLY

# Instantiate config for easy import
config = Config()

# Basic logging configuration
log_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(level=log_level,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Log loaded configuration values (be careful not to log secrets)
logging.info(f"Flask DEBUG mode: {config.DEBUG}")
logging.info(f"React build folder configured at: {config.REACT_APP_BUILD_PATH}")
if config.SECRET_KEY == "dev_secret_key":
     logging.warning("Running with insecure default SECRET_KEY.")