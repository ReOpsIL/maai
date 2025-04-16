import logging
import os
from abc import ABC, abstractmethod
from utils import load_config
from agents.openai_client import OpenAIClient

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, project_name: str, project_path: str):
        """
        Initializes the agent with project context.

        Args:
            project_name: The name of the project.
            project_path: The absolute path to the project directory.
        """
        self.project_name = project_name
        self.project_path = project_path
        self.docs_path = os.path.join(self.project_path, "docs")
        self.src_path = os.path.join(self.project_path, "src")
        self.tests_path = os.path.join(self.project_path, "tests")
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load configuration
        config = load_config()
        model_name = config.get('llm', {}).get('model')
        provider = config.get('llm', {}).get('provider')

        self.logger.info(f"Using LLM model: {model_name} from provider: {provider}")
        if provider  in ["grok", "groq", "openrouter"]:
            self.model = OpenAIClient()
        else:
            raise Exception(f"Unknown AI provider {provider} - Cant initialize client")
        
        self.logger.info(f"Initialized for project: {self.project_name}")

    def generate_content(self, prompt: str) -> str:
        """Helper method to interact with OpenRouter API."""
        if self.model is None:
            self.logger.error("AI client not initialized. Cannot generate response.")
            raise Exception("FATAL error - Stopping!")

        return self.model.method(prompt=prompt)

    @abstractmethod
    def run(self, *args, **kwargs) -> str:
        """
        Executes the agent's primary task.
        Must be implemented by subclasses.
        """
        pass

    def _read_file(self, file_path: str) -> str | None:
        """Helper method to read a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def _write_file(self, file_path: str, content: str):
        """Helper method to write content to a file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Successfully wrote to {file_path}")
        except Exception as e:
            self.logger.error(f"Error writing file {file_path}: {e}")

    def _ensure_dir_exists(self, dir_path: str):
        """Helper method to ensure a directory exists."""
        try:
            os.makedirs(dir_path, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {dir_path}")
        except Exception as e:
            self.logger.error(f"Error creating directory {dir_path}: {e}")