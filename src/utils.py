import re
import unicodedata
import logging
import yaml
import os

logger = logging.getLogger(__name__)

def slugify(value: str, allow_unicode=False) -> str:
    """
    Convert spaces or repeated dashes to single dashes. Remove characters that
    aren't alphanumerics, underscores, or hyphens. Convert to lowercase.
    Also strip leading and trailing whitespace, dashes, and underscores.

    Adapted from Django's slugify function.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        value = re.sub(r'[^\w\s-]', '', value.lower())
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    # Replace spaces and repeated dashes with single dashes
    value = re.sub(r'[-\s]+', '-', value)
    # Remove leading/trailing whitespace, dashes, underscores
    value = re.sub(r'^[-\s_]+|[-\s_]+$', '', value)
    logger.debug(f"Slugified '{value[:50]}...' to '{value}'")
    return value


# --- Configuration Loading ---

# Define the path to the config file relative to the project root
# Assumes utils.py is in src/ and config.yaml is in the root
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

def load_config() -> dict:
    """Loads the configuration from config.yaml."""
  
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            if config is None: # Handle empty YAML file
                 raise Exception(f"Configuration file {CONFIG_PATH} is empty.")
            logger.info(f"Loaded configuration from {CONFIG_PATH}")
            return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file {CONFIG_PATH}: {e}")
        # Decide on error handling: raise exception, return default, etc.
        raise # Re-raise the exception for now
    except Exception as e:
        logger.error(f"Error loading configuration file {CONFIG_PATH}: {e}")
        raise # Re-raise other potential errors

# --- End Configuration Loading ---

# Example usage:
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    test_string = "  Create a CLI tool to fetch Weather data!!  "
    slug = slugify(test_string)
    logger.info(f"Original: '{test_string}'")
    logger.info(f"Slugified: '{slug}'") # Expected: 'create-a-cli-tool-to-fetch-weather-data'

    test_string_2 = "Project with_underscores and --- multiple dashes"
    slug_2 = slugify(test_string_2)
    logger.info(f"Original: '{test_string_2}'")
    logger.info(f"Slugified: '{slug_2}'") # Expected: 'project-with_underscores-and-multiple-dashes'

    test_string_3 = "_Leading and Trailing_"
    slug_3 = slugify(test_string_3)
    logger.info(f"Original: '{test_string_3}'")
    logger.info(f"Slugified: '{slug_3}'") # Expected: 'leading-and-trailing'